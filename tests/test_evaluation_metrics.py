import math

import pytest

from chennai_routing.evaluation.metrics import (
    seeded_compliance_mask,
    summarize_accessibility,
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
    assert 30 <= sum(first.values()) <= 70
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
