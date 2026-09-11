from types import MappingProxyType

import math
import networkx as nx
import pytest

from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.models.capacity import effective_capacity
from chennai_routing.models.pathway import ExplainedArcState, integer_metric_from_states
from chennai_routing.routing.dynamic import (
    CertificateTolerance,
    CertifiedLazySynchronizer,
    WeightUpdateBatch,
)
from chennai_routing.evaluation.baseline import EagerRefreshRouter
from chennai_routing.routing.engine import EnginePath, MetricSnapshot
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine
from chennai_routing.routing.quantization import quantize_seconds
from chennai_routing.routing.rerouting import AdoptionThresholds, decide_route_adoption
from chennai_routing.stage1_poc import apply_stage1_costs, select_route_change_edge


def test_bpr_rejects_nonfinite_parameters() -> None:
    with pytest.raises(ValueError):
        bpr_travel_time(10, 1, 10, alpha=float("nan"))
    with pytest.raises(ValueError):
        bpr_travel_time(10, 1, 10, beta=-1)


def test_unknown_capacity_is_rejected() -> None:
    with pytest.raises(ValueError, match="UNKNOWN"):
        effective_capacity(1000, "UNKNOWN")
    assert effective_capacity(1000, "NORMAL", flood_multiplier=0.5, incident_multiplier=0.5) == 250
    assert effective_capacity(1000, "NORMAL", closed=True) == 0
    assert effective_capacity(1000, "DEGRADED", minimum_capacity=800) == 800


def test_degradation_skips_cooldown() -> None:
    adopted = EnginePath(nodes=("S", "T"), edges=(("S", "T", 0),), cost=100)
    worse = EnginePath(nodes=("S", "T"), edges=(("S", "T", 1),), cost=120)
    decision = decide_route_adoption(
        adopted=adopted,
        candidate=worse,
        epoch=3,
        last_change_epoch=2,
        thresholds=AdoptionThresholds(degradation=0.15, minimum_gain=0.05, cooldown_epochs=2),
    )
    assert decision.adopt is True
    assert decision.reason == "degradation"


def test_quantize_seconds_rounds_to_milliseconds() -> None:
    assert quantize_seconds(1.234) == 1234
    with pytest.raises(ValueError):
        quantize_seconds(math.inf)


def test_select_route_change_edge_preserves_before_graph() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0, length=10.0, travel_time=10.0)
    graph.add_edge(1, 3, key=0, length=10.0, travel_time=11.0)
    graph.add_edge(3, 4, key=0, length=10.0, travel_time=11.0)
    graph.add_edge(4, 2, key=0, length=10.0, travel_time=11.0)
    import geopandas as gpd
    from shapely.geometry import Point

    affected = gpd.GeoDataFrame(
        {"u": [1], "v": [2], "key": [0], "distance_to_road_m": [1.0]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    apply_stage1_costs(graph)
    before_weight = graph[1][2][0]["stage1_weight"]
    edge, before, after, before_cost, after_cost = select_route_change_edge(graph, affected)
    assert edge == (1, 2, 0)
    assert graph[1][2][0]["stage1_weight"] == before_weight
    assert math.isfinite(graph[1][2][0]["stage1_weight"])
    assert before == [1, 2]
    assert after == [1, 3, 4, 2]
    assert after_cost > before_cost


def test_empty_update_batch_is_rejected() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("S", "T", key=0)
    engine = NetworkXDijkstraEngine(graph)
    snapshot = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights=MappingProxyType({("S", "T", 0): 10}),
    )
    router = CertifiedLazySynchronizer(engine, snapshot, tolerance=CertificateTolerance(5, 100))
    with pytest.raises(ValueError, match="at least one replacement"):
        router.apply_updates(WeightUpdateBatch(0, 1, ()))


def test_eager_identity_update_does_not_bump_version() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("S", "T", key=0)
    engine = NetworkXDijkstraEngine(graph)
    snapshot = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights=MappingProxyType({("S", "T", 0): 10}),
    )
    eager = EagerRefreshRouter(engine, snapshot)
    eager.apply_updates(WeightUpdateBatch(0, 1, ((("S", "T", 0), 10),)))
    assert eager.state().metric_version == 0
    assert eager.state().synchronization_count == 1


def test_identity_update_does_not_bump_version() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("S", "T", key=0)
    engine = NetworkXDijkstraEngine(graph)
    snapshot = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights=MappingProxyType({("S", "T", 0): 10}),
    )
    router = CertifiedLazySynchronizer(engine, snapshot)
    receipt = router.apply_updates(WeightUpdateBatch(0, 1, ((("S", "T", 0), 10),)))
    assert receipt.version == 0
    assert router.state().current_version == router.state().synchronized_version == 0


def test_pathway_bpr_snapshot_enters_certificate_controller() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("S", "A", key=0)
    graph.add_edge("A", "T", key=0)
    graph.add_edge("S", "T", key=0)
    states = {
        ("S", "A", 0): ExplainedArcState(
            ("S", "A", 0), "NORMAL", 0.0, 10.0, 1200.0, "SCENARIO", "fast"
        ),
        ("A", "T", 0): ExplainedArcState(
            ("A", "T", 0), "NORMAL", 0.0, 10.0, 1200.0, "SCENARIO", "fast"
        ),
        ("S", "T", 0): ExplainedArcState(
            ("S", "T", 0), "BLOCKED", 0.0, 5.0, 1200.0, "SCENARIO", "direct"
        ),
    }
    snapshot, classes = integer_metric_from_states(graph, states)
    assert classes[("S", "T", 0)] == "SCENARIO"
    engine = NetworkXDijkstraEngine(graph)
    aligned = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights=snapshot.weights,
    )
    router = CertifiedLazySynchronizer(engine, aligned)
    result = router.route("S", "T")
    assert result.status == "FOUND"
    assert result.path is not None
    assert result.path.edges == (("S", "A", 0), ("A", "T", 0))


def test_adoption_filter_holds_inside_gain_and_cooldown() -> None:
    adopted = EnginePath(nodes=("S", "T"), edges=(("S", "T", 0),), cost=100)
    slightly_better = EnginePath(nodes=("S", "T"), edges=(("S", "T", 1),), cost=98)
    decision = decide_route_adoption(
        adopted=adopted,
        candidate=slightly_better,
        epoch=3,
        last_change_epoch=2,
        thresholds=AdoptionThresholds(degradation=0.15, minimum_gain=0.05, cooldown_epochs=2),
    )
    assert decision.adopt is False
    assert decision.reason == "cooldown"
    big_gain = EnginePath(nodes=("S", "T"), edges=(("S", "T", 1),), cost=80)
    after_cool = decide_route_adoption(
        adopted=adopted,
        candidate=big_gain,
        epoch=5,
        last_change_epoch=2,
        thresholds=AdoptionThresholds(),
    )
    assert after_cool.adopt is True
    assert after_cool.reason == "minimum_gain"
