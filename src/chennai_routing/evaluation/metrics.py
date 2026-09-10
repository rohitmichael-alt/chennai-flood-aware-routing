"""Small, auditable evaluation metrics for accessibility and compliance."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from numbers import Real
from typing import Collection, Hashable, Mapping, Sequence

import networkx as nx

from chennai_routing.routing.engine import EdgeId


@dataclass(frozen=True)
class AccessibilitySummary:
    """Population-weighted access to one declared facility class."""

    origin_count: int
    total_population: float
    connected_population: float
    disconnected_population: float
    disconnected_population_share: float
    connected_weighted_mean_time: float | None
    connected_population_weighted_p50_time: float | None
    connected_population_weighted_p90_time: float | None
    population_weighted_p90_time: float
    population_share_over_threshold: float
    threshold: float


@dataclass(frozen=True)
class RoadCriticalityResult:
    """Facility-access impact caused by closing one directed keyed edge."""

    edge: EdgeId
    baseline_reachable_population: float
    newly_disconnected_population: float
    affected_population: float
    population_weighted_added_time: float
    maximum_added_time: float


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
    connected_times = [time for time, _ in connected]
    connected_weights = [weight for _, weight in connected]
    connected_p50 = (
        _weighted_quantile(connected_times, connected_weights, 0.5)
        if connected_weights
        else None
    )
    connected_p90 = (
        _weighted_quantile(connected_times, connected_weights, 0.9)
        if connected_weights
        else None
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
        connected_population_weighted_p50_time=connected_p50,
        connected_population_weighted_p90_time=connected_p90,
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
    """Select an exact-size compliant cohort reproducibly."""

    if not 0 <= probability <= 1:
        raise ValueError("Compliance probability must lie in [0, 1].")
    if len(set(vehicle_ids)) != len(vehicle_ids):
        raise ValueError("Vehicle identifiers must be unique.")
    rng = random.Random(seed)
    shuffled = list(vehicle_ids)
    rng.shuffle(shuffled)
    compliant_count = math.floor(len(shuffled) * probability + 0.5)
    compliant = set(shuffled[:compliant_count])
    return {vehicle_id: vehicle_id in compliant for vehicle_id in vehicle_ids}


def _nearest_facility_times(
    graph: nx.MultiDiGraph,
    facilities: Collection[Hashable],
    *,
    weight: str,
) -> dict[Hashable, float]:
    reversed_graph = graph.reverse(copy=False)
    return dict(
        nx.multi_source_dijkstra_path_length(
            reversed_graph,
            facilities,
            weight=weight,
        )
    )


def rank_facility_oriented_road_criticality(
    graph: nx.MultiDiGraph,
    *,
    origin_populations: Mapping[Hashable, float],
    facility_nodes: Collection[Hashable],
    candidate_edges: Sequence[EdgeId],
    weight: str = "weight",
) -> tuple[RoadCriticalityResult, ...]:
    """Rank edges by population-weighted nearest-facility access loss.

    This is an evaluation output, not an additional shortest-path penalty.
    """

    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("Road criticality requires a networkx.MultiDiGraph.")
    if not origin_populations:
        raise ValueError("At least one origin population is required.")
    if not facility_nodes:
        raise ValueError("At least one facility node is required.")
    if any(node not in graph for node in origin_populations):
        raise ValueError("Every population origin must exist in the graph.")
    if any(node not in graph for node in facility_nodes):
        raise ValueError("Every facility node must exist in the graph.")
    for population in origin_populations.values():
        if not math.isfinite(population) or population < 0:
            raise ValueError("Population weights must be finite and non-negative.")
    if sum(origin_populations.values()) <= 0:
        raise ValueError("At least one population weight must be positive.")
    if len(set(candidate_edges)) != len(candidate_edges):
        raise ValueError("Candidate edges must be unique.")
    for _, _, _, data in graph.edges(keys=True, data=True):
        edge_weight = data.get(weight)
        if (
            isinstance(edge_weight, bool)
            or not isinstance(edge_weight, Real)
            or not math.isfinite(float(edge_weight))
            or edge_weight < 0
        ):
            raise ValueError(
                f"Every edge must have a finite non-negative `{weight}` value."
            )
    for u, v, key in candidate_edges:
        if not graph.has_edge(u, v, key):
            raise ValueError(f"Candidate edge {(u, v, key)!r} is not in the graph.")

    baseline = _nearest_facility_times(
        graph,
        facility_nodes,
        weight=weight,
    )
    baseline_reachable_population = sum(
        population
        for origin, population in origin_populations.items()
        if math.isfinite(baseline.get(origin, math.inf))
    )
    results: list[RoadCriticalityResult] = []
    for edge in candidate_edges:
        disrupted = graph.copy()
        disrupted.remove_edge(*edge)
        disrupted_times = _nearest_facility_times(
            disrupted,
            facility_nodes,
            weight=weight,
        )
        newly_disconnected_population = 0.0
        affected_population = 0.0
        weighted_added_time = 0.0
        maximum_added_time = 0.0
        for origin, population in origin_populations.items():
            baseline_time = float(baseline.get(origin, math.inf))
            if not math.isfinite(baseline_time):
                continue
            disrupted_time = float(disrupted_times.get(origin, math.inf))
            if not math.isfinite(disrupted_time):
                newly_disconnected_population += population
                affected_population += population
                maximum_added_time = math.inf
                continue
            added_time = max(0.0, disrupted_time - baseline_time)
            if added_time > 0:
                affected_population += population
                weighted_added_time += population * added_time
                if math.isfinite(maximum_added_time):
                    maximum_added_time = max(maximum_added_time, added_time)

        results.append(
            RoadCriticalityResult(
                edge=edge,
                baseline_reachable_population=float(
                    baseline_reachable_population
                ),
                newly_disconnected_population=float(
                    newly_disconnected_population
                ),
                affected_population=float(affected_population),
                population_weighted_added_time=float(weighted_added_time),
                maximum_added_time=float(maximum_added_time),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.newly_disconnected_population,
                result.population_weighted_added_time,
                result.affected_population,
                repr(result.edge),
            ),
            reverse=True,
        )
    )
