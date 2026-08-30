"""OpenStreetMap and OSMnx data access for the Stage 1 proof of concept."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import osmnx as ox


def build_bbox_around_point(lon: float, lat: float, half_size_degrees: float) -> tuple[float, float, float, float]:
    """Return an OSMnx bbox tuple `(left, bottom, right, top)` around a point."""

    return (
        lon - half_size_degrees,
        lat - half_size_degrees,
        lon + half_size_degrees,
        lat + half_size_degrees,
    )


def download_drive_graph_for_bbox(
    bbox: tuple[float, float, float, float],
    *,
    retain_all: bool = False,
    fallback_speed_kph: float = 30.0,
) -> nx.MultiDiGraph:
    """Download a routable OSM driving graph for a small EPSG:4326 bbox."""

    ox.settings.use_cache = True
    ox.settings.log_console = False
    graph = ox.graph_from_bbox(
        bbox,
        network_type="drive",
        simplify=True,
        retain_all=retain_all,
        truncate_by_edge=True,
    )
    graph = ox.add_edge_speeds(graph, fallback=fallback_speed_kph)
    graph = ox.add_edge_travel_times(graph)
    graph.graph["stage1_speed_fallback_kph"] = fallback_speed_kph
    graph.graph["stage1_speed_fallback_basis"] = (
        "MODEL ASSUMPTION: used only where OSM maxspeed data is missing in the Stage 1 POC."
    )
    return graph


def save_graphml(graph: nx.MultiDiGraph, path: Path) -> Path:
    """Save an OSMnx graph to GraphML."""

    path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=path)
    return path


def load_graphml(path: Path) -> nx.MultiDiGraph:
    """Load an OSMnx GraphML file."""

    return ox.load_graphml(path)
