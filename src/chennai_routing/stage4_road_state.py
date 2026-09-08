"""Stage 4 flood/rainfall/elevation evidence and explained road-state mapping."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
from shapely import wkt
from shapely.geometry.base import BaseGeometry

from chennai_routing.config import get_project_paths
from chennai_routing.data.elevation import fetch_open_meteo_elevation_grid
from chennai_routing.data.flood import download_pinned_flood_resources
from chennai_routing.data.hydrology import download_swd_2023_kml
from chennai_routing.data.rainfall import fetch_open_meteo_era5_precipitation
from chennai_routing.evaluation.robustness import (
    perturb_binary_evidence,
    summarize_binary_evidence,
)
from chennai_routing.models.road_state import (
    assign_states_from_hotspots,
    assign_states_from_inundation,
    merge_state_rows,
    rainfall_does_not_assign_road_state,
    rows_to_frame,
)
from chennai_routing.preprocessing.evidence_mapping import (
    DEFAULT_DISTANCE_SWEEP_METERS,
    evidence_points,
    intersect_polygons_with_roads,
    summaries_as_records,
    sweep_point_mapping,
)


@dataclass(frozen=True)
class Stage4Result:
    """Acquisition and optional mapping outputs for Stage 4."""

    evidence_path: str
    flood_manifest_path: str
    rainfall_path: str
    elevation_path: str
    hydrology_path: str
    mapping_path: str | None
    road_state_path: str | None
    decision: str
    claim_limit: str
    next_gate: str


def _repository_relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def load_stage3_edges_from_graphml(path: Path) -> gpd.GeoDataFrame:
    """Load Stage 3 edges without OSMnx bool coercion of OSM oneway tags."""

    import networkx as nx

    graph = nx.read_graphml(path)
    rows = []
    for u, v, data in graph.edges(data=True):
        geometry_text = data.get("geometry")
        if not geometry_text or geometry_text == "nan":
            continue
        rows.append(
            {
                "u": data.get("u", u),
                "v": data.get("v", v),
                "key": data.get("id", 0),
                "stage3_arc_id": data.get("stage3_arc_id"),
                "osmid": data.get("osmid"),
                "geometry": wkt.loads(str(geometry_text)),
            }
        )
    if not rows:
        raise ValueError("GraphML has no parseable edge geometries for Stage 4 mapping.")
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def load_mapping_roads(paths) -> gpd.GeoDataFrame | None:
    """Prefer a GeoPackage export; otherwise parse the Stage 3 GraphML."""

    gpkg = paths.processed_roads / "stage3_chennai_gcc_2022_edges.gpkg"
    if gpkg.is_file():
        return gpd.read_file(gpkg)
    graphml = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    if graphml.is_file():
        roads = load_stage3_edges_from_graphml(graphml)
        gpkg.parent.mkdir(parents=True, exist_ok=True)
        roads.to_file(gpkg, driver="GPKG")
        return roads
    return None


def graph_edges_to_gdf(graph) -> gpd.GeoDataFrame:
    """Build a road-edge GeoDataFrame from a Stage 3 MultiDiGraph."""

    rows = []
    for u, v, key, data in graph.edges(keys=True, data=True):
        geometry = data.get("geometry")
        if not isinstance(geometry, BaseGeometry):
            continue
        rows.append(
            {
                "u": u,
                "v": v,
                "key": key,
                "stage3_arc_id": data.get("stage3_arc_id"),
                "osmid": data.get("osmid"),
                "geometry": geometry,
            }
        )
    if not rows:
        raise ValueError("Graph has no edge geometries for Stage 4 mapping.")
    crs = graph.graph.get("crs", "EPSG:4326")
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)


def _gcc_bounds_from_boundary_evidence(root: Path) -> tuple[float, float, float, float]:
    evidence = json.loads(
        (root / "docs" / "evidence" / "STAGE3_BOUNDARY_RESULTS.json").read_text(encoding="utf-8")
    )
    bounds = evidence["audit"]["bounds_wgs84"]
    return (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))


def _freshness_experiment() -> dict[str, object]:
    """Synthetic lag/error test. Not a measured Chennai sensor-accuracy study."""

    truth = (False, False, True, True, True, False, False, True, False, False)
    observed = perturb_binary_evidence(
        truth,
        lag_steps=2,
        false_positive_rate=0.1,
        false_negative_rate=0.1,
        seed=8597,
    )
    summary = summarize_binary_evidence(truth, observed)
    return {
        "classification": "SCENARIO",
        "claim_limit": (
            "Lag and false-positive/false-negative rates are declared scenario "
            "parameters, not measured OpenCity sensing error."
        ),
        "truth": list(truth),
        "observed": list(observed),
        "summary": asdict(summary),
    }


def run_stage4_road_state(graph=None) -> Stage4Result:
    """Acquire Stage 4 evidence and map it when a Stage 3 graph is available."""

    paths = get_project_paths()
    for directory in (
        paths.raw_flood,
        paths.raw_rainfall,
        paths.raw_elevation,
        paths.raw_hydrology,
        paths.processed_flood,
        paths.processed_rainfall,
        paths.processed_elevation,
        paths.processed_hydrology,
        paths.processed_road_state,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    flood_results = download_pinned_flood_resources(paths.raw_flood)
    _raw_rain, rain_table, rain_prov = fetch_open_meteo_era5_precipitation(paths.raw_rainfall)
    elev_path, elev_prov = fetch_open_meteo_elevation_grid(
        paths.raw_elevation,
        _gcc_bounds_from_boundary_evidence(paths.root),
    )
    _swd_path, hydro_prov, _swd_features = download_swd_2023_kml(paths.raw_hydrology)

    flood_manifest = [
        {**asdict(provenance), "local_path": str(kml_path.relative_to(paths.root))}
        for kml_path, provenance, _features in flood_results
    ]
    flood_manifest_path = paths.root / "docs" / "evidence" / "STAGE4_FLOOD_MANIFEST.json"
    flood_manifest_path.write_text(
        json.dumps(flood_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    mapping_path = None
    road_state_path = None
    mapping_done = False
    sweep_records: list[dict[str, float | int]] = []
    state_count = 0
    conflict_count = 0
    if graph is not None:
        roads = graph_edges_to_gdf(graph)
    else:
        roads = load_mapping_roads(paths)

    if roads is not None:
        hotspot_features = next(
            features
            for _path, provenance, features in flood_results
            if provenance.resource_id == "8e1c5b2d-322c-4dbd-bd64-6da2d1a8681d"
        )
        inundation_features = next(
            (
                features
                for _path, provenance, features in flood_results
                if provenance.resource_id == "2056abd6-26d7-413b-9dfa-e63cbbf41ee7"
            ),
            gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"),
        )
        points = evidence_points(hotspot_features)
        joined, summaries = sweep_point_mapping(points, roads)
        sweep_records = summaries_as_records(summaries)
        chosen_distance = 150.0
        hotspot_states = assign_states_from_hotspots(
            joined[chosen_distance],
            retrieval_time=flood_results[0][1].retrieved_at_utc,
            matching_distance_m=chosen_distance,
        )
        polygons = inundation_features[
            inundation_features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        ]
        inundation_states = assign_states_from_inundation(
            intersect_polygons_with_roads(polygons, roads) if not polygons.empty else polygons,
            retrieval_time=flood_results[0][1].retrieved_at_utc,
        )
        merged = merge_state_rows([*hotspot_states, *inundation_states])
        state_frame = rows_to_frame(merged)
        state_count = len(state_frame)
        conflict_count = int(state_frame["conflict"].sum()) if not state_frame.empty else 0
        mapping_path = paths.root / "docs" / "evidence" / "STAGE4_MAPPING_SWEEP.json"
        mapping_path.write_text(
            json.dumps(
                {
                    "distances_meters": list(DEFAULT_DISTANCE_SWEEP_METERS),
                    "reported_distance_for_state_table_m": chosen_distance,
                    "distance_selection": "SCENARIO",
                    "summaries": sweep_records,
                    "note": (
                        "150 m is reported because it matches the Stage 1 demonstration "
                        "distance; it is not a measured KML accuracy."
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        road_state_path = paths.processed_road_state / "stage4_road_states.csv"
        state_frame.to_csv(road_state_path, index=False)
        summary_path = paths.root / "docs" / "evidence" / "STAGE4_ROAD_STATE_SUMMARY.json"
        summary_path.write_text(
            json.dumps(
                {
                    "row_count": state_count,
                    "conflict_count": conflict_count,
                    "state_counts": {}
                    if state_frame.empty
                    else {str(key): int(value) for key, value in state_frame["state"].value_counts().items()},
                    "capacity_multiplier_class": "SCENARIO",
                    "claim_limit": (
                        "These states are declared scenario overlays on historical "
                        "inventories, not observed 2015 or live closures."
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        mapping_done = True

    evidence_path = paths.root / "docs" / "evidence" / "STAGE4_ROAD_STATE_RESULTS.json"
    decision = "PASS WITH LIMITATIONS"
    claim_limit = (
        "Stage 4 pins historical flood inventories, Open-Meteo ERA5 rainfall, coarse "
        "DEM samples, and the 2023 drain map. Rainfall and elevation do not create "
        "road closures. Assigned BLOCKED/SEVERE states are declared scenario rules "
        "on historical inventory overlays, not observed 2015 or live closures."
    )
    next_gate = (
        "Stage 5 traffic/SUMO calibration, labelled SYNTHETIC unless independent "
        "Chennai counts are obtained."
        if mapping_done
        else "Complete Stage 3 graph output, then rerun Stage 4 mapping."
    )
    payload = {
        "stage": 4,
        "decision": decision,
        "claim_limit": claim_limit,
        "rainfall_rule": rainfall_does_not_assign_road_state(),
        "mapping_completed": mapping_done,
        "state_row_count": state_count,
        "conflict_count": conflict_count,
        "mapping_sweep": sweep_records,
        "freshness_experiment": _freshness_experiment(),
        "flood": flood_manifest,
        "rainfall": asdict(rain_prov),
        "elevation": asdict(elev_prov),
        "hydrology": asdict(hydro_prov),
        "artifacts": {
            "flood_manifest": _repository_relative(flood_manifest_path, paths.root),
            "rainfall_csv": _repository_relative(rain_table, paths.root),
            "elevation_geojson": _repository_relative(elev_path, paths.root),
            "mapping": None if mapping_path is None else _repository_relative(mapping_path, paths.root),
            "road_states": None
            if road_state_path is None
            else _repository_relative(road_state_path, paths.root),
        },
    }
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return Stage4Result(
        evidence_path=_repository_relative(evidence_path, paths.root),
        flood_manifest_path=_repository_relative(flood_manifest_path, paths.root),
        rainfall_path=_repository_relative(rain_table, paths.root),
        elevation_path=_repository_relative(elev_path, paths.root),
        hydrology_path=_repository_relative(
            paths.raw_hydrology / "chennai_swd_map_2023_provenance.json",
            paths.root,
        ),
        mapping_path=None if mapping_path is None else _repository_relative(mapping_path, paths.root),
        road_state_path=None
        if road_state_path is None
        else _repository_relative(road_state_path, paths.root),
        decision=decision,
        claim_limit=claim_limit,
        next_gate=next_gate,
    )
