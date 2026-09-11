"""Glue from explained road state to an integer metric snapshot.

This module does not claim Chennai calibration. It makes the documented
evidence → capacity → BPR → millisecond snapshot chain callable on a small
graph so Stage 1 and Stage 2 are no longer disconnected.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

import networkx as nx

from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.models.capacity import effective_capacity
from chennai_routing.routing.engine import EdgeId, MetricSnapshot, topology_digest
from chennai_routing.routing.quantization import quantize_seconds


@dataclass(frozen=True)
class ExplainedArcState:
    """One directed keyed arc's explained state for a routing epoch."""

    edge: EdgeId
    state: str
    assigned_flow: float
    free_flow_time_seconds: float
    normal_capacity: float
    evidence_class: str
    reason: str


def travel_time_seconds(state: ExplainedArcState) -> float:
    """Return BPR seconds, or +inf when the arc is closed."""

    capacity = effective_capacity(state.normal_capacity, state.state)
    return bpr_travel_time(
        state.free_flow_time_seconds,
        state.assigned_flow,
        capacity,
    )


def integer_metric_from_states(
    graph: nx.MultiDiGraph,
    states: Mapping[EdgeId, ExplainedArcState],
    *,
    version: int = 0,
) -> tuple[MetricSnapshot, dict[EdgeId, str]]:
    """Build a complete integer-millisecond snapshot from explained states.

    Closed arcs become +inf. Finite times are rounded to milliseconds.
    Classifications (OBSERVED / SCENARIO) are returned for audit, not used as
    weights.
    """

    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("Pathway metric construction requires a MultiDiGraph.")
    edge_ids = tuple((u, v, key) for u, v, key in graph.edges(keys=True))
    if set(states) != set(edge_ids):
        raise ValueError("Explained states must cover exactly the graph arcs.")
    weights: dict[EdgeId, int | float] = {}
    classes: dict[EdgeId, str] = {}
    for edge in edge_ids:
        seconds = travel_time_seconds(states[edge])
        classes[edge] = states[edge].evidence_class
        if math.isinf(seconds):
            weights[edge] = math.inf
        else:
            weights[edge] = quantize_seconds(seconds)
    snapshot = MetricSnapshot(
        topology_id=topology_digest(tuple(graph.nodes), edge_ids),
        version=version,
        weights=MappingProxyType(weights),
    )
    return snapshot, classes
