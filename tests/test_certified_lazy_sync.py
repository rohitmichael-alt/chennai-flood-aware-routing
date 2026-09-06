import math
from pathlib import Path
from types import MappingProxyType

import networkx as nx
import pytest

from chennai_routing.evaluation.experiments import (
    LazySyncExperimentConfig,
    run_certified_lazy_experiment,
)
from chennai_routing.routing.dynamic import (
    CertificateTolerance,
    CertifiedLazySynchronizer,
    WeightUpdateBatch,
)
from chennai_routing.routing.engine import MetricSnapshot
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine


def _three_road_system() -> tuple[CertifiedLazySynchronizer, dict]:
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(("S", "T"))
    graph.add_edge("S", "T", key="A")
    graph.add_edge("S", "T", key="B")
    graph.add_edge("S", "T", key="C")
    engine = NetworkXDijkstraEngine(graph)
    weights = {
        ("S", "T", "A"): 5_000,
        ("S", "T", "B"): 6_000,
        ("S", "T", "C"): 8_000,
    }
    snapshot = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights=MappingProxyType(weights),
    )
    return (
        CertifiedLazySynchronizer(
            engine,
            snapshot,
            tolerance=CertificateTolerance(5, 100),
        ),
        weights,
    )


def _batch(
    base: int,
    edge: tuple,
    weight: int | float,
) -> WeightUpdateBatch:
    return WeightUpdateBatch(
        base_version=base,
        version=base + 1,
        replacements=((edge, weight),),
    )


def test_current_query_uses_road_a() -> None:
    router, _ = _three_road_system()

    result = router.route("S", "T")

    assert result.decision == "CURRENT"
    assert result.path is not None
    assert result.path.edges == (("S", "T", "A"),)
    assert result.path.cost == 5_000


def test_off_path_increase_is_certified_without_refresh() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "B"), 6_500))

    result = router.route("S", "T")

    assert result.decision == "CERTIFIED_STALE"
    assert result.lower_bound == result.upper_bound == 5_000
    assert router.state().refresh_count == 0


def test_three_road_five_percent_example_passes_at_5200() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "A"), 5_200))

    result = router.route("S", "T")

    assert result.decision == "CERTIFIED_STALE"
    assert result.lower_bound == 5_000
    assert result.upper_bound == 5_200
    assert result.path is not None and result.path.cost == 5_200


def test_three_road_example_refreshes_at_5800() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "A"), 5_800))

    result = router.route("S", "T")

    assert result.decision == "REFRESHED"
    assert result.refresh_reason == "certificate_failed"
    assert result.path is not None
    assert result.path.edges == (("S", "T", "A"),)
    assert result.path.cost == 5_800
    assert router.state().refresh_count == 1


def test_refresh_can_switch_to_road_b() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "A"), 7_000))

    result = router.route("S", "T")

    assert result.path is not None
    assert result.path.edges == (("S", "T", "B"),)
    assert result.path.cost == 6_000


def test_decrease_below_synchronized_weight_forces_refresh() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "B"), 4_000))

    result = router.route("S", "T")

    assert result.decision == "REFRESHED"
    assert result.refresh_reason == "lower_bound_invalidated"
    assert result.path is not None
    assert result.path.edges == (("S", "T", "B"),)


def test_decrease_that_stays_above_synchronized_weight_preserves_bound() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "B"), 8_000))
    router.apply_updates(_batch(1, ("S", "T", "B"), 7_000))

    result = router.route("S", "T")

    assert result.decision == "CERTIFIED_STALE"
    assert router.state().lower_bound_violation_count == 0


def test_closure_refreshes_and_reopening_forces_refresh() -> None:
    router, _ = _three_road_system()
    router.apply_updates(_batch(0, ("S", "T", "A"), math.inf))
    closed = router.route("S", "T")
    assert closed.path is not None
    assert closed.path.edges == (("S", "T", "B"),)

    router.apply_updates(_batch(1, ("S", "T", "A"), 4_500))
    reopened = router.route("S", "T")
    assert reopened.refresh_reason == "lower_bound_invalidated"
    assert reopened.path is not None
    assert reopened.path.edges == (("S", "T", "A"),)


def test_unreachable_under_stale_metric_stays_unreachable_under_increases() -> None:
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(("S", "U", "T"))
    graph.add_edge("S", "U", key=0)
    engine = NetworkXDijkstraEngine(graph)
    edge = ("S", "U", 0)
    metric = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights={edge: 10},
    )
    router = CertifiedLazySynchronizer(engine, metric)
    router.apply_updates(_batch(0, edge, 20))

    result = router.route("S", "T")

    assert result.status == "UNREACHABLE"
    assert result.decision == "CERTIFIED_UNREACHABLE"


def test_source_equals_target_has_zero_cost() -> None:
    router, _ = _three_road_system()
    result = router.route("S", "S")
    assert result.path is not None
    assert result.path.nodes == ("S",)
    assert result.path.edges == ()
    assert result.path.cost == 0


@pytest.mark.parametrize("bad_weight", [-1, float("nan"), 1.5, -math.inf])
def test_bad_update_is_rejected_atomically(bad_weight: float) -> None:
    router, weights = _three_road_system()

    with pytest.raises((TypeError, ValueError)):
        router.apply_updates(_batch(0, ("S", "T", "A"), bad_weight))

    assert router.state().current_version == 0
    assert dict(router.current_weights) == weights


def test_duplicate_and_out_of_order_updates_are_rejected() -> None:
    router, _ = _three_road_system()
    edge = ("S", "T", "A")
    duplicate = WeightUpdateBatch(
        base_version=0,
        version=1,
        replacements=((edge, 5_100), (edge, 5_200)),
    )
    with pytest.raises(ValueError, match="duplicate"):
        router.apply_updates(duplicate)
    with pytest.raises(ValueError, match="base version"):
        router.apply_updates(_batch(3, edge, 5_100))


def test_seeded_experiment_has_no_certificate_or_exact_mismatch(
    tmp_path: Path,
) -> None:
    for mode in ("increases_only", "mixed"):
        summary = run_certified_lazy_experiment(
            LazySyncExperimentConfig(
                seed=12,
                node_count=15,
                extra_edge_count=20,
                epochs=5,
                updates_per_epoch=2,
                queries_per_epoch=10,
                update_mode=mode,
                engine="networkx",
            ),
            tmp_path,
        )
        assert summary.certificate_violation_count == 0
        assert summary.exact_after_refresh_mismatch_count == 0
        assert summary.engine_oracle_mismatch_count == 0
        assert summary.query_count == 50
        assert list(
            tmp_path.glob(f"lazy_sync_summary_networkx_{mode}_*.json")
        )


def test_native_cch_matches_dijkstra_on_keyed_parallel_edges() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = nx.MultiDiGraph()
    graph.add_nodes_from(("S", "M", "T"))
    graph.add_edge("S", "T", key="slow")
    graph.add_edge("S", "M", key="first")
    graph.add_edge("S", "M", key="slower_parallel")
    graph.add_edge("M", "T", key="second")
    weights = {
        ("S", "T", "slow"): 20,
        ("S", "M", "first"): 5,
        ("S", "M", "slower_parallel"): 9,
        ("M", "T", "second"): 6,
    }
    cch = RoutingKitCCHEngine(graph)
    dijkstra = NetworkXDijkstraEngine(graph)
    for engine in (cch, dijkstra):
        engine.synchronize(
            MetricSnapshot(
                topology_id=engine.topology_id,
                version=0,
                weights=weights,
            )
        )

    cch_result = cch.query("S", "T")
    dijkstra_result = dijkstra.query("S", "T")

    assert cch_result == dijkstra_result
    assert cch_result.path is not None
    assert cch_result.path.edges == (
        ("S", "M", "first"),
        ("M", "T", "second"),
    )


def test_native_cch_experiment_has_no_certificate_violation(
    tmp_path: Path,
) -> None:
    pytest.importorskip("routingkit_cch")
    summary = run_certified_lazy_experiment(
        LazySyncExperimentConfig(
            seed=19,
            node_count=20,
            extra_edge_count=30,
            epochs=4,
            updates_per_epoch=2,
            queries_per_epoch=10,
            update_mode="increases_only",
            engine="cch",
        ),
        tmp_path,
    )
    assert summary.certificate_violation_count == 0
    assert summary.exact_after_refresh_mismatch_count == 0
    assert summary.engine_oracle_mismatch_count == 0


def test_cch_safe_weight_bound_prevents_infinity_collision() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, key=0)
    graph.add_edge(1, 2, key=0)
    engine = RoutingKitCCHEngine(graph)
    maximum = engine.capabilities.max_finite_weight
    assert maximum is not None
    valid = MetricSnapshot(
        topology_id=engine.topology_id,
        version=0,
        weights={(0, 1, 0): maximum, (1, 2, 0): maximum},
    )
    engine.synchronize(valid)
    result = engine.query(0, 2)
    assert result.path is not None
    assert result.path.cost == maximum * 2

    with pytest.raises(ValueError, match="safe finite maximum"):
        engine.synchronize(
            MetricSnapshot(
                topology_id=engine.topology_id,
                version=1,
                weights={(0, 1, 0): maximum + 1, (1, 2, 0): 1},
            )
        )


def test_cch_closure_update_is_rejected_before_state_commit() -> None:
    pytest.importorskip("routingkit_cch")
    from chennai_routing.routing.cch_engine import RoutingKitCCHEngine

    graph = nx.MultiDiGraph()
    graph.add_edge("S", "T", key=0)
    engine = RoutingKitCCHEngine(graph)
    edge = ("S", "T", 0)
    router = CertifiedLazySynchronizer(
        engine,
        MetricSnapshot(
            topology_id=engine.topology_id,
            version=0,
            weights={edge: 10},
        ),
    )

    with pytest.raises(ValueError, match="does not support"):
        router.apply_updates(_batch(0, edge, math.inf))

    assert router.state().current_version == 0
    assert router.current_weights[edge] == 10


@pytest.mark.parametrize(
    "numerator,denominator",
    [(5.0, 100), (5, 100.0), (True, 100), (5, False)],
)
def test_certificate_tolerance_requires_exact_integers(
    numerator: object,
    denominator: object,
) -> None:
    with pytest.raises(TypeError):
        CertificateTolerance(numerator, denominator)  # type: ignore[arg-type]


def test_engine_rejects_metric_version_rollback() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, key=0)
    engine = NetworkXDijkstraEngine(graph)
    for version in (2, 1):
        metric = MetricSnapshot(
            topology_id=engine.topology_id,
            version=version,
            weights={(1, 2, 0): 5},
        )
        if version == 2:
            engine.synchronize(metric)
        else:
            with pytest.raises(ValueError, match="backwards"):
                engine.synchronize(metric)


def test_topology_identifier_is_insertion_order_independent() -> None:
    first = nx.MultiDiGraph()
    first.add_nodes_from((1, "1", ("zone", 2)))
    first.add_edge(1, "1", key="road")
    second = nx.MultiDiGraph()
    second.add_nodes_from((("zone", 2), "1", 1))
    second.add_edge(1, "1", key="road")

    assert (
        NetworkXDijkstraEngine(first).topology_id
        == NetworkXDijkstraEngine(second).topology_id
    )


def test_topology_identifier_rejects_unstable_custom_objects() -> None:
    class UnstableId:
        pass

    graph = nx.MultiDiGraph()
    graph.add_node(UnstableId())
    with pytest.raises(TypeError, match="stable primitive"):
        NetworkXDijkstraEngine(graph)
