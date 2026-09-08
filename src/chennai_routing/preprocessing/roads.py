"""Deterministic Stage 3 road-graph normalization and structural auditing."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Hashable

import networkx as nx
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry

ROAD_GRAPH_DATA_DICTIONARY = {
    "stage3_arc_id": {
        "meaning": "SHA-256 of canonical u, v, key, osmid, and geometry identity",
        "classification": "OBSERVED",
        "unit": None,
    },
    "osmid": {
        "meaning": "OpenStreetMap way identifier copied from the dated extract",
        "classification": "OBSERVED",
        "unit": None,
    },
    "highway": {
        "meaning": "OSM highway class tag",
        "classification": "OBSERVED",
        "unit": None,
    },
    "maxspeed": {
        "meaning": "Raw OSM maxspeed tag; missing or compound values are not imputed",
        "classification": "OBSERVED",
        "unit": "tag text",
    },
    "stage3_explicit_speed_kph": {
        "meaning": "Parsed unambiguous maxspeed in kilometres per hour, else missing",
        "classification": "OBSERVED",
        "unit": "km/h",
    },
    "length": {
        "meaning": "Edge length from the OSM geometry",
        "classification": "OBSERVED",
        "unit": "m",
    },
    "stage3_free_flow_time_seconds": {
        "meaning": "length / explicit speed; missing when speed or length is unavailable",
        "classification": "OBSERVED",
        "unit": "s",
    },
    "lanes": {
        "meaning": "Raw OSM lanes tag; missing values stay missing",
        "classification": "UNAVAILABLE when absent",
        "unit": None,
    },
    "oneway": {
        "meaning": "Raw OSM oneway tag",
        "classification": "OBSERVED",
        "unit": None,
    },
    "access": {
        "meaning": "Raw OSM access tag when present",
        "classification": "UNAVAILABLE when absent",
        "unit": None,
    },
    "bridge": {
        "meaning": "Raw OSM bridge tag when present",
        "classification": "UNAVAILABLE when absent",
        "unit": None,
    },
    "tunnel": {
        "meaning": "Raw OSM tunnel tag when present",
        "classification": "UNAVAILABLE when absent",
        "unit": None,
    },
    "layer": {
        "meaning": "Raw OSM layer tag when present",
        "classification": "UNAVAILABLE when absent",
        "unit": None,
    },
    "geometry": {
        "meaning": "Source linestring, or a two-point line from node coordinates",
        "classification": "OBSERVED",
        "unit": "EPSG:4326",
    },
}

_MAXSPEED_PATTERN = re.compile(
    r"^(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>km/h|kmh|kph|mph)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RoadGraphAudit:
    """Machine-readable quality and missingness summary for one graph."""

    node_count: int
    arc_count: int
    self_loop_count: int
    directed_pairs_with_parallel_arcs: int
    arcs_in_parallel_directed_pairs: int
    weak_component_count: int
    strong_component_count: int
    largest_weak_component_nodes: int
    missing_node_coordinate_count: int
    missing_or_invalid_length_count: int
    missing_geometry_count: int
    derived_geometry_count: int
    missing_osmid_count: int
    missing_highway_count: int
    missing_maxspeed_count: int
    unparseable_maxspeed_count: int
    explicit_speed_count: int
    free_flow_time_count: int
    missing_lanes_count: int
    missing_oneway_count: int
    missing_access_count: int
    missing_grade_separation_tag_count: int
    duplicate_arc_id_count: int


def _canonical_identifier(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        canonical = [_canonical_identifier(item) for item in value]
        return sorted(
            canonical,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return str(value)


def stable_osm_arc_id(
    u: Hashable,
    v: Hashable,
    key: Hashable,
    data: dict[str, object],
) -> str:
    """Return an ID stable for the same fixed raw graph artifact."""

    geometry = data.get("geometry")
    geometry_identity = geometry.wkb_hex if isinstance(geometry, BaseGeometry) else None
    identity = {
        "u": _canonical_identifier(u),
        "v": _canonical_identifier(v),
        "key": _canonical_identifier(key),
        "osmid": _canonical_identifier(data.get("osmid")),
        "geometry_wkb_hex": geometry_identity,
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_explicit_osm_maxspeed_kph(value: object) -> float | None:
    """Parse one unambiguous OSM maxspeed value without imputing missing data."""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) and numeric > 0 else None
    if not isinstance(value, str):
        return None
    match = _MAXSPEED_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    numeric = float(match.group("value"))
    if not math.isfinite(numeric) or numeric <= 0:
        return None
    if (match.group("unit") or "").lower() == "mph":
        return numeric * 1.609344
    return numeric


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value == ""


def normalize_road_graph(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Copy and annotate a directed OSM graph without scientific-value fallback."""

    if not isinstance(graph, nx.MultiDiGraph) or not graph.is_directed():
        raise TypeError("Stage 3 requires a directed networkx.MultiDiGraph.")
    normalized = graph.copy()
    normalized.graph["stage3_speed_policy"] = (
        "Only unambiguous explicit OSM maxspeed values are parsed; missing or "
        "compound values remain unavailable."
    )
    normalized.graph["stage3_numeric_maxspeed_unit_basis"] = (
        "OSM maxspeed numeric values without a unit are kilometres per hour."
    )
    normalized.graph["stage3_capacity_policy"] = (
        "No capacity is assigned in Stage 3; calibration/sensitivity is a Stage 5 gate."
    )

    arc_ids: set[str] = set()
    for u, v, key, data in normalized.edges(keys=True, data=True):
        geometry = data.get("geometry")
        if not isinstance(geometry, BaseGeometry):
            start = normalized.nodes[u]
            end = normalized.nodes[v]
            coordinates = (start.get("x"), start.get("y"), end.get("x"), end.get("y"))
            if all(
                isinstance(value, (int, float)) and math.isfinite(float(value))
                for value in coordinates
            ):
                data["geometry"] = LineString(
                    [
                        (float(coordinates[0]), float(coordinates[1])),
                        (float(coordinates[2]), float(coordinates[3])),
                    ]
                )
                data["stage3_geometry_source"] = "derived_from_endpoint_coordinates"
        data.setdefault("stage3_geometry_source", "source")

        arc_id = stable_osm_arc_id(u, v, key, data)
        if arc_id in arc_ids:
            raise ValueError(f"Stable arc ID collision detected for {(u, v, key)!r}.")
        arc_ids.add(arc_id)
        data["stage3_arc_id"] = arc_id

        explicit_speed = parse_explicit_osm_maxspeed_kph(data.get("maxspeed"))
        data["stage3_explicit_speed_kph"] = explicit_speed
        length = data.get("length")
        if (
            explicit_speed is not None
            and isinstance(length, (int, float))
            and math.isfinite(float(length))
            and float(length) > 0
        ):
            data["stage3_free_flow_time_seconds"] = float(length) / (
                explicit_speed * 1000.0 / 3600.0
            )
            data["stage3_free_flow_time_basis"] = "explicit_osm_maxspeed_and_edge_length"
        else:
            data["stage3_free_flow_time_seconds"] = None
            data["stage3_free_flow_time_basis"] = "UNAVAILABLE"
    return normalized


def audit_road_graph(graph: nx.MultiDiGraph) -> RoadGraphAudit:
    """Quantify topology, geometry, and attribute completeness."""

    if not isinstance(graph, nx.MultiDiGraph) or not graph.is_directed():
        raise TypeError("Stage 3 requires a directed networkx.MultiDiGraph.")

    missing_coordinates = sum(
        1
        for _, data in graph.nodes(data=True)
        if any(
            not isinstance(data.get(axis), (int, float))
            or not math.isfinite(float(data[axis]))
            for axis in ("x", "y")
        )
    )
    parallel_counts: dict[tuple[Hashable, Hashable], int] = {}
    for u, v in graph.edges():
        parallel_counts[(u, v)] = parallel_counts.get((u, v), 0) + 1
    parallel_pair_counts = [count for count in parallel_counts.values() if count > 1]

    edge_rows = list(graph.edges(keys=True, data=True))
    arc_ids = [
        str(data["stage3_arc_id"])
        for _, _, _, data in edge_rows
        if not _is_missing(data.get("stage3_arc_id"))
    ]

    def count_missing(field: str) -> int:
        return sum(1 for _, _, _, data in edge_rows if _is_missing(data.get(field)))

    invalid_length = sum(
        1
        for _, _, _, data in edge_rows
        if not isinstance(data.get("length"), (int, float))
        or not math.isfinite(float(data["length"]))
        or float(data["length"]) <= 0
    )
    source_maxspeed = [data.get("maxspeed") for _, _, _, data in edge_rows]
    unparseable_speed = sum(
        1
        for value in source_maxspeed
        if not _is_missing(value) and parse_explicit_osm_maxspeed_kph(value) is None
    )
    weak_components = list(nx.weakly_connected_components(graph)) if graph else []
    strong_component_count = nx.number_strongly_connected_components(graph) if graph else 0

    return RoadGraphAudit(
        node_count=graph.number_of_nodes(),
        arc_count=graph.number_of_edges(),
        self_loop_count=nx.number_of_selfloops(graph),
        directed_pairs_with_parallel_arcs=len(parallel_pair_counts),
        arcs_in_parallel_directed_pairs=sum(parallel_pair_counts),
        weak_component_count=len(weak_components),
        strong_component_count=strong_component_count,
        largest_weak_component_nodes=max((len(item) for item in weak_components), default=0),
        missing_node_coordinate_count=missing_coordinates,
        missing_or_invalid_length_count=invalid_length,
        missing_geometry_count=sum(
            1
            for _, _, _, data in edge_rows
            if not isinstance(data.get("geometry"), BaseGeometry)
        ),
        derived_geometry_count=sum(
            1
            for _, _, _, data in edge_rows
            if data.get("stage3_geometry_source") == "derived_from_endpoint_coordinates"
        ),
        missing_osmid_count=count_missing("osmid"),
        missing_highway_count=count_missing("highway"),
        missing_maxspeed_count=count_missing("maxspeed"),
        unparseable_maxspeed_count=unparseable_speed,
        explicit_speed_count=sum(
            1
            for _, _, _, data in edge_rows
            if not _is_missing(data.get("stage3_explicit_speed_kph"))
        ),
        free_flow_time_count=sum(
            1
            for _, _, _, data in edge_rows
            if not _is_missing(data.get("stage3_free_flow_time_seconds"))
        ),
        missing_lanes_count=count_missing("lanes"),
        missing_oneway_count=count_missing("oneway"),
        missing_access_count=count_missing("access"),
        missing_grade_separation_tag_count=sum(
            1
            for _, _, _, data in edge_rows
            if all(_is_missing(data.get(field)) for field in ("bridge", "tunnel", "layer"))
        ),
        duplicate_arc_id_count=len(arc_ids) - len(set(arc_ids)),
    )


def write_road_graph_audit(audit: RoadGraphAudit, path: Path) -> Path:
    """Write a deterministic structural and missingness report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
