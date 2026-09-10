"""Capacity-state helpers for explained road states.

Multipliers are labelled SCENARIO values unless a later stage cites a
Chennai calibration. They are not observed 2015 closures.
"""

from __future__ import annotations

from types import MappingProxyType

CONDITION_MULTIPLIERS = MappingProxyType(
    {
        "UNKNOWN": None,
        "NORMAL": 1.0,
        "DEGRADED": 0.7,
        "SEVERE": 0.3,
        "BLOCKED": 0.0,
    }
)

MULTIPLIER_CLASS = "SCENARIO"


def effective_capacity(
    normal_capacity: float,
    road_state: str,
    *,
    flood_multiplier: float | None = None,
    incident_multiplier: float | None = None,
    minimum_capacity: float = 0.0,
    closed: bool = False,
) -> float:
    """Compose flood and incident multipliers, or return 0 for a verified closure.

    Matches the research-document formula:
    0 if closed, otherwise max(c_min, c0 * m_flood * m_incident).
    When only ``road_state`` is supplied, the SCENARIO table is used for both
    flood and incident (incident defaults to 1).
    """

    if normal_capacity < 0:
        raise ValueError("normal_capacity must be non-negative.")
    if minimum_capacity < 0:
        raise ValueError("minimum_capacity must be non-negative.")
    if closed or road_state == "BLOCKED":
        return 0.0
    if road_state not in CONDITION_MULTIPLIERS:
        raise ValueError(f"Unsupported road state: {road_state}")
    state_multiplier = CONDITION_MULTIPLIERS[road_state]
    if state_multiplier is None:
        raise ValueError(
            "UNKNOWN road state cannot be converted to capacity; assign an "
            "explained NORMAL/DEGRADED/SEVERE/BLOCKED state."
        )
    flood = state_multiplier if flood_multiplier is None else flood_multiplier
    incident = 1.0 if incident_multiplier is None else incident_multiplier
    if flood < 0 or incident < 0:
        raise ValueError("Capacity multipliers must be non-negative.")
    composed = normal_capacity * flood * incident
    return max(minimum_capacity, composed)
