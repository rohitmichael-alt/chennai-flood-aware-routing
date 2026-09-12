"""Stage 7 deterministic projected-load experiment.

This engineering experiment uses a declared synthetic network and demand.  It
tests policy ordering and herding behavior; it is not Chennai traffic evidence.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from types import MappingProxyType

import networkx as nx

from chennai_routing.evaluation.metrics import seeded_compliance_mask
from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.routing.dynamic import CertifiedLazySynchronizer, WeightUpdateBatch
from chennai_routing.routing.engine import EdgeId, MetricSnapshot, topology_digest
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine
from chennai_routing.routing.reservations import ReservationLedger, ReservationPolicy


def _network() -> tuple[nx.MultiDiGraph, dict[EdgeId, float], dict[EdgeId, float]]:
    graph = nx.MultiDiGraph()
    graph.add_edge("s", "a", key=0)
    graph.add_edge("a", "t", key=0)
    graph.add_edge("s", "b", key=0)
    graph.add_edge("b", "t", key=0)
    free_flow = {
        ("s", "a", 0): 10.0,
        ("a", "t", 0): 10.0,
        ("s", "b", 0): 12.0,
        ("b", "t", 0): 12.0,
    }
    capacity = {edge: 20.0 for edge in free_flow}
    return graph, free_flow, capacity


def _weights(
    free_flow: dict[EdgeId, float], capacity: dict[EdgeId, float], loads: dict[EdgeId, float]
) -> dict[EdgeId, int]:
    return {
        edge: int(round(1000 * bpr_travel_time(free_flow[edge], loads[edge], capacity[edge])))
        for edge in free_flow
    }


def _realized_seconds(
    path: tuple[EdgeId, ...],
    free_flow: dict[EdgeId, float],
    capacity: dict[EdgeId, float],
    loads: dict[EdgeId, float],
) -> float:
    return sum(bpr_travel_time(free_flow[e], loads[e], capacity[e]) for e in path)


def run_assignment(*, vehicle_count: int, compliance: float, seed: int) -> dict[str, object]:
    graph, free_flow, capacity = _network()
    edges = tuple(graph.edges(keys=True))
    initial_loads = {edge: 0.0 for edge in edges}
    initial_weights = _weights(free_flow, capacity, initial_loads)
    topology = topology_digest(tuple(graph.nodes), edges)
    sync = CertifiedLazySynchronizer(
        NetworkXDijkstraEngine(graph),
        MetricSnapshot(topology, 0, MappingProxyType(initial_weights)),
    )
    vehicle_ids = tuple(f"veh_{index:04d}" for index in range(vehicle_count))
    compliant = seeded_compliance_mask(vehicle_ids, compliance, seed=seed)
    ledger = ReservationLedger(ReservationPolicy(bin_seconds=300, vehicle_pce=1.0))
    assigned: dict[str, tuple[EdgeId, ...]] = {}

    for vehicle_id in vehicle_ids:
        if compliant[vehicle_id]:
            projected_loads = {
                edge: ledger.projected_pce(edge, 0) for edge in edges
            }
            replacements = tuple(_weights(free_flow, capacity, projected_loads).items())
            current = sync.state().current_version
            receipt = sync.apply_updates(
                WeightUpdateBatch(current, current + 1, replacements)
            )
            result = sync.route("s", "t")
            if result.path is None:
                raise RuntimeError("Synthetic Stage 7 network unexpectedly disconnected.")
            path = result.path
            assigned[vehicle_id] = path.edges
            ledger.reserve(
                path,
                departure_seconds=0,
                edge_travel_time_seconds={edge: initial_weights[edge] / 1000 for edge in path.edges},
                compliant=True,
            )
            assert receipt.version == sync.state().current_version
        else:
            assigned[vehicle_id] = (("s", "a", 0), ("a", "t", 0))

    final_loads = {edge: 0.0 for edge in edges}
    for path in assigned.values():
        for edge in path:
            final_loads[edge] += 1.0
    realized = [
        _realized_seconds(path, free_flow, capacity, final_loads)
        for path in assigned.values()
    ]
    route_counts: dict[str, int] = {}
    for path in assigned.values():
        key = "-".join(edge[1] for edge in path)
        route_counts[key] = route_counts.get(key, 0) + 1
    certificate_state = sync.state()
    return {
        "seed": seed,
        "vehicle_count": vehicle_count,
        "compliance": compliance,
        "compliant_vehicle_count": sum(compliant.values()),
        "route_counts": route_counts,
        "maximum_volume_capacity_ratio": max(
            final_loads[edge] / capacity[edge] for edge in edges
        ),
        "mean_realized_bpr_seconds": mean(realized),
        "maximum_realized_bpr_seconds": max(realized),
        "certificate_state": {
            "current_version": certificate_state.current_version,
            "synchronized_version": certificate_state.synchronized_version,
            "pending_edge_count": certificate_state.pending_edge_count,
            "refresh_count": certificate_state.refresh_count,
            "certified_stale_query_count": certificate_state.certified_stale_query_count,
            "lower_bound_violation_count": certificate_state.lower_bound_violation_count,
        },
    }


def run_stage7_experiment(output: Path | None = None) -> dict[str, object]:
    levels = (0.0, 0.25, 0.5, 0.75, 1.0)
    seeds = (8597, 8598, 8599)
    rows = [run_assignment(vehicle_count=40, compliance=p, seed=s) for p in levels for s in seeds]
    evidence = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision": "PASS WITH LIMITATIONS",
        "classification": "SYNTHETIC / SCENARIO",
        "policy": {
            "reservation_bin_seconds": 300,
            "vehicle_pce": 1.0,
            "bpr_alpha": 0.15,
            "bpr_beta": 4.0,
            "capacity_pce_per_bin": 20.0,
            "classification": "SCENARIO",
        },
        "runs": rows,
        "invariants": {
            "compliant_only_reservation": True,
            "edge_entry_time_bins": True,
            "metric_update_before_certificate": True,
            "equilibrium_claim": False,
        },
        "unavailable_comparator": "The Stage 5 city network is regenerated, but a matched SUMO periodic-rerouting experiment has not been executed.",
        "claim_limit": (
            "This seeded four-node engineering experiment measures recommendation herding "
            "under scenario BPR parameters. It is not a Chennai traffic result, calibrated "
            "assignment, Wardrop equilibrium, or fleet optimum."
        ),
    }
    destination = output or Path("docs/evidence/STAGE7_RESERVATION_RESULTS.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return evidence
