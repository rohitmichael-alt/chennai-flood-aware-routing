"""Certified lazy synchronization for fixed-topology metric snapshots.

The lower/upper-bound certificate is established prior art. This module applies
that principle as an engine-neutral synchronization gate; it does not claim a
new shortest-path algorithm.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from time import perf_counter_ns
from types import MappingProxyType
from typing import Literal

from chennai_routing.routing.engine import (
    EdgeId,
    EnginePath,
    EngineQuery,
    MetricSnapshot,
    NodeId,
    ShortestPathEngine,
    Weight,
)


@dataclass(frozen=True)
class CertificateTolerance:
    """Exact rational stretch allowance: epsilon = numerator / denominator."""

    numerator: int = 5
    denominator: int = 100

    def __post_init__(self) -> None:
        if self.numerator < 0:
            raise ValueError("Tolerance numerator must be non-negative.")
        if self.denominator <= 0:
            raise ValueError("Tolerance denominator must be positive.")

    @property
    def epsilon(self) -> float:
        return self.numerator / self.denominator


@dataclass(frozen=True)
class WeightUpdateBatch:
    """Atomic absolute edge-weight replacements for one new version."""

    base_version: int
    version: int
    replacements: tuple[tuple[EdgeId, Weight], ...]


@dataclass(frozen=True)
class UpdateReceipt:
    version: int
    replacement_count: int
    pending_edge_count: int
    lower_bound_violation_count: int


@dataclass(frozen=True)
class RefreshReport:
    previous_engine_version: int | None
    metric_version: int
    reason: str
    duration_ns: int


@dataclass(frozen=True)
class SynchronizerState:
    current_version: int
    synchronized_version: int
    pending_edge_count: int
    lower_bound_violation_count: int
    update_batch_count: int
    refresh_count: int
    certified_stale_query_count: int
    certified_unreachable_count: int
    synchronization_duration_ns: int


RouteDecision = Literal[
    "CURRENT",
    "CERTIFIED_STALE",
    "CERTIFIED_UNREACHABLE",
    "REFRESHED",
    "REFRESHED_UNREACHABLE",
]


@dataclass(frozen=True)
class RouteResult:
    """A route evaluated under the authoritative current metric."""

    status: Literal["FOUND", "UNREACHABLE"]
    path: EnginePath | None
    decision: RouteDecision
    current_version: int
    initial_engine_version: int
    final_engine_version: int
    lower_bound: Weight | None
    upper_bound: Weight | None
    tolerance: CertificateTolerance
    pending_edge_count_before: int
    refresh_reason: str | None
    query_duration_ns: int
    path_evaluation_duration_ns: int
    refresh_duration_ns: int
    total_duration_ns: int


def _validate_certifiable_weight(weight: Weight) -> None:
    if isinstance(weight, bool):
        raise TypeError("Certified metrics require integer weights or positive infinity.")
    if isinstance(weight, int):
        if weight < 0:
            raise ValueError("Certified metric weights must be non-negative.")
        return
    if isinstance(weight, float) and weight == math.inf:
        return
    raise TypeError(
        "Certified metrics require non-negative integer weights (for example, "
        "quantized milliseconds) or positive infinity for closures."
    )


def _snapshot(
    topology_id: str,
    version: int,
    weights: dict[EdgeId, Weight],
) -> MetricSnapshot:
    return MetricSnapshot(
        topology_id=topology_id,
        version=version,
        weights=MappingProxyType(dict(weights)),
    )


class CertifiedLazySynchronizer:
    """Gate metric refreshes with a per-query bounded-staleness certificate."""

    def __init__(
        self,
        engine: ShortestPathEngine,
        initial_metric: MetricSnapshot,
        *,
        tolerance: CertificateTolerance | None = None,
    ) -> None:
        if not engine.capabilities.exact_for_represented_metric:
            raise ValueError("The controller requires an exact represented-metric engine.")
        if initial_metric.topology_id != engine.topology_id:
            raise ValueError("Initial metric topology does not match the engine.")
        for weight in initial_metric.weights.values():
            _validate_certifiable_weight(weight)

        self._engine = engine
        self._tolerance = tolerance or CertificateTolerance()
        self._lock = threading.RLock()
        self._current_weights = dict(initial_metric.weights)
        self._synchronized_weights = dict(initial_metric.weights)
        self._current_version = initial_metric.version
        self._synchronized_version = initial_metric.version
        self._pending_edges: set[EdgeId] = set()
        self._violating_edges: set[EdgeId] = set()
        self._update_batch_count = 0
        self._refresh_count = 0
        self._certified_stale_query_count = 0
        self._certified_unreachable_count = 0
        synchronization_started = perf_counter_ns()
        engine.synchronize(
            _snapshot(
                engine.topology_id,
                initial_metric.version,
                self._current_weights,
            )
        )
        self._synchronization_duration_ns = (
            perf_counter_ns() - synchronization_started
        )

    @property
    def topology_id(self) -> str:
        return self._engine.topology_id

    @property
    def current_weights(self) -> MappingProxyType:
        with self._lock:
            return MappingProxyType(dict(self._current_weights))

    def state(self) -> SynchronizerState:
        with self._lock:
            return SynchronizerState(
                current_version=self._current_version,
                synchronized_version=self._synchronized_version,
                pending_edge_count=len(self._pending_edges),
                lower_bound_violation_count=len(self._violating_edges),
                update_batch_count=self._update_batch_count,
                refresh_count=self._refresh_count,
                certified_stale_query_count=self._certified_stale_query_count,
                certified_unreachable_count=self._certified_unreachable_count,
                synchronization_duration_ns=self._synchronization_duration_ns,
            )

    def apply_updates(self, batch: WeightUpdateBatch) -> UpdateReceipt:
        with self._lock:
            if batch.base_version != self._current_version:
                raise ValueError(
                    f"Update base version {batch.base_version} does not match "
                    f"current version {self._current_version}."
                )
            if batch.version != batch.base_version + 1:
                raise ValueError("Update versions must be contiguous.")

            seen: set[EdgeId] = set()
            candidate = dict(self._current_weights)
            for edge, weight in batch.replacements:
                if edge in seen:
                    raise ValueError(f"Update contains duplicate edge {edge!r}.")
                if edge not in candidate:
                    raise ValueError(f"Update contains unknown edge {edge!r}.")
                _validate_certifiable_weight(weight)
                seen.add(edge)
                candidate[edge] = weight

            self._current_weights = candidate
            self._current_version = batch.version
            self._pending_edges = {
                edge
                for edge, weight in candidate.items()
                if weight != self._synchronized_weights[edge]
            }
            self._violating_edges = {
                edge
                for edge in self._pending_edges
                if candidate[edge] < self._synchronized_weights[edge]
            }
            self._update_batch_count += 1
            return UpdateReceipt(
                version=batch.version,
                replacement_count=len(batch.replacements),
                pending_edge_count=len(self._pending_edges),
                lower_bound_violation_count=len(self._violating_edges),
            )

    def refresh(self, reason: str = "explicit") -> RefreshReport:
        with self._lock:
            return self._refresh_locked(reason)

    def _refresh_locked(self, reason: str) -> RefreshReport:
        started = perf_counter_ns()
        previous_version = self._engine.metric_version
        self._engine.synchronize(
            _snapshot(
                self._engine.topology_id,
                self._current_version,
                self._current_weights,
            )
        )
        duration = perf_counter_ns() - started
        self._synchronization_duration_ns += duration
        self._synchronized_weights = dict(self._current_weights)
        self._synchronized_version = self._current_version
        self._pending_edges.clear()
        self._violating_edges.clear()
        self._refresh_count += 1
        return RefreshReport(
            previous_engine_version=previous_version,
            metric_version=self._current_version,
            reason=reason,
            duration_ns=duration,
        )

    def _evaluate_path(self, path: EnginePath) -> Weight:
        cost: Weight = 0
        for edge in path.edges:
            cost += self._current_weights[edge]
        return cost

    def _certificate_passes(self, lower: Weight, upper: Weight) -> bool:
        if math.isinf(float(upper)):
            return False
        if not isinstance(lower, int) or not isinstance(upper, int):
            raise TypeError("Finite certified path costs must be integers.")
        tolerance = self._tolerance
        return (
            upper * tolerance.denominator
            <= lower * (tolerance.denominator + tolerance.numerator)
        )

    def route(self, source: NodeId, target: NodeId) -> RouteResult:
        with self._lock:
            total_started = perf_counter_ns()
            pending_before = len(self._pending_edges)
            initial_engine_version = self._synchronized_version
            refresh_duration = 0
            refresh_reason: str | None = None

            if self._violating_edges:
                refresh_reason = "lower_bound_invalidated"
                report = self._refresh_locked(refresh_reason)
                refresh_duration += report.duration_ns

            query_started = perf_counter_ns()
            query = self._engine.query(source, target)
            query_duration = perf_counter_ns() - query_started

            if not self._pending_edges:
                return self._result_from_current_query(
                    query=query,
                    decision=(
                        "REFRESHED"
                        if refresh_reason and query.status == "FOUND"
                        else "REFRESHED_UNREACHABLE"
                        if refresh_reason
                        else "CURRENT"
                    ),
                    current_version=self._current_version,
                    initial_engine_version=initial_engine_version,
                    pending_before=pending_before,
                    refresh_reason=refresh_reason,
                    query_duration=query_duration,
                    refresh_duration=refresh_duration,
                    total_started=total_started,
                )

            if query.status == "UNREACHABLE":
                self._certified_unreachable_count += 1
                return RouteResult(
                    status="UNREACHABLE",
                    path=None,
                    decision="CERTIFIED_UNREACHABLE",
                    current_version=self._current_version,
                    initial_engine_version=initial_engine_version,
                    final_engine_version=self._synchronized_version,
                    lower_bound=None,
                    upper_bound=None,
                    tolerance=self._tolerance,
                    pending_edge_count_before=pending_before,
                    refresh_reason=None,
                    query_duration_ns=query_duration,
                    path_evaluation_duration_ns=0,
                    refresh_duration_ns=0,
                    total_duration_ns=perf_counter_ns() - total_started,
                )

            assert query.path is not None
            evaluation_started = perf_counter_ns()
            upper = self._evaluate_path(query.path)
            evaluation_duration = perf_counter_ns() - evaluation_started
            lower = query.path.cost

            if self._certificate_passes(lower, upper):
                self._certified_stale_query_count += 1
                certified_path = EnginePath(
                    nodes=query.path.nodes,
                    edges=query.path.edges,
                    cost=upper,
                )
                return RouteResult(
                    status="FOUND",
                    path=certified_path,
                    decision="CERTIFIED_STALE",
                    current_version=self._current_version,
                    initial_engine_version=initial_engine_version,
                    final_engine_version=self._synchronized_version,
                    lower_bound=lower,
                    upper_bound=upper,
                    tolerance=self._tolerance,
                    pending_edge_count_before=pending_before,
                    refresh_reason=None,
                    query_duration_ns=query_duration,
                    path_evaluation_duration_ns=evaluation_duration,
                    refresh_duration_ns=0,
                    total_duration_ns=perf_counter_ns() - total_started,
                )

            refresh_reason = "certificate_failed"
            report = self._refresh_locked(refresh_reason)
            refresh_duration += report.duration_ns
            refreshed_query_started = perf_counter_ns()
            refreshed_query = self._engine.query(source, target)
            query_duration += perf_counter_ns() - refreshed_query_started
            return self._result_from_current_query(
                query=refreshed_query,
                decision=(
                    "REFRESHED"
                    if refreshed_query.status == "FOUND"
                    else "REFRESHED_UNREACHABLE"
                ),
                current_version=self._current_version,
                initial_engine_version=initial_engine_version,
                pending_before=pending_before,
                refresh_reason=refresh_reason,
                query_duration=query_duration,
                refresh_duration=refresh_duration,
                total_started=total_started,
                lower_bound=lower,
                upper_bound=upper,
                path_evaluation_duration=evaluation_duration,
            )

    def _result_from_current_query(
        self,
        *,
        query: EngineQuery,
        decision: RouteDecision,
        current_version: int,
        initial_engine_version: int,
        pending_before: int,
        refresh_reason: str | None,
        query_duration: int,
        refresh_duration: int,
        total_started: int,
        lower_bound: Weight | None = None,
        upper_bound: Weight | None = None,
        path_evaluation_duration: int = 0,
    ) -> RouteResult:
        return RouteResult(
            status=query.status,
            path=query.path,
            decision=decision,
            current_version=current_version,
            initial_engine_version=initial_engine_version,
            final_engine_version=self._synchronized_version,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            tolerance=self._tolerance,
            pending_edge_count_before=pending_before,
            refresh_reason=refresh_reason,
            query_duration_ns=query_duration,
            path_evaluation_duration_ns=path_evaluation_duration,
            refresh_duration_ns=refresh_duration,
            total_duration_ns=perf_counter_ns() - total_started,
        )
