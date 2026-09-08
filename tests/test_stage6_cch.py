from types import MappingProxyType

import networkx as nx
import pytest

from chennai_routing.preprocessing.roads import parse_explicit_osm_maxspeed_kph
from chennai_routing.routing.engine import MetricSnapshot
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine
from chennai_routing.routing.quantization import (
    QuantizationPolicy,
    bbox_diameter_m,
    geographic_overflow_bound_ms,
    path_quantization_error_bound_ms,
    quantize_travel_time_ms,
    travel_time_seconds,
)
from chennai_routing.stage6_cch import (
    TURN_MODEL_DECISION,
    build_quantized_weights,
    decide_turn_model,
    evaluate_graph,
    sample_od_pairs,
)


def _coord_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_node("A", x=80.27, y=13.08)
    graph.add_node("B", x=80.28, y=13.08)
    graph.add_node("C", x=80.28, y=13.09)
    graph.add_node("D", x=80.27, y=13.09)
    graph.add_edge("A", "B", key=0, length=100.0, maxspeed="36", stage3_arc_id="ab")
    graph.add_edge("B", "C", key=0, length=100.0, maxspeed="36", stage3_arc_id="bc")
    graph.add_edge("C", "D", key=0, length=100.0, maxspeed="36", stage3_arc_id="cd")
    graph.add_edge("D", "A", key=0, length=100.0, maxspeed="36", stage3_arc_id="da")
    graph.add_edge("A", "C", key=0, length=200.0, maxspeed="36", stage3_arc_id="ac")
    return graph


def test_quantize_100m_at_36_kph_is_exactly_10_seconds() -> None:
    assert travel_time_seconds(100.0, 36.0) == 10.0
    assert quantize_travel_time_ms(100.0, 36.0) == 10_000


def test_path_quantization_error_grows_linearly_with_arc_count() -> None:
    policy = QuantizationPolicy()
    assert path_quantization_error_bound_ms(0, policy) == 0.0
    assert path_quantization_error_bound_ms(4, policy) == 2.0


def test_geographic_bound_is_below_routingkit_infinity() -> None:
    diameter = bbox_diameter_m(80.0, 12.9, 80.4, 13.3)
    bound = geographic_overflow_bound_ms(
        diameter_m=diameter,
        min_speed_kph=30.0,
        max_arc_ms=12_000,
    )
    assert diameter > 10_000
    assert int(bound["bound_ms"]) > 12_000
    assert int(bound["bound_ms"]) < 2**31 - 1
    assert bound["classification"] == "SCENARIO"


def test_turn_model_is_restricted_when_restrictions_are_absent() -> None:
    decision = decide_turn_model(_coord_graph())
    assert decision["decision"] == TURN_MODEL_DECISION
    assert decision["classification"] == "UNAVAILABLE"
    assert decision["restriction_attribute_count"] == 0


def test_missing_maxspeed_is_labelled_scenario() -> None:
    graph = _coord_graph()
    graph.add_edge("B", "D", key=0, length=150.0, maxspeed="", stage3_arc_id="bd")
    bundle = build_quantized_weights(graph)
    assert bundle["scenario_speed_count"] == 1
    assert bundle["observed_speed_count"] == 5
    assert bundle["classifications"][("B", "D", 0)] == "SCENARIO"


def test_sample_od_pairs_are_deterministic() -> None:
    nodes = ["A", "B", "C", "D"]
    first = sample_od_pairs(nodes, 3, seed=8597)
    second = sample_od_pairs(nodes, 3, seed=8597)
    assert first == second
    assert len(set(first)) == 3
    assert all(source != target for source, target in first)


def test_inertial_cch_matches_dijkstra_on_tiny_graph() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = _coord_graph()
    bundle = build_quantized_weights(graph)
    cch = RoutingKitCCHEngine(
        graph,
        order_method="inertial",
        max_finite_weight=int(bundle["overflow"]["bound_ms"]),
    )
    dijkstra = NetworkXDijkstraEngine(graph)
    snapshot_cch = MetricSnapshot(
        topology_id=cch.topology_id,
        version=0,
        weights=MappingProxyType(bundle["weights"]),
    )
    snapshot_dij = MetricSnapshot(
        topology_id=dijkstra.topology_id,
        version=0,
        weights=MappingProxyType(bundle["weights"]),
    )
    cch.synchronize(snapshot_cch)
    dijkstra.synchronize(snapshot_dij)
    cch_result = cch.query("A", "C")
    dij_result = dijkstra.query("A", "C")
    assert cch.order_method == "inertial"
    assert cch_result.status == dij_result.status == "FOUND"
    assert cch_result.path is not None
    assert dij_result.path is not None
    assert cch_result.path.cost == dij_result.path.cost


def test_declared_overflow_accepts_millisecond_city_weights() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = nx.MultiDiGraph()
    graph.add_node(0, x=80.0, y=13.0)
    graph.add_node(1, x=80.1, y=13.0)
    graph.add_edge(0, 1, key=0)
    engine = RoutingKitCCHEngine(graph, max_finite_weight=120_000)
    engine.synchronize(
        MetricSnapshot(
            topology_id=engine.topology_id,
            version=0,
            weights={(0, 1, 0): 120_000},
        )
    )
    result = engine.query(0, 1)
    assert result.path is not None
    assert result.path.cost == 120_000


def test_simple_path_bound_still_rejects_overflow() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0)
    graph.add_edge(1, 2, key=0)
    engine = RoutingKitCCHEngine(graph)
    maximum = engine.capabilities.max_finite_weight
    assert maximum is not None
    with pytest.raises(ValueError, match="conservative bound"):
        engine.synchronize(
            MetricSnapshot(
                topology_id=engine.topology_id,
                version=0,
                weights={(0, 1, 0): maximum + 1, (1, 2, 0): 1},
            )
        )


def test_finite_closure_sentinel_avoids_closed_arc_when_alternative_exists() -> None:
    pytest.importorskip("routingkit_cch")
    graph = _coord_graph()
    evaluation = evaluate_graph(
        graph,
        differential_query_count=4,
        cch_query_count=4,
        seed=8597,
        closed_arc_ids=["ac"],
        order_method="inertial",
    )
    assert evaluation["differential"]["mismatch_count"] == 0
    assert evaluation["closure"]["mismatch_count"] == 0
    assert evaluation["closure"]["paths_using_closed_edge"] == 0
    assert evaluation["closure"]["recovery_mismatch_count"] == 0


def test_evaluate_graph_writes_osm_to_cch_maps() -> None:
    pytest.importorskip("routingkit_cch")
    graph = _coord_graph()
    evaluation = evaluate_graph(
        graph,
        differential_query_count=3,
        cch_query_count=3,
        seed=7,
        order_method="inertial",
    )
    maps = evaluation["maps"]
    assert maps["node_count"] == 4
    assert maps["arc_count"] == 5
    assert {row["osm_id"] for row in maps["nodes"]} == {"A", "B", "C", "D"}
    assert {row["stage3_arc_id"] for row in maps["arcs"]} == {
        "ab",
        "bc",
        "cd",
        "da",
        "ac",
    }


def test_explicit_speed_parser_still_rejects_compound_values() -> None:
    assert parse_explicit_osm_maxspeed_kph("40") == 40.0
    assert parse_explicit_osm_maxspeed_kph("40;50") is None
