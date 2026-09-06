"""Reproducible functional experiments for certified metric synchronization."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter_ns
from types import MappingProxyType
from typing import Literal

import networkx as nx

from chennai_routing.evaluation.baseline import EagerRefreshRouter
from chennai_routing.routing.dynamic import (
    CertificateTolerance,
    CertifiedLazySynchronizer,
    WeightUpdateBatch,
)
from chennai_routing.routing.cch_engine import RoutingKitCCHEngine
from chennai_routing.routing.engine import EdgeId, MetricSnapshot
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine


@dataclass(frozen=True)
class LazySyncExperimentConfig:
    seed: int = 8597
    node_count: int = 100
    extra_edge_count: int = 250
    epochs: int = 40
    updates_per_epoch: int = 4
    queries_per_epoch: int = 25
    update_mode: Literal["increases_only", "mixed"] = "increases_only"
    engine: Literal["networkx", "cch"] = "networkx"
    epsilon_numerator: int = 5
    epsilon_denominator: int = 100

    def __post_init__(self) -> None:
        if self.node_count < 3:
            raise ValueError("node_count must be at least 3.")
        if self.extra_edge_count < 0:
            raise ValueError("extra_edge_count must be non-negative.")
        if self.epochs <= 0 or self.updates_per_epoch <= 0:
            raise ValueError("epochs and updates_per_epoch must be positive.")
        if self.queries_per_epoch <= 0:
            raise ValueError("queries_per_epoch must be positive.")
        if self.update_mode not in {"increases_only", "mixed"}:
            raise ValueError("Unsupported update mode.")
        if self.engine not in {"networkx", "cch"}:
            raise ValueError("Unsupported routing engine.")


@dataclass(frozen=True)
class ExperimentSummary:
    config: dict[str, object]
    topology_digest: str
    trace_digest: str
    query_count: int
    certificate_violation_count: int
    exact_after_refresh_mismatch_count: int
    certified_stale_query_count: int
    certified_unreachable_count: int
    lazy_refresh_count: int
    eager_synchronization_count: int
    refreshes_avoided: int
    certificate_hit_rate: float
    lazy_engine_build_duration_ns: int
    eager_engine_build_duration_ns: int
    lazy_synchronization_duration_ns: int
    eager_synchronization_duration_ns: int
    lazy_total_duration_ns: int
    eager_total_duration_ns: int
    python_version: str
    networkx_version: str
    qualification: str


def _build_graph(
    config: LazySyncExperimentConfig,
    rng: random.Random,
) -> tuple[nx.MultiDiGraph, dict[EdgeId, int]]:
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(range(config.node_count))

    for node in range(config.node_count):
        next_node = (node + 1) % config.node_count
        graph.add_edge(node, next_node)
        graph.add_edge(next_node, node)

    for _ in range(config.extra_edge_count):
        source = rng.randrange(config.node_count)
        target = rng.randrange(config.node_count)
        if source == target:
            target = (target + 1) % config.node_count
        graph.add_edge(source, target)

    weights = {
        (u, v, key): rng.randint(5_000, 60_000)
        for u, v, key in graph.edges(keys=True)
    }
    return graph, weights


def _trace_digest(events: list[dict[str, object]]) -> str:
    payload = json.dumps(events, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _topology_digest(graph: nx.MultiDiGraph) -> str:
    payload = json.dumps(
        sorted(repr((u, v, key)) for u, v, key in graph.edges(keys=True))
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def run_certified_lazy_experiment(
    config: LazySyncExperimentConfig,
    output_dir: Path,
) -> ExperimentSummary:
    """Replay one deterministic trace through eager and certificate-gated routers."""

    rng = random.Random(config.seed)
    graph, initial_weights = _build_graph(config, rng)
    edge_ids = tuple(initial_weights)
    engine_type = (
        RoutingKitCCHEngine
        if config.engine == "cch"
        else NetworkXDijkstraEngine
    )
    lazy_build_started = perf_counter_ns()
    lazy_engine = engine_type(graph)
    lazy_build_duration = perf_counter_ns() - lazy_build_started
    eager_build_started = perf_counter_ns()
    eager_engine = engine_type(graph)
    eager_build_duration = perf_counter_ns() - eager_build_started
    initial_snapshot = MetricSnapshot(
        topology_id=lazy_engine.topology_id,
        version=0,
        weights=MappingProxyType(dict(initial_weights)),
    )
    tolerance = CertificateTolerance(
        numerator=config.epsilon_numerator,
        denominator=config.epsilon_denominator,
    )
    lazy = CertifiedLazySynchronizer(
        lazy_engine,
        initial_snapshot,
        tolerance=tolerance,
    )
    eager = EagerRefreshRouter(
        eager_engine,
        initial_snapshot,
    )

    events: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    certificate_violations = 0
    exact_mismatches = 0
    lazy_total_ns = 0
    eager_total_ns = 0
    version = 0

    for epoch in range(config.epochs):
        selected = rng.sample(
            edge_ids,
            k=min(config.updates_per_epoch, len(edge_ids)),
        )
        replacements: list[tuple[EdgeId, int]] = []
        for edge in selected:
            old_weight = int(eager.weights[edge])
            if config.update_mode == "mixed" and rng.random() < 0.3:
                new_weight = max(1, old_weight - rng.randint(1, 2_000))
            else:
                new_weight = old_weight + rng.randint(1, 2_000)
            replacements.append((edge, new_weight))

        batch = WeightUpdateBatch(
            base_version=version,
            version=version + 1,
            replacements=tuple(replacements),
        )
        version += 1
        lazy.apply_updates(batch)
        eager.apply_updates(batch)
        events.append(
            {
                "epoch": epoch,
                "version": version,
                "updates": [
                    [repr(edge), weight] for edge, weight in replacements
                ],
            }
        )

        for query_index in range(config.queries_per_epoch):
            source = rng.randrange(config.node_count)
            target = rng.randrange(config.node_count)
            while target == source:
                target = rng.randrange(config.node_count)

            eager_started = perf_counter_ns()
            eager_result = eager.route(source, target)
            eager_duration = perf_counter_ns() - eager_started
            lazy_result = lazy.route(source, target)

            eager_total_ns += eager_duration
            lazy_total_ns += (
                lazy_result.query_duration_ns
                + lazy_result.path_evaluation_duration_ns
            )
            events.append(
                {
                    "epoch": epoch,
                    "query": query_index,
                    "source": source,
                    "target": target,
                }
            )

            eager_cost = eager_result.path.cost if eager_result.path else None
            lazy_cost = lazy_result.path.cost if lazy_result.path else None
            violation = False
            exact_mismatch = False
            if eager_result.status != lazy_result.status:
                violation = True
                exact_mismatch = lazy_result.decision.startswith("REFRESHED")
            elif eager_cost is not None and lazy_cost is not None:
                violation = (
                    lazy_cost * tolerance.denominator
                    > eager_cost
                    * (tolerance.denominator + tolerance.numerator)
                )
                if lazy_result.decision.startswith("REFRESHED"):
                    exact_mismatch = lazy_cost != eager_cost

            certificate_violations += int(violation)
            exact_mismatches += int(exact_mismatch)
            rows.append(
                {
                    "epoch": epoch,
                    "query_index": query_index,
                    "metric_version": version,
                    "source": source,
                    "target": target,
                    "decision": lazy_result.decision,
                    "eager_cost": eager_cost,
                    "lazy_cost": lazy_cost,
                    "lower_bound": lazy_result.lower_bound,
                    "upper_bound": lazy_result.upper_bound,
                    "pending_edges_before": lazy_result.pending_edge_count_before,
                    "certificate_violation": violation,
                    "exact_after_refresh_mismatch": exact_mismatch,
                    "lazy_total_duration_ns": lazy_result.total_duration_ns,
                    "eager_query_duration_ns": eager_duration,
                }
            )

    state = lazy.state()
    eager_state = eager.state()
    query_count = len(rows)
    stale_count = state.certified_stale_query_count
    hit_rate = stale_count / query_count if query_count else 0.0
    summary = ExperimentSummary(
        config=asdict(config),
        topology_digest=_topology_digest(graph),
        trace_digest=_trace_digest(events),
        query_count=query_count,
        certificate_violation_count=certificate_violations,
        exact_after_refresh_mismatch_count=exact_mismatches,
        certified_stale_query_count=stale_count,
        certified_unreachable_count=state.certified_unreachable_count,
        lazy_refresh_count=state.refresh_count,
        eager_synchronization_count=eager_state.synchronization_count,
        refreshes_avoided=max(
            0,
            eager_state.synchronization_count - 1 - state.refresh_count,
        ),
        certificate_hit_rate=hit_rate,
        lazy_engine_build_duration_ns=lazy_build_duration,
        eager_engine_build_duration_ns=eager_build_duration,
        lazy_synchronization_duration_ns=state.synchronization_duration_ns,
        eager_synchronization_duration_ns=(
            eager_state.synchronization_duration_ns
        ),
        lazy_total_duration_ns=(
            lazy_total_ns + state.synchronization_duration_ns
        ),
        eager_total_duration_ns=(
            eager_total_ns + eager_state.synchronization_duration_ns
        ),
        python_version=platform.python_version(),
        networkx_version=nx.__version__,
        qualification=(
            "Synthetic fixed-topology functional experiment. NetworkX results "
            "validate controller correctness; CCH results measure this binding "
            "with degree ordering. Neither establishes Chennai traffic outcomes."
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{config.engine}_{config.update_mode}"
    query_path = output_dir / f"lazy_sync_queries_{suffix}.csv"
    with query_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary_path = output_dir / f"lazy_sync_summary_{suffix}.json"
    summary_path.write_text(
        json.dumps(asdict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary
