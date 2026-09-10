"""BPR travel-time model.

Default α=0.15 and β=4.0 are US HCM scenario parameters, not Chennai-calibrated
values. Zero capacity is treated as unavailable and does not evaluate BPR.
"""

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

    if free_flow_time < 0 or not math.isfinite(free_flow_time):
        raise ValueError("free_flow_time must be finite and non-negative.")
    if flow < 0 or not math.isfinite(flow):
        raise ValueError("flow must be finite and non-negative.")
    if capacity < 0 or not math.isfinite(capacity):
        raise ValueError("capacity must be finite and non-negative.")
    if not math.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha must be finite and non-negative.")
    if not math.isfinite(beta) or beta < 0:
        raise ValueError("beta must be finite and non-negative.")
    if capacity == 0:
        return math.inf
    return free_flow_time * (1.0 + alpha * ((flow / capacity) ** beta))
