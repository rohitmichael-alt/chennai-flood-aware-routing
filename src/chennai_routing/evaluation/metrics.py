"""Small, auditable evaluation metrics for accessibility and compliance."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Hashable, Sequence


@dataclass(frozen=True)
class AccessibilitySummary:
    """Population-weighted access to one declared facility class."""

    origin_count: int
    total_population: float
    connected_population: float
    disconnected_population: float
    disconnected_population_share: float
    connected_weighted_mean_time: float | None
    population_weighted_p90_time: float
    population_share_over_threshold: float
    threshold: float


def _validate_accessibility_inputs(
    travel_times: Sequence[float],
    populations: Sequence[float],
    threshold: float,
) -> None:
    if len(travel_times) != len(populations) or not travel_times:
        raise ValueError(
            "Travel times and populations must have the same non-zero length."
        )
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("Threshold must be a finite non-negative value.")
    for time in travel_times:
        if math.isnan(time) or time < 0:
            raise ValueError("Travel times must be non-negative or positive infinity.")
    for population in populations:
        if not math.isfinite(population) or population < 0:
            raise ValueError("Population weights must be finite and non-negative.")
    if sum(populations) <= 0:
        raise ValueError("At least one population weight must be positive.")


def _weighted_quantile(
    values: Sequence[float],
    weights: Sequence[float],
    quantile: float,
) -> float:
    ranked = sorted(zip(values, weights), key=lambda pair: pair[0])
    target = sum(weights) * quantile
    cumulative = 0.0
    for value, weight in ranked:
        cumulative += weight
        if cumulative >= target:
            return value
    return ranked[-1][0]


def summarize_accessibility(
    travel_times: Sequence[float],
    populations: Sequence[float],
    *,
    threshold: float,
) -> AccessibilitySummary:
    """Summarize nearest-facility travel times without inventing facility capacity."""

    _validate_accessibility_inputs(travel_times, populations, threshold)
    total_population = float(sum(populations))
    connected = [
        (time, population)
        for time, population in zip(travel_times, populations)
        if math.isfinite(time)
    ]
    connected_population = float(sum(weight for _, weight in connected))
    disconnected_population = total_population - connected_population
    weighted_mean = (
        sum(time * weight for time, weight in connected) / connected_population
        if connected_population > 0
        else None
    )
    over_threshold = sum(
        population
        for time, population in zip(travel_times, populations)
        if time > threshold
    )
    return AccessibilitySummary(
        origin_count=len(travel_times),
        total_population=total_population,
        connected_population=connected_population,
        disconnected_population=disconnected_population,
        disconnected_population_share=(
            disconnected_population / total_population
        ),
        connected_weighted_mean_time=weighted_mean,
        population_weighted_p90_time=_weighted_quantile(
            travel_times,
            populations,
            0.9,
        ),
        population_share_over_threshold=over_threshold / total_population,
        threshold=threshold,
    )


def seeded_compliance_mask(
    vehicle_ids: Sequence[Hashable],
    probability: float,
    *,
    seed: int,
) -> dict[Hashable, bool]:
    """Select compliant vehicles reproducibly for a sensitivity experiment."""

    if not 0 <= probability <= 1:
        raise ValueError("Compliance probability must lie in [0, 1].")
    if len(set(vehicle_ids)) != len(vehicle_ids):
        raise ValueError("Vehicle identifiers must be unique.")
    rng = random.Random(seed)
    return {
        vehicle_id: rng.random() < probability
        for vehicle_id in vehicle_ids
    }
