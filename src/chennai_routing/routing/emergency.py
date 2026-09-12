"""Transparent Stage 9 emergency-route policy for controlled scenarios.

The policy contains no signal pre-emption and uses no live fleet data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chennai_routing.routing.engine import EdgeId


@dataclass(frozen=True)
class EmergencyPolicy:
    deadline_seconds: float
    ordinary_delay_cap_seconds: float
    classification: str = "SCENARIO"

    def __post_init__(self) -> None:
        if not math.isfinite(self.deadline_seconds) or self.deadline_seconds < 0:
            raise ValueError("deadline_seconds must be finite and non-negative.")
        if (
            not math.isfinite(self.ordinary_delay_cap_seconds)
            or self.ordinary_delay_cap_seconds < 0
        ):
            raise ValueError("ordinary_delay_cap_seconds must be finite and non-negative.")
        if self.classification != "SCENARIO":
            raise ValueError("Uncalibrated emergency targets must remain SCENARIO.")


@dataclass(frozen=True)
class EmergencyRouteCandidate:
    route_id: str
    edges: tuple[EdgeId, ...]
    arrival_seconds: float
    blocked_edge_count: int
    severe_edge_count: int
    ordinary_external_delay_seconds: float

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route_id must not be empty.")
        if self.blocked_edge_count < 0 or self.severe_edge_count < 0:
            raise ValueError("Edge exposure counts must be non-negative.")
        for value in (self.arrival_seconds, self.ordinary_external_delay_seconds):
            if not math.isfinite(value) or value < 0:
                raise ValueError("Time values must be finite and non-negative.")


def select_emergency_route(
    candidates: tuple[EmergencyRouteCandidate, ...],
    policy: EmergencyPolicy,
) -> EmergencyRouteCandidate:
    """Select by safety, deadline/arrival, bounded external delay, stable ties."""

    if not candidates:
        raise ValueError("At least one emergency route candidate is required.")
    feasible = tuple(candidate for candidate in candidates if candidate.blocked_edge_count == 0)
    pool = feasible or candidates
    minimum_severe = min(candidate.severe_edge_count for candidate in pool)
    pool = tuple(candidate for candidate in pool if candidate.severe_edge_count == minimum_severe)
    within_delay_cap = tuple(
        candidate
        for candidate in pool
        if candidate.ordinary_external_delay_seconds <= policy.ordinary_delay_cap_seconds
    )
    pool = within_delay_cap or pool

    def rank(candidate: EmergencyRouteCandidate) -> tuple[object, ...]:
        lateness = max(0.0, candidate.arrival_seconds - policy.deadline_seconds)
        return (
            candidate.blocked_edge_count,
            candidate.severe_edge_count,
            lateness > 0,
            lateness,
            candidate.arrival_seconds,
            candidate.ordinary_external_delay_seconds,
            candidate.route_id,
            repr(candidate.edges),
        )

    return min(pool, key=rank)
