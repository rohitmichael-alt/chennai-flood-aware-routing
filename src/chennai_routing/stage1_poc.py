"""Stage 1 proof-of-concept orchestration."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd

from chennai_routing.config import get_project_paths
from chennai_routing.data.flood import download_opencity_flood_kml, parse_kml_points
from chennai_routing.data.osm import build_bbox_around_point, download_drive_graph_for_bbox, save_graphml
from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.models.capacity import effective_capacity
from chennai_routing.preprocessing.geospatial import map_flood_points_to_nearest_roads
from chennai_routing.preprocessing.validation import require_same_crs, validate_routable_graph
from chennai_routing.routing.dijkstra import path_cost, shortest_path
from chennai_routing.visualization.maps import plot_stage1_before_after


@dataclass(frozen=True)
class Stage1Result:
    """Artifacts and summary values produced by the Stage 1 run."""

    graph_path: str
    flood_kml_path: str
    flood_provenance_path: str
    affected_roads_csv: str
    route_summary_csv: str
    map_path: str
    before_route: list[int]
    after_route: list[int]
    before_cost_seconds: float
    after_cost_seconds: float
    affected_edge: tuple[int, int, int]
    flood_points_loaded: int
    affected_roads_found: int
    bbox: tuple[float, float, float, float]


def _edge_free_flow_time(data: dict[str, object]) -> float:
    if "travel_time" in data and data["travel_time"] is not None:
        return float(data["travel_time"])
    length = float(data.get("length", 1.0))
    speed_kph = float(data.get("speed_kph", 30.0))
    return length / (speed_kph * 1000.0 / 3600.0)


def apply_stage1_costs(
    graph: nx.MultiDiGraph,
    blocked_edges: set[tuple[int, int, int]] | None = None,
    *,
    normal_capacity: float = 1200.0,
    flow: float = 600.0,
) -> None:
    """Apply transparent capacity and BPR costs to graph edges in place."""

    blocked_edges = blocked_edges or set()
    for u, v, key, data in graph.edges(keys=True, data=True):
        road_state = "BLOCKED" if (u, v, key) in blocked_edges else "NORMAL"
        capacity = effective_capacity(normal_capacity, road_state)
        free_flow_time = _edge_free_flow_time(data)
        data["road_condition"] = road_state
        data["normal_capacity"] = normal_capacity
        data["effective_capacity"] = capacity
        data["current_flow"] = flow
        data["bpr_travel_time"] = bpr_travel_time(free_flow_time, flow, capacity)
        data["stage1_weight"] = data["bpr_travel_time"]


def select_route_change_edge(
    graph: nx.MultiDiGraph,
    affected_edges: gpd.GeoDataFrame,
) -> tuple[tuple[int, int, int], list[int], list[int], float, float]:
    """Find an affected edge whose blockage forces a different route."""

    apply_stage1_costs(graph)
    candidates = affected_edges[["u", "v", "key", "distance_to_road_m"]].drop_duplicates()
    candidates = candidates.sort_values("distance_to_road_m")

    for row in candidates.itertuples(index=False):
        edge = (int(row.u), int(row.v), int(row.key))
        if not graph.has_edge(edge[0], edge[1], edge[2]):
            continue

        try:
            before = shortest_path(graph, edge[0], edge[1], weight="stage1_weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

        blocked_graph = graph.copy()
        apply_stage1_costs(blocked_graph, {edge})
        try:
            after = shortest_path(blocked_graph, edge[0], edge[1], weight="stage1_weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

        if before != after and len(after) > 2:
            before_cost = path_cost(graph, before, weight="stage1_weight")
            after_cost = path_cost(blocked_graph, after, weight="stage1_weight")
            if math.isfinite(after_cost):
                graph.clear()
                graph.add_nodes_from(blocked_graph.nodes(data=True))
                graph.add_edges_from(blocked_graph.edges(keys=True, data=True))
                graph.graph.update(blocked_graph.graph)
                return edge, before, after, before_cost, after_cost

    raise RuntimeError(
        "Could not find a real flood-mapped edge with an alternate route in the selected OSM area."
    )


def _write_route_summary(path: Path, result: Stage1Result) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "scenario": "before_historical_hotspot_disruption",
                "route_nodes": json.dumps(result.before_route),
                "cost_seconds": result.before_cost_seconds,
            },
            {
                "scenario": "after_controlled_blockage_of_real_flood_mapped_edge",
                "route_nodes": json.dumps(result.after_route),
                "cost_seconds": result.after_cost_seconds,
            },
        ]
    ).to_csv(path, index=False)
    return path


def run_stage1_poc() -> Stage1Result:
    """Run the reproducible Stage 1 proof of concept."""

    paths = get_project_paths()
    for directory in [
        paths.raw_flood,
        paths.processed_roads,
        paths.processed_flood,
        paths.output_maps,
        paths.output_tables,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    kml_path, provenance_path, _metadata = download_opencity_flood_kml(paths.raw_flood)
    flood_points = parse_kml_points(kml_path)

    # The first usable OpenCity hotspot is used only to center a small OSM query.
    center_point = flood_points.geometry.iloc[0]
    bbox_sizes = [0.012, 0.018, 0.025]
    last_error: Exception | None = None

    for bbox_size in bbox_sizes:
        bbox = build_bbox_around_point(center_point.x, center_point.y, bbox_size)
        try:
            graph = download_drive_graph_for_bbox(bbox)
            validate_routable_graph(graph)
            _, road_edges = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
            local_flood_points = flood_points.cx[bbox[0] : bbox[2], bbox[1] : bbox[3]].copy()
            require_same_crs(local_flood_points, road_edges)
            affected_edges = map_flood_points_to_nearest_roads(
                local_flood_points,
                road_edges,
                max_distance_meters=150.0,
            )
            if affected_edges.empty:
                continue

            affected_edge, before, after, before_cost, after_cost = select_route_change_edge(
                graph, affected_edges
            )
            graph_path = save_graphml(graph, paths.processed_roads / "stage1_chennai_osm_graph.graphml")

            affected_csv = paths.output_tables / "stage1_affected_roads.csv"
            affected_edges.drop(columns="geometry").to_csv(affected_csv, index=False)

            selected_affected_mask = (
                (affected_edges["u"] == affected_edge[0])
                & (affected_edges["v"] == affected_edge[1])
                & (affected_edges["key"] == affected_edge[2])
            )
            map_path = plot_stage1_before_after(
                graph,
                local_flood_points,
                affected_edges[selected_affected_mask],
                before,
                after,
                paths.output_maps / "stage1_before_after_route.png",
            )

            result = Stage1Result(
                graph_path=str(graph_path),
                flood_kml_path=str(kml_path),
                flood_provenance_path=str(provenance_path),
                affected_roads_csv=str(affected_csv),
                route_summary_csv=str(paths.output_tables / "stage1_route_summary.csv"),
                map_path=str(map_path),
                before_route=before,
                after_route=after,
                before_cost_seconds=before_cost,
                after_cost_seconds=after_cost,
                affected_edge=affected_edge,
                flood_points_loaded=len(flood_points),
                affected_roads_found=len(affected_edges),
                bbox=bbox,
            )
            _write_route_summary(Path(result.route_summary_csv), result)
            (paths.output_tables / "stage1_summary.json").write_text(
                json.dumps(asdict(result), indent=2),
                encoding="utf-8",
            )
            return result
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError("Stage 1 POC failed for all configured bbox sizes.") from last_error
