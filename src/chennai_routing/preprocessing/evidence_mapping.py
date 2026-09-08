"""Source-accuracy-aware evidence-to-road mapping for Stage 4.

Where positional accuracy is unknown, distances are swept rather than a single
tolerance being treated as ground truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import geopandas as gpd

from chennai_routing.preprocessing.geospatial import project_to_metric_crs

DEFAULT_DISTANCE_SWEEP_METERS = (50.0, 100.0, 150.0, 200.0, 250.0)


@dataclass(frozen=True)
class MappingSweepSummary:
    """How many evidence features join roads at each matching distance."""

    distance_meters: float
    evidence_count: int
    matched_feature_count: int
    unmatched_feature_count: int
    matched_arc_count: int


def evidence_points(features: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return point evidence only. Polygons are handled by intersection."""

    points = features[features.geometry.geom_type == "Point"].copy()
    return gpd.GeoDataFrame(points, geometry="geometry", crs=features.crs)


def map_points_to_nearest_roads(
    points: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
    *,
    max_distance_meters: float,
) -> gpd.GeoDataFrame:
    """Join points to nearest roads without assigning a road state."""

    if max_distance_meters <= 0:
        raise ValueError("max_distance_meters must be positive.")
    if points.empty or road_edges.empty:
        return gpd.GeoDataFrame(geometry=[], crs=points.crs)
    if points.crs != road_edges.crs:
        raise ValueError(f"CRS mismatch: {points.crs!s} != {road_edges.crs!s}")

    points_metric, roads_metric = project_to_metric_crs(points, road_edges)
    roads_for_join = roads_metric.reset_index().copy()
    nearest = gpd.sjoin_nearest(
        points_metric,
        roads_for_join,
        how="left",
        max_distance=max_distance_meters,
        distance_col="distance_to_road_m",
    )
    nearest["matching_distance_threshold_m"] = max_distance_meters
    nearest["mapping_basis"] = (
        "Nearest OSM arc within a declared matching-distance scenario; "
        "the distance is not a measured GPS accuracy."
    )
    return gpd.GeoDataFrame(nearest, geometry="geometry", crs=points_metric.crs)


def sweep_point_mapping(
    points: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
    distances_meters: tuple[float, ...] = DEFAULT_DISTANCE_SWEEP_METERS,
) -> tuple[dict[float, gpd.GeoDataFrame], list[MappingSweepSummary]]:
    """Map the same points at several distances and report coverage change."""

    joined: dict[float, gpd.GeoDataFrame] = {}
    summaries: list[MappingSweepSummary] = []
    for distance in distances_meters:
        mapped = map_points_to_nearest_roads(
            points,
            road_edges,
            max_distance_meters=distance,
        )
        matched = mapped[mapped["distance_to_road_m"].notna()] if not mapped.empty else mapped
        matched_count = 0 if matched.empty else int(matched["distance_to_road_m"].notna().sum())
        arc_count = 0
        if not matched.empty and {"u", "v", "key"}.issubset(matched.columns):
            arc_count = int(
                matched.dropna(subset=["u", "v", "key"]).groupby(["u", "v", "key"]).ngroups
            )
        summaries.append(
            MappingSweepSummary(
                distance_meters=distance,
                evidence_count=len(points),
                matched_feature_count=matched_count,
                unmatched_feature_count=max(len(points) - matched_count, 0),
                matched_arc_count=arc_count,
            )
        )
        joined[distance] = mapped
    return joined, summaries


def intersect_polygons_with_roads(
    polygons: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Intersect historical inundation polygons with road edges."""

    if polygons.empty or road_edges.empty:
        return gpd.GeoDataFrame(geometry=[], crs=road_edges.crs)
    polygons_metric, roads_metric = project_to_metric_crs(polygons, road_edges)
    roads_reset = roads_metric.reset_index()
    joined = gpd.sjoin(roads_reset, polygons_metric, predicate="intersects", how="inner")
    joined["mapping_basis"] = (
        "Road geometry intersects a historical inundation polygon. "
        "This is inventory overlay, not an observed 2015 closure."
    )
    return gpd.GeoDataFrame(joined, geometry="geometry", crs=roads_metric.crs)


def summaries_as_records(summaries: list[MappingSweepSummary]) -> list[dict[str, float | int]]:
    return [asdict(item) for item in summaries]
