"""Explained road-state assignment for Stage 4.

Capacity multipliers remain labelled SCENARIO values. Rainfall and DEM do not
create BLOCKED states. Historical inventories are not live closures.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import geopandas as gpd
import pandas as pd

ROAD_STATES = ("UNKNOWN", "NORMAL", "DEGRADED", "SEVERE", "BLOCKED")
EVIDENCE_CLASSES = ("OBSERVED", "HISTORICAL_INVENTORY", "MODELLED", "PROXY")

SCENARIO_CAPACITY_MULTIPLIERS = {
    "UNKNOWN": None,
    "NORMAL": 1.0,
    "DEGRADED": 0.7,
    "SEVERE": 0.3,
    "BLOCKED": 0.0,
}

HOTSPOT_BLOCKED_RULE = "historical_hotspot_nearest_edge_blocked_scenario"
INUNDATION_SEVERE_RULE = "historical_inundation_polygon_intersects_edge_scenario"
EXPIRY_RULE = "Historical inventory has no operational expiry; treat as non-current unless a later observation replaces it."


@dataclass(frozen=True)
class RoadStateRow:
    """One explained arc state at one matching-distance scenario."""

    arc_id: str
    u: object
    v: object
    key: object
    state: str
    evidence_class: str
    matching_distance_m: float | None
    source_time: str
    retrieval_time: str
    confidence_basis: str
    expiry_rule: str
    reason: str
    scenario_rule: str
    conflict: bool
    capacity_multiplier: float | None
    multiplier_class: str


def _arc_id(row: pd.Series) -> str:
    if "stage3_arc_id" in row and pd.notna(row.get("stage3_arc_id")):
        return str(row["stage3_arc_id"])
    return f"{row.get('u')}|{row.get('v')}|{row.get('key')}"


def assign_states_from_hotspots(
    mapped_points: gpd.GeoDataFrame,
    *,
    retrieval_time: str,
    source_time: str = "2015",
    matching_distance_m: float,
) -> list[RoadStateRow]:
    """Apply the declared hotspot scenario rule. This is not observed closure."""

    rows: list[RoadStateRow] = []
    if mapped_points.empty:
        return rows
    matched = mapped_points[mapped_points["distance_to_road_m"].notna()]
    for _, row in matched.iterrows():
        rows.append(
            RoadStateRow(
                arc_id=_arc_id(row),
                u=row.get("u"),
                v=row.get("v"),
                key=row.get("key"),
                state="BLOCKED",
                evidence_class="HISTORICAL_INVENTORY",
                matching_distance_m=float(row["distance_to_road_m"]),
                source_time=source_time,
                retrieval_time=retrieval_time,
                confidence_basis=(
                    f"Nearest-road join within {matching_distance_m} m; "
                    "positional accuracy of the KML is unknown."
                ),
                expiry_rule=EXPIRY_RULE,
                reason="Historical flood hotspot mapped to nearest arc under a declared scenario rule.",
                scenario_rule=HOTSPOT_BLOCKED_RULE,
                conflict=False,
                capacity_multiplier=SCENARIO_CAPACITY_MULTIPLIERS["BLOCKED"],
                multiplier_class="SCENARIO",
            )
        )
    return rows


def assign_states_from_inundation(
    intersecting_roads: gpd.GeoDataFrame,
    *,
    retrieval_time: str,
    source_time: str = "2015",
) -> list[RoadStateRow]:
    """Mark polygon-overlapping arcs SEVERE as a scenario, not an observation."""

    rows: list[RoadStateRow] = []
    if intersecting_roads.empty:
        return rows
    for _, row in intersecting_roads.iterrows():
        rows.append(
            RoadStateRow(
                arc_id=_arc_id(row),
                u=row.get("u"),
                v=row.get("v"),
                key=row.get("key"),
                state="SEVERE",
                evidence_class="HISTORICAL_INVENTORY",
                matching_distance_m=None,
                source_time=source_time,
                retrieval_time=retrieval_time,
                confidence_basis="Polygon overlay; inventory geometry accuracy is unknown.",
                expiry_rule=EXPIRY_RULE,
                reason="Road geometry intersects a historical inundation polygon under a declared scenario rule.",
                scenario_rule=INUNDATION_SEVERE_RULE,
                conflict=False,
                capacity_multiplier=SCENARIO_CAPACITY_MULTIPLIERS["SEVERE"],
                multiplier_class="SCENARIO",
            )
        )
    return rows


def merge_state_rows(rows: Iterable[RoadStateRow]) -> list[RoadStateRow]:
    """Keep the more severe state and flag conflicts when rules disagree."""

    severity = {state: index for index, state in enumerate(ROAD_STATES)}
    grouped: dict[str, list[RoadStateRow]] = {}
    for row in rows:
        grouped.setdefault(row.arc_id, []).append(row)

    merged: list[RoadStateRow] = []
    for arc_id, items in grouped.items():
        unique_states = {item.state for item in items}
        chosen = max(items, key=lambda item: severity[item.state])
        conflict = len(unique_states) > 1
        reasons = " | ".join(sorted({item.reason for item in items}))
        merged.append(
            RoadStateRow(
                arc_id=arc_id,
                u=chosen.u,
                v=chosen.v,
                key=chosen.key,
                state=chosen.state,
                evidence_class=chosen.evidence_class,
                matching_distance_m=chosen.matching_distance_m,
                source_time=chosen.source_time,
                retrieval_time=chosen.retrieval_time,
                confidence_basis=chosen.confidence_basis,
                expiry_rule=chosen.expiry_rule,
                reason=reasons,
                scenario_rule=chosen.scenario_rule,
                conflict=conflict,
                capacity_multiplier=chosen.capacity_multiplier,
                multiplier_class="SCENARIO",
            )
        )
    return merged


def rainfall_does_not_assign_road_state() -> str:
    """Document the hard rule that precipitation is not a closure."""

    return (
        "MODELLED rainfall and PROXY elevation never assign NORMAL/DEGRADED/"
        "SEVERE/BLOCKED. Unmapped arcs remain UNKNOWN."
    )


def rows_to_frame(rows: list[RoadStateRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])
