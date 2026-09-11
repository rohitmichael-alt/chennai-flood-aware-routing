"""Validation helpers for Stage 1 geospatial and graph checks."""

from __future__ import annotations

import geopandas as gpd
import networkx as nx


def require_same_crs(left: gpd.GeoDataFrame, right: gpd.GeoDataFrame) -> None:
    """Raise when two GeoDataFrames do not have the same CRS."""

    if left.crs is None or right.crs is None:
        raise ValueError("Both GeoDataFrames must have a defined CRS.")
    if left.crs != right.crs:
        raise ValueError(f"CRS mismatch: {left.crs!s} != {right.crs!s}")


def validate_routable_graph(graph: nx.MultiDiGraph) -> None:
    """Validate the minimal OSM road graph properties required by Stage 1."""

    if graph.number_of_nodes() == 0:
        raise ValueError("OSM graph has no nodes.")
    if graph.number_of_edges() == 0:
        raise ValueError("OSM graph has no edges.")
    missing_or_invalid = [
        (u, v, k)
        for u, v, k, data in graph.edges(keys=True, data=True)
        if "length" not in data
        or not _positive_finite(data.get("length"))
    ]
    if missing_or_invalid:
        raise ValueError(
            f"OSM graph has edges without a positive finite length: {missing_or_invalid[:5]}"
        )


def _positive_finite(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return number == number and number > 0
