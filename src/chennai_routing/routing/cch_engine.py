"""Optional native Customizable Contraction Hierarchies engine adapter."""

from __future__ import annotations

import hashlib
from numbers import Integral

import networkx as nx

from chennai_routing.routing.engine import (
    EdgeId,
    EngineCapabilities,
    EnginePath,
    EngineQuery,
    MetricSnapshot,
    NodeId,
    SyncReport,
)

try:
    import routingkit_cch
except ImportError:  # pragma: no cover - exercised on installations without extra
    routingkit_cch = None


_MAX_ARC_WEIGHT = 2**31 - 1


def _topology_digest(graph: nx.MultiDiGraph) -> str:
    nodes = sorted(repr(node) for node in graph.nodes)
    edges = sorted(repr((u, v, key)) for u, v, key in graph.edges(keys=True))
    payload = "\n".join(["nodes", *nodes, "edges", *edges]).encode()
    return hashlib.sha256(payload).hexdigest()


class RoutingKitCCHEngine:
    """Exact finite-integer CCH adapter for a fixed directed multigraph.

    Degree ordering is suitable for functional benchmarks. A Chennai-scale
    production adapter should use a geometry-aware inertial/nested-dissection
    order and separately validate turn-expanded topology.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        if routingkit_cch is None:
            raise RuntimeError(
                "Install the optional CCH dependency with "
                "`python -m pip install -e '.[cch]'`."
            )
        if not isinstance(graph, nx.MultiDiGraph):
            raise TypeError("RoutingKitCCHEngine requires a networkx.MultiDiGraph.")

        self._nodes = tuple(graph.nodes)
        self._node_to_index = {
            node: index for index, node in enumerate(self._nodes)
        }
        self._edge_ids: tuple[EdgeId, ...] = tuple(
            (u, v, key) for u, v, key in graph.edges(keys=True)
        )
        self._edge_set = frozenset(self._edge_ids)
        tail = [self._node_to_index[edge[0]] for edge in self._edge_ids]
        head = [self._node_to_index[edge[1]] for edge in self._edge_ids]
        order = routingkit_cch.compute_order_degree(
            len(self._nodes),
            tail,
            head,
        )
        self._cch = routingkit_cch.CCH(order, tail, head, False)
        self._metric = None
        self._weights: dict[EdgeId, int] = {}
        self._metric_version: int | None = None
        self._topology_id = _topology_digest(graph)

    @property
    def topology_id(self) -> str:
        return self._topology_id

    @property
    def metric_version(self) -> int | None:
        return self._metric_version

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            name="routingkit-cch",
            exact_for_represented_metric=True,
        )

    def synchronize(self, metric: MetricSnapshot) -> SyncReport:
        if metric.topology_id != self._topology_id:
            raise ValueError("Metric topology does not match the CCH topology.")
        if set(metric.weights) != set(self._edge_set):
            raise ValueError("Metric must contain exactly the CCH topology edges.")

        weights: dict[EdgeId, int] = {}
        vector: list[int] = []
        for edge in self._edge_ids:
            weight = metric.weights[edge]
            if isinstance(weight, bool) or not isinstance(weight, Integral):
                raise TypeError("The CCH represented metric requires integer weights.")
            integer_weight = int(weight)
            if not 0 <= integer_weight <= _MAX_ARC_WEIGHT:
                raise ValueError(
                    "CCH weights must be finite integers between 0 and "
                    f"{_MAX_ARC_WEIGHT}; closures need a validated finite sentinel."
                )
            weights[edge] = integer_weight
            vector.append(integer_weight)

        new_metric = routingkit_cch.CCHMetric(self._cch, vector)
        previous_version = self._metric_version
        self._metric = new_metric
        self._weights = weights
        self._metric_version = metric.version
        return SyncReport(
            previous_version=previous_version,
            metric_version=metric.version,
            edge_count=len(weights),
        )

    def query(self, source: NodeId, target: NodeId) -> EngineQuery:
        if self._metric is None or self._metric_version is None:
            raise RuntimeError("The CCH engine must be synchronized before querying.")
        if source not in self._node_to_index or target not in self._node_to_index:
            raise ValueError("Source and target must exist in the fixed topology.")
        if source == target:
            return EngineQuery(
                status="FOUND",
                path=EnginePath(nodes=(source,), edges=(), cost=0),
            )

        query = routingkit_cch.CCHQuery(self._metric)
        result = query.run(
            self._node_to_index[source],
            self._node_to_index[target],
        )
        distance = result.distance
        if distance is None:
            return EngineQuery(status="UNREACHABLE", path=None)

        arc_ids = tuple(result.arc_path)
        edges = tuple(self._edge_ids[arc_id] for arc_id in arc_ids)
        nodes = tuple(self._nodes[index] for index in result.node_path)
        cost = sum(self._weights[edge] for edge in edges)
        if cost != distance:
            raise RuntimeError(
                "CCH unpacked path cost does not match its represented distance."
            )
        return EngineQuery(
            status="FOUND",
            path=EnginePath(nodes=nodes, edges=edges, cost=cost),
        )
