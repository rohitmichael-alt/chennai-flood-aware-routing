"""Optional native Customizable Contraction Hierarchies engine adapter."""

from __future__ import annotations

from numbers import Integral
from typing import Literal, Mapping, Sequence

import networkx as nx

from chennai_routing.routing.engine import (
    EdgeId,
    EngineCapabilities,
    EnginePath,
    EngineQuery,
    MetricSnapshot,
    NodeId,
    SyncReport,
    topology_digest,
)
from chennai_routing.routing.quantization import ROUTINGKIT_INFINITY

try:
    import routingkit_cch
except ImportError:  # pragma: no cover - exercised on installations without extra
    routingkit_cch = None


OrderMethod = Literal["degree", "inertial"]
OverflowPolicy = Literal["simple_path", "declared"]


def node_latitudes_longitudes(
    graph: nx.MultiDiGraph,
    nodes: Sequence[NodeId],
) -> tuple[list[float], list[float]]:
    """Return WGS84 latitudes and longitudes in CCH node-index order.

    OSM/GraphML convention: ``x`` is longitude, ``y`` is latitude.
    """

    latitudes: list[float] = []
    longitudes: list[float] = []
    for node in nodes:
        data = graph.nodes[node]
        try:
            longitude = float(data["x"])
            latitude = float(data["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Inertial CCH ordering requires numeric node attributes "
                "x (longitude) and y (latitude)."
            ) from exc
        latitudes.append(latitude)
        longitudes.append(longitude)
    return latitudes, longitudes


def compute_contraction_order(
    *,
    node_count: int,
    tails: Sequence[int],
    heads: Sequence[int],
    method: OrderMethod,
    latitudes: Sequence[float] | None = None,
    longitudes: Sequence[float] | None = None,
) -> list[int]:
    """Return a RoutingKit contraction order for one fixed topology."""

    if routingkit_cch is None:
        raise RuntimeError(
            "Install the optional CCH dependency with `python -m pip install -e '.[cch]'`."
        )
    if method == "degree":
        return list(routingkit_cch.compute_order_degree(node_count, list(tails), list(heads)))
    if method != "inertial":
        raise ValueError(f"Unsupported CCH order method: {method}")
    if latitudes is None or longitudes is None:
        raise ValueError("Inertial ordering requires latitude and longitude arrays.")
    if len(latitudes) != node_count or len(longitudes) != node_count:
        raise ValueError("Latitude and longitude arrays must match the node count.")
    return list(
        routingkit_cch.compute_order_inertial(
            node_count,
            list(tails),
            list(heads),
            list(latitudes),
            list(longitudes),
        )
    )


class RoutingKitCCHEngine:
    """Exact finite-integer CCH adapter for a fixed directed multigraph.

    Degree ordering remains the default so existing synthetic tests are
    unchanged. Stage 6 uses inertial (geometry-aware) ordering and a declared
    geographic overflow bound. Turn-expanded topology is not implied.
    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        *,
        order_method: OrderMethod = "degree",
        order: Sequence[int] | None = None,
        max_finite_weight: int | None = None,
        latitudes: Sequence[float] | None = None,
        longitudes: Sequence[float] | None = None,
    ) -> None:
        if routingkit_cch is None:
            raise RuntimeError(
                "Install the optional CCH dependency with "
                "`python -m pip install -e '.[cch]'`."
            )
        if not isinstance(graph, nx.MultiDiGraph):
            raise TypeError("RoutingKitCCHEngine requires a networkx.MultiDiGraph.")
        if not graph.nodes:
            raise ValueError("RoutingKitCCHEngine requires at least one node.")

        self._nodes = tuple(graph.nodes)
        self._node_to_index = {
            node: index for index, node in enumerate(self._nodes)
        }
        self._edge_ids: tuple[EdgeId, ...] = tuple(
            (u, v, key) for u, v, key in graph.edges(keys=True)
        )
        self._edge_to_index = {edge: index for index, edge in enumerate(self._edge_ids)}
        self._edge_set = frozenset(self._edge_ids)
        tail = [self._node_to_index[edge[0]] for edge in self._edge_ids]
        head = [self._node_to_index[edge[1]] for edge in self._edge_ids]
        if latitudes is None and longitudes is None and order_method == "inertial":
            latitudes, longitudes = node_latitudes_longitudes(graph, self._nodes)
        if order is None:
            order = compute_contraction_order(
                node_count=len(self._nodes),
                tails=tail,
                heads=head,
                method=order_method,
                latitudes=latitudes,
                longitudes=longitudes,
            )
        if len(order) != len(self._nodes):
            raise ValueError("Contraction order length must match the node count.")
        self._order_method: OrderMethod = order_method
        self._order = tuple(int(index) for index in order)
        self._cch = routingkit_cch.CCH(list(self._order), tail, head, False)
        self._metric = None
        self._partial_updater = None
        self._weights: dict[EdgeId, int] = {}
        self._metric_version: int | None = None
        self._topology_id = topology_digest(self._nodes, self._edge_ids)
        simple_path_bound = (ROUTINGKIT_INFINITY - 1) // max(1, len(self._nodes) - 1)
        if max_finite_weight is None:
            self._overflow_policy: OverflowPolicy = "simple_path"
            self._max_safe_arc_weight = simple_path_bound
        else:
            if not 0 <= int(max_finite_weight) < ROUTINGKIT_INFINITY:
                raise ValueError(
                    "Declared max_finite_weight must be in "
                    f"[0, {ROUTINGKIT_INFINITY})."
                )
            self._overflow_policy = "declared"
            self._max_safe_arc_weight = int(max_finite_weight)

    @property
    def topology_id(self) -> str:
        return self._topology_id

    @property
    def metric_version(self) -> int | None:
        return self._metric_version

    @property
    def order_method(self) -> OrderMethod:
        return self._order_method

    @property
    def overflow_policy(self) -> OverflowPolicy:
        return self._overflow_policy

    @property
    def node_to_index(self) -> Mapping[NodeId, int]:
        return self._node_to_index

    @property
    def edge_ids(self) -> tuple[EdgeId, ...]:
        return self._edge_ids

    @property
    def nodes(self) -> tuple[NodeId, ...]:
        return self._nodes

    @property
    def contraction_order(self) -> tuple[int, ...]:
        return self._order

    @property
    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            name="routingkit-cch",
            exact_for_represented_metric=True,
            supports_positive_infinity=False,
            max_finite_weight=self._max_safe_arc_weight,
        )

    def synchronize(self, metric: MetricSnapshot) -> SyncReport:
        if metric.topology_id != self._topology_id:
            raise ValueError("Metric topology does not match the CCH topology.")
        if metric.version < 0 or (
            self._metric_version is not None
            and metric.version < self._metric_version
        ):
            raise ValueError(
                "Metric version must be non-negative and cannot move backwards."
            )
        if set(metric.weights) != set(self._edge_set):
            raise ValueError("Metric must contain exactly the CCH topology edges.")

        weights: dict[EdgeId, int] = {}
        vector: list[int] = []
        for edge in self._edge_ids:
            weight = metric.weights[edge]
            integer_weight = self._require_safe_weight(weight)
            weights[edge] = integer_weight
            vector.append(integer_weight)

        new_metric = routingkit_cch.CCHMetric(self._cch, vector)
        previous_version = self._metric_version
        self._metric = new_metric
        self._partial_updater = routingkit_cch.CCHMetricPartialUpdater(self._cch)
        self._weights = weights
        self._metric_version = metric.version
        return SyncReport(
            previous_version=previous_version,
            metric_version=metric.version,
            edge_count=len(weights),
        )

    def reset_metric_vector(self, vector: Sequence[int]) -> None:
        """Replace the customized metric in place without rebuilding the CCH."""

        if self._metric is None:
            raise RuntimeError("The CCH engine must be synchronized before reset.")
        if len(vector) != len(self._edge_ids):
            raise ValueError("Metric vector length must match the CCH arc count.")
        safe = [self._require_safe_weight(weight) for weight in vector]
        self._metric.reset(safe)
        self._weights = {
            edge: weight for edge, weight in zip(self._edge_ids, safe, strict=True)
        }

    def apply_partial_updates(self, replacements: Mapping[EdgeId, int]) -> None:
        """Apply a RoutingKit partial customization for a subset of arcs."""

        if self._metric is None or self._partial_updater is None:
            raise RuntimeError(
                "The CCH engine must be synchronized before partial updates."
            )
        updates: dict[int, int] = {}
        for edge, weight in replacements.items():
            if edge not in self._edge_to_index:
                raise KeyError(f"Partial update refers to an unknown edge: {edge!r}")
            updates[self._edge_to_index[edge]] = self._require_safe_weight(weight)
            self._weights[edge] = updates[self._edge_to_index[edge]]
        self._partial_updater.apply(self._metric, updates)

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

    def _require_safe_weight(self, weight: object) -> int:
        if isinstance(weight, bool) or not isinstance(weight, Integral):
            raise TypeError("The CCH represented metric requires integer weights.")
        integer_weight = int(weight)
        if not 0 <= integer_weight <= self._max_safe_arc_weight:
            if self._overflow_policy == "simple_path":
                raise ValueError(
                    "CCH weights must be finite integers between 0 and "
                    f"{self._max_safe_arc_weight}. This conservative bound keeps "
                    "every simple-path sum below RoutingKit's infinity sentinel; "
                    "closures are unsupported until separately validated."
                )
            raise ValueError(
                "CCH weights must be finite integers between 0 and "
                f"{self._max_safe_arc_weight} under the declared overflow policy."
            )
        return integer_weight
