"""BPR travel-time model for the Stage 1 proof of concept."""

from __future__ import annotations

import math


def bpr_travel_time(
    free_flow_time: float,
    flow: float,
    capacity: float,
    *,
    alpha: float = 0.15,
    beta: float = 4.0,
) -> float:
    """Compute BPR travel time, treating zero capacity as unavailable."""

    if free_flow_time < 0:
        raise ValueError("free_flow_time must be non-negative.")
    if flow < 0:
        raise ValueError("flow must be non-negative.")
    if capacity < 0:
        raise ValueError("capacity must be non-negative.")
    if capacity == 0:
        return math.inf
    return free_flow_time * (1.0 + alpha * ((flow / capacity) ** beta))
