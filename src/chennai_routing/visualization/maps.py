"""Map visualization for the Stage 1 proof of concept."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox


def _route_nodes_to_gdf(graph: nx.MultiDiGraph, route: list[int]) -> gpd.GeoDataFrame:
    _, edges = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
    edges = edges.sort_index()
    route_edges = []
    for u, v in zip(route[:-1], route[1:]):
        candidates = edges.loc[(u, v)]
        if isinstance(candidates, gpd.GeoDataFrame):
            route_edges.append(candidates.sort_values("length").iloc[0])
        else:
            route_edges.append(candidates)
    return gpd.GeoDataFrame(route_edges, geometry="geometry", crs=edges.crs)


def plot_stage1_before_after(
    graph: nx.MultiDiGraph,
    flood_points: gpd.GeoDataFrame,
    affected_edges: gpd.GeoDataFrame,
    before_route: list[int],
    after_route: list[int],
    output_path: Path,
) -> Path:
    """Create a before/after route-change visualization."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _, road_edges = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
    before_edges = _route_nodes_to_gdf(graph, before_route)
    after_edges = _route_nodes_to_gdf(graph, after_route)

    origin_node = before_route[0]
    destination_node = before_route[-1]
    node_data = graph.nodes
    origin = gpd.GeoDataFrame(
        {"label": ["origin"]},
        geometry=[gpd.points_from_xy([node_data[origin_node]["x"]], [node_data[origin_node]["y"]])[0]],
        crs="EPSG:4326",
    )
    destination = gpd.GeoDataFrame(
        {"label": ["destination"]},
        geometry=[
            gpd.points_from_xy([node_data[destination_node]["x"]], [node_data[destination_node]["y"]])[0]
        ],
        crs="EPSG:4326",
    )

    target_crs = road_edges.estimate_utm_crs() or "EPSG:4326"
    road_edges = road_edges.to_crs(target_crs)
    before_edges = before_edges.to_crs(target_crs)
    after_edges = after_edges.to_crs(target_crs)
    flood_points = flood_points.to_crs(target_crs)
    affected_edges = affected_edges.to_crs(target_crs)
    origin = origin.to_crs(target_crs)
    destination = destination.to_crs(target_crs)

    fig, ax = plt.subplots(figsize=(11, 9))
    road_edges.plot(ax=ax, linewidth=0.45, color="#b6bcc6", alpha=0.85)
    affected_edges.plot(ax=ax, linewidth=3.0, color="#d7263d", label="Affected road")
    before_edges.plot(ax=ax, linewidth=3.0, color="#1f77b4", label="Before route")
    after_edges.plot(ax=ax, linewidth=3.0, color="#2ca02c", linestyle="--", label="After route")
    flood_points.plot(ax=ax, markersize=55, color="#6a00f4", marker="x", label="Historical flood hotspot")
    origin.plot(ax=ax, markersize=90, color="#111111", marker="o", label="Origin")
    destination.plot(ax=ax, markersize=110, color="#ffbf00", marker="*", label="Destination")

    ax.set_title("Stage 1 Chennai Flood-Aware Routing Proof of Concept")
    ax.set_axis_off()
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path
