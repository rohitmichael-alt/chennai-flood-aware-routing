"""NetworkX reference engine implementing the metric-snapshot protocol."""

from __future__ import annotations

import hashlib
import math
from numbers import Real

import networkx as nx

from chennai_routing.routing.engine import (
    EdgeId,
    EngineCapabilities,
    EnginePath,
    EngineQuery,
    MetricSnapshot,
    NodeId,
    SyncReport,
    Weight,
)


def _topology_digest(graph: nx.MultiDiGraph) -> str:
    nodes = sorted(repr(node) for node in graph.nodes)
    edges = sorted(repr((u, v, key)) for u, v, key in graph.edges(keys=True))
    payload = "\n".join(["nodes", *nodes, "edges", *edges]).encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_weight(weight: Weight) -> None:
    if isinstance(weight, bool) or not isinstance(weight, Real):
        raise TypeError("Weights must be real numbers.")
    value = float(weight)
    if math.isnan(value) or value == -math.inf or value < 0:
        raise ValueError("Weights must be non-negative and not NaN.")


class NetworkXDijkstraEngine:
    """Exact reference engine for a fixed directed multigraph."""

    _WEIGHT_ATTRIBUTE = "_represented_weight"

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        if not isinstance(graph, nx.MultiDiGraph):
            raise TypeError("NetworkXDijkstraEngine requires a networkx.MultiDiGraph.")
        self._nodes = tuple(graph.nodes)
        self._edge_ids = frozenset(
            (u, v, key) for u, v, key in graph.edges(keys=True)
        )
        self._topology_id = _topology_digest(graph)
        self._metric_version: int | None = None
        self._weights: dict[EdgeId, Weight] = {}
        self._weighted_graph = nx.MultiDiGraph()
        self._weighted_graph.add_nodes_from(self._nodes)

    @property
    def topology_id(self) -> str:
        return self._topology_id

    @property
    def metric_version(self) -> int | None:
        return self._metric_version

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            name="networkx-dijkstra",
            exact_for_represented_metric=True,
        )

    @property
    def edge_ids(self) -> frozenset[EdgeId]:
        return self._edge_ids

    def synchronize(self, metric: MetricSnapshot) -> SyncReport:
        if metric.topology_id != self._topology_id:
            raise ValueError("Metric topology does not match the engine topology.")
        if metric.version < 0:
            raise ValueError("Metric version must be non-negative.")
        if set(metric.weights) != set(self._edge_ids):
            missing = self._edge_ids.difference(metric.weights)
            extra = set(metric.weights).difference(self._edge_ids)
            raise ValueError(
                f"Metric must contain exactly the topology edges; "
                f"missing={len(missing)}, extra={len(extra)}."
            )

        new_weights = dict(metric.weights)
        for weight in new_weights.values():
            _validate_weight(weight)

        new_graph = nx.MultiDiGraph()
        new_graph.add_nodes_from(self._nodes)
        for edge, weight in new_weights.items():
            if math.isinf(float(weight)):
                continue
            u, v, key = edge
            new_graph.add_edge(
                u,
                v,
                key=key,
                **{self._WEIGHT_ATTRIBUTE: weight},
            )

        previous_version = self._metric_version
        self._weights = new_weights
        self._weighted_graph = new_graph
        self._metric_version = metric.version
        return SyncReport(
            previous_version=previous_version,
            metric_version=metric.version,
            edge_count=len(new_weights),
        )

    def query(self, source: NodeId, target: NodeId) -> EngineQuery:
        if self._metric_version is None:
            raise RuntimeError("The engine must be synchronized before querying.")
        if source not in self._weighted_graph or target not in self._weighted_graph:
            raise ValueError("Source and target must exist in the fixed topology.")
        if source == target:
            return EngineQuery(
                status="FOUND",
                path=EnginePath(nodes=(source,), edges=(), cost=0),
            )

        try:
            nodes = tuple(
                nx.shortest_path(
                    self._weighted_graph,
                    source,
                    target,
                    weight=self._WEIGHT_ATTRIBUTE,
                    method="dijkstra",
                )
            )
        except nx.NetworkXNoPath:
            return EngineQuery(status="UNREACHABLE", path=None)

        edges: list[EdgeId] = []
        cost: Weight = 0
        for u, v in zip(nodes[:-1], nodes[1:]):
            candidates = self._weighted_graph.get_edge_data(u, v)
            if not candidates:
                raise RuntimeError("Engine returned a node path containing a non-edge.")
            key, data = min(
                candidates.items(),
                key=lambda item: (
                    item[1][self._WEIGHT_ATTRIBUTE],
                    repr(item[0]),
                ),
            )
            edge = (u, v, key)
            edges.append(edge)
            cost += self._weights[edge]

        return EngineQuery(
            status="FOUND",
            path=EnginePath(nodes=nodes, edges=tuple(edges), cost=cost),
        )
