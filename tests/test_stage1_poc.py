import math

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point

from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.models.capacity import effective_capacity
from chennai_routing.preprocessing.geospatial import map_flood_points_to_nearest_roads
from chennai_routing.preprocessing.validation import require_same_crs
from chennai_routing.routing.dijkstra import shortest_path
from chennai_routing.stage1_poc import apply_stage1_costs


def test_crs_compatibility_validation() -> None:
    left = gpd.GeoDataFrame(geometry=[Point(80.25, 13.05)], crs="EPSG:4326")
    right = gpd.GeoDataFrame(geometry=[Point(80.25, 13.05)], crs="EPSG:4326")
    require_same_crs(left, right)

    mismatched = right.to_crs("EPSG:3857")
    with pytest.raises(ValueError, match="CRS mismatch"):
        require_same_crs(left, mismatched)


def test_flood_point_maps_to_nearest_road_edge() -> None:
    flood = gpd.GeoDataFrame(
        {
            "flood_id": ["historical_hotspot_1"],
            "name": ["Historical hotspot"],
            "source": ["OpenCity test fixture"],
            "data_classification": ["HISTORICAL"],
        },
        geometry=[Point(80.2500, 13.0500)],
        crs="EPSG:4326",
    )
    roads = gpd.GeoDataFrame(
        {
            "u": [1],
            "v": [2],
            "key": [0],
            "osmid": [101],
            "length": [50.0],
        },
        geometry=[LineString([(80.2499, 13.0499), (80.2501, 13.0501)])],
        crs="EPSG:4326",
    ).set_index(["u", "v", "key"])

    mapped = map_flood_points_to_nearest_roads(flood, roads, max_distance_meters=50)

    assert len(mapped) == 1
    assert mapped.iloc[0]["u"] == 1
    assert mapped.iloc[0]["v"] == 2
    assert mapped.iloc[0]["road_state"] == "BLOCKED"
    assert mapped.geometry.iloc[0].geom_type == "LineString"


def test_bpr_and_capacity_blocked_edge_becomes_unavailable() -> None:
    assert effective_capacity(1200, "NORMAL") == 1200
    assert effective_capacity(1200, "BLOCKED") == 0
    assert math.isfinite(bpr_travel_time(30, 600, 1200))
    assert math.isinf(bpr_travel_time(30, 600, 0))


def test_blocked_edge_exclusion_changes_route() -> None:
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=0.0, y=0.0)
    graph.add_node(2, x=1.0, y=0.0)
    graph.add_node(3, x=0.0, y=1.0)
    graph.add_node(4, x=1.0, y=1.0)
    graph.add_edge(1, 2, key=0, length=10.0, travel_time=10.0)
    graph.add_edge(1, 3, key=0, length=10.0, travel_time=11.0)
    graph.add_edge(3, 4, key=0, length=10.0, travel_time=11.0)
    graph.add_edge(4, 2, key=0, length=10.0, travel_time=11.0)

    apply_stage1_costs(graph)
    before = shortest_path(graph, 1, 2, weight="stage1_weight")

    apply_stage1_costs(graph, {(1, 2, 0)})
    after = shortest_path(graph, 1, 2, weight="stage1_weight")

    assert before == [1, 2]
    assert after == [1, 3, 4, 2]
