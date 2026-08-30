"""Shared geospatial preprocessing for Stage 1."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def project_to_metric_crs(
    flood_points: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Project flood points and road edges to a shared local metric CRS."""

    metric_crs = road_edges.estimate_utm_crs() or flood_points.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Could not estimate a metric CRS for flood-to-road mapping.")
    return flood_points.to_crs(metric_crs), road_edges.to_crs(metric_crs)


def map_flood_points_to_nearest_roads(
    flood_points: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
    *,
    max_distance_meters: float = 120.0,
) -> gpd.GeoDataFrame:
    """Map historical flood hotspot points to nearest road edges within a tolerance."""

    if flood_points.empty:
        raise ValueError("Flood point GeoDataFrame is empty.")
    if road_edges.empty:
        raise ValueError("Road edge GeoDataFrame is empty.")
    if flood_points.crs != road_edges.crs:
        raise ValueError(f"CRS mismatch: {flood_points.crs!s} != {road_edges.crs!s}")

    flood_metric, roads_metric = project_to_metric_crs(flood_points, road_edges)
    roads_for_join = roads_metric.reset_index().copy()
    roads_for_join["road_geometry"] = roads_for_join.geometry
    nearest = gpd.sjoin_nearest(
        flood_metric,
        roads_for_join,
        how="inner",
        max_distance=max_distance_meters,
        distance_col="distance_to_road_m",
    )
    if nearest.empty:
        columns = [
            "flood_id",
            "name",
            "u",
            "v",
            "key",
            "distance_to_road_m",
            "data_classification",
        ]
        return gpd.GeoDataFrame(columns=columns, geometry=[], crs=flood_metric.crs)

    keep_columns = [
        column
        for column in [
            "flood_id",
            "name",
            "source",
            "data_classification",
            "u",
            "v",
            "key",
            "osmid",
            "name_right",
            "highway",
            "length",
            "distance_to_road_m",
            "geometry",
        ]
        if column in nearest.columns
    ]
    result = nearest[keep_columns].copy()
    if "road_geometry" in nearest.columns:
        result["geometry"] = nearest["road_geometry"]
    result["road_state"] = "BLOCKED"
    result["state_basis"] = (
        "MODEL ASSUMPTION for controlled Stage 1 demo: historical hotspot nearest road "
        "is treated as unavailable after disruption."
    )
    return gpd.GeoDataFrame(pd.DataFrame(result), geometry="geometry", crs=flood_metric.crs)
