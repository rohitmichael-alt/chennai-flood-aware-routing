"""Eager repeated-snapshot baseline for lazy synchronization experiments."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns
from types import MappingProxyType

from chennai_routing.routing.dynamic import WeightUpdateBatch
from chennai_routing.routing.engine import (
    EdgeId,
    EngineQuery,
    MetricSnapshot,
    ShortestPathEngine,
    Weight,
)


@dataclass(frozen=True)
class EagerBaselineState:
    metric_version: int
    synchronization_count: int
    synchronization_duration_ns: int


class EagerRefreshRouter:
    """Synchronize the complete metric after every accepted update batch."""

    def __init__(
        self,
        engine: ShortestPathEngine,
        initial_metric: MetricSnapshot,
    ) -> None:
        if not engine.capabilities.exact_for_represented_metric:
            raise ValueError("The eager oracle requires an exact engine.")
        self._engine = engine
        self._weights: dict[EdgeId, Weight] = dict(initial_metric.weights)
        self._version = initial_metric.version
        self._synchronization_count = 1
        started = perf_counter_ns()
        engine.synchronize(initial_metric)
        self._synchronization_duration_ns = perf_counter_ns() - started

    @property
    def weights(self) -> MappingProxyType:
        return MappingProxyType(dict(self._weights))

    def state(self) -> EagerBaselineState:
        return EagerBaselineState(
            metric_version=self._version,
            synchronization_count=self._synchronization_count,
            synchronization_duration_ns=self._synchronization_duration_ns,
        )

    def apply_updates(self, batch: WeightUpdateBatch) -> None:
        if batch.base_version != self._version:
            raise ValueError("Update base version does not match eager metric version.")
        if batch.version != batch.base_version + 1:
            raise ValueError("Update versions must be contiguous.")
        candidate = dict(self._weights)
        seen: set[EdgeId] = set()
        for edge, weight in batch.replacements:
            if edge in seen:
                raise ValueError(f"Update contains duplicate edge {edge!r}.")
            if edge not in candidate:
                raise ValueError(f"Update contains unknown edge {edge!r}.")
            seen.add(edge)
            candidate[edge] = weight

        snapshot = MetricSnapshot(
            topology_id=self._engine.topology_id,
            version=batch.version,
            weights=MappingProxyType(candidate),
        )
        started = perf_counter_ns()
        self._engine.synchronize(snapshot)
        self._synchronization_duration_ns += perf_counter_ns() - started
        self._weights = candidate
        self._version = batch.version
        self._synchronization_count += 1

    def route(self, source: object, target: object) -> EngineQuery:
        return self._engine.query(source, target)
