import math

import networkx as nx
import pytest

from chennai_routing.evaluation.metrics import (
    rank_facility_oriented_road_criticality,
    seeded_compliance_mask,
    summarize_accessibility,
)
from chennai_routing.evaluation.robustness import (
    perturb_binary_evidence,
    summarize_binary_evidence,
)


def test_population_weighted_accessibility_reports_disconnection() -> None:
    summary = summarize_accessibility(
        [10.0, 20.0, math.inf],
        [100.0, 200.0, 700.0],
        threshold=15.0,
    )

    assert summary.total_population == 1_000
    assert summary.connected_population == 300
    assert summary.disconnected_population_share == 0.7
    assert summary.connected_weighted_mean_time == pytest.approx(50 / 3)
    assert summary.population_weighted_p90_time == math.inf
    assert summary.connected_population_weighted_p50_time == pytest.approx(20.0)
    assert summary.connected_population_weighted_p90_time == pytest.approx(20.0)
    assert summary.population_share_over_threshold == 0.9


def test_accessibility_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        summarize_accessibility([], [], threshold=10)
    with pytest.raises(ValueError):
        summarize_accessibility([10], [0], threshold=10)
    with pytest.raises(ValueError):
        summarize_accessibility([-1], [1], threshold=10)


def test_compliance_mask_is_reproducible_and_bounded() -> None:
    vehicle_ids = list(range(100))
    first = seeded_compliance_mask(vehicle_ids, 0.5, seed=8597)
    second = seeded_compliance_mask(vehicle_ids, 0.5, seed=8597)

    assert first == second
    assert sum(first.values()) == 50
    assert all(
        seeded_compliance_mask(vehicle_ids, 0.0, seed=1)[vehicle] is False
        for vehicle in vehicle_ids
    )
    assert all(
        seeded_compliance_mask(vehicle_ids, 1.0, seed=1)[vehicle] is True
        for vehicle in vehicle_ids
    )


def test_compliance_mask_rejects_bad_probability_and_duplicate_ids() -> None:
    with pytest.raises(ValueError):
        seeded_compliance_mask([1], 1.1, seed=1)
    with pytest.raises(ValueError):
        seeded_compliance_mask([1, 1], 0.5, seed=1)


def test_evidence_lag_and_error_experiment_is_reproducible() -> None:
    truth = [False, False, True, True, False]
    first = perturb_binary_evidence(
        truth,
        lag_steps=2,
        false_positive_rate=0,
        false_negative_rate=0,
        seed=8597,
    )
    second = perturb_binary_evidence(
        truth,
        lag_steps=2,
        false_positive_rate=0,
        false_negative_rate=0,
        seed=8597,
    )

    assert first == second == (None, None, False, False, True)
    summary = summarize_binary_evidence(truth, first)
    assert summary.available_count == 3
    assert summary.unavailable_count == 2
    assert summary.false_negative == 2
    assert summary.false_positive == 1
    assert summary.accuracy_when_available == 0


def test_evidence_error_extremes_flip_all_available_values() -> None:
    truth = [False, True, False, True]
    observed = perturb_binary_evidence(
        truth,
        lag_steps=0,
        false_positive_rate=1,
        false_negative_rate=1,
        seed=1,
    )

    assert observed == (True, False, True, False)
    summary = summarize_binary_evidence(truth, observed)
    assert summary.false_positive == 2
    assert summary.false_negative == 2


def test_facility_road_criticality_ranks_disconnection_first() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("O1", "J", key=0, weight=1)
    graph.add_edge("O2", "J", key=0, weight=1)
    graph.add_edge("J", "F", key=0, weight=1)
    graph.add_edge("O1", "F", key="alternate", weight=10)

    results = rank_facility_oriented_road_criticality(
        graph,
        origin_populations={"O1": 100, "O2": 200},
        facility_nodes={"F"},
        candidate_edges=[
            ("O1", "J", 0),
            ("J", "F", 0),
        ],
    )

    assert results[0].edge == ("J", "F", 0)
    assert results[0].newly_disconnected_population == 200
    assert results[0].affected_population == 300
    assert results[0].population_weighted_added_time == 800
    assert results[0].maximum_added_time == math.inf
    assert results[1].newly_disconnected_population == 0
    assert results[1].population_weighted_added_time == 800


def test_facility_road_criticality_rejects_unknown_edges() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("O", "F", key=0, weight=1)
    with pytest.raises(ValueError, match="not in the graph"):
        rank_facility_oriented_road_criticality(
            graph,
            origin_populations={"O": 1},
            facility_nodes={"F"},
            candidate_edges=[("missing", "F", 0)],
        )


@pytest.mark.parametrize("bad_weight", [None, -1, math.inf, math.nan])
def test_facility_road_criticality_rejects_invalid_edge_weights(
    bad_weight: object,
) -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("O", "F", key=0, weight=bad_weight)
    with pytest.raises(ValueError, match="finite non-negative"):
        rank_facility_oriented_road_criticality(
            graph,
            origin_populations={"O": 1},
            facility_nodes={"F"},
            candidate_edges=[("O", "F", 0)],
        )
