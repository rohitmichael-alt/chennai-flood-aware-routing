"""Capacity-state helpers for the Stage 1 proof of concept."""

from __future__ import annotations

import math


CONDITION_MULTIPLIERS = {
    "NORMAL": 1.0,
    "DEGRADED": 0.7,
    "SEVERE": 0.3,
    "BLOCKED": 0.0,
}


def effective_capacity(normal_capacity: float, road_state: str) -> float:
    """Apply the transparent road-state capacity multiplier."""

    if normal_capacity < 0:
        raise ValueError("normal_capacity must be non-negative.")
    if road_state not in CONDITION_MULTIPLIERS:
        raise ValueError(f"Unsupported road state: {road_state}")
    return normal_capacity * CONDITION_MULTIPLIERS[road_state]


def route_weight_for_state(base_cost: float, road_state: str) -> float:
    """Return infinite cost for blocked roads and base cost otherwise."""

    if road_state == "BLOCKED":
        return math.inf
    return base_cost
