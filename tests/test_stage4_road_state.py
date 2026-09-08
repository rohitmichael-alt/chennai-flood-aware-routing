from pathlib import Path

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import LineString, Point

from chennai_routing.data.elevation import build_sample_grid
from chennai_routing.data.flood import parse_kml_features
from chennai_routing.data.rainfall import earthdata_imerg_status
from chennai_routing.models.road_state import (
    assign_states_from_hotspots,
    assign_states_from_inundation,
    merge_state_rows,
    rainfall_does_not_assign_road_state,
)
from chennai_routing.preprocessing.evidence_mapping import (
    map_points_to_nearest_roads,
    sweep_point_mapping,
)
from chennai_routing.stage4_road_state import graph_edges_to_gdf


def _kml_document(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"{body}"
        "</Document></kml>"
    )


def test_parse_kml_features_reads_points_and_polygons(tmp_path: Path) -> None:
    kml = _kml_document(
        """
        <Placemark>
          <name>hotspot</name>
          <Point><coordinates>80.25,13.05,0</coordinates></Point>
        </Placemark>
        <Placemark>
          <name>zone</name>
          <Polygon>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>
                  80.24,13.04,0 80.26,13.04,0 80.26,13.06,0 80.24,13.06,0 80.24,13.04,0
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>
        </Placemark>
        """
    )
    path = tmp_path / "mixed.kml"
    path.write_text(kml, encoding="utf-8")
    features = parse_kml_features(
        path,
        source="fixture",
        evidence_class="HISTORICAL_INVENTORY",
        id_prefix="fx",
    )
    assert len(features) == 2
    assert set(features.geometry.geom_type) == {"Point", "Polygon"}
    assert (features["evidence_class"] == "HISTORICAL_INVENTORY").all()


def test_mapping_sweep_does_not_assign_road_state() -> None:
    points = gpd.GeoDataFrame(
        {"feature_id": ["a"]},
        geometry=[Point(80.2500, 13.0500)],
        crs="EPSG:4326",
    )
    roads = gpd.GeoDataFrame(
        {"u": [1], "v": [2], "key": [0], "stage3_arc_id": ["arc-1"]},
        geometry=[LineString([(80.2499, 13.0499), (80.2501, 13.0501)])],
        crs="EPSG:4326",
    )
    mapped = map_points_to_nearest_roads(points, roads, max_distance_meters=50)
    assert "road_state" not in mapped.columns
    assert mapped.iloc[0]["u"] == 1
    _joined, summaries = sweep_point_mapping(points, roads, distances_meters=(5.0, 50.0))
    assert summaries[0].distance_meters == 5.0
    assert summaries[1].matched_feature_count >= summaries[0].matched_feature_count


def test_hotspot_rule_is_labelled_scenario_not_observation() -> None:
    mapped = gpd.GeoDataFrame(
        {
            "u": [1],
            "v": [2],
            "key": [0],
            "stage3_arc_id": ["arc-1"],
            "distance_to_road_m": [12.0],
        },
        geometry=[Point(80.25, 13.05)],
        crs="EPSG:4326",
    )
    rows = assign_states_from_hotspots(
        mapped,
        retrieval_time="2026-09-08T00:00:00+00:00",
        matching_distance_m=150.0,
    )
    assert rows[0].state == "BLOCKED"
    assert rows[0].evidence_class == "HISTORICAL_INVENTORY"
    assert rows[0].multiplier_class == "SCENARIO"
    assert "scenario" in rows[0].scenario_rule


def test_inundation_and_hotspot_conflict_is_recorded() -> None:
    hotspot = assign_states_from_hotspots(
        gpd.GeoDataFrame(
            {
                "u": [1],
                "v": [2],
                "key": [0],
                "stage3_arc_id": ["arc-1"],
                "distance_to_road_m": [8.0],
            },
            geometry=[Point(80.25, 13.05)],
            crs="EPSG:4326",
        ),
        retrieval_time="2026-09-08T00:00:00+00:00",
        matching_distance_m=50.0,
    )
    inundation = assign_states_from_inundation(
        gpd.GeoDataFrame(
            {
                "u": [1],
                "v": [2],
                "key": [0],
                "stage3_arc_id": ["arc-1"],
            },
            geometry=[LineString([(80.24, 13.04), (80.26, 13.06)])],
            crs="EPSG:4326",
        ),
        retrieval_time="2026-09-08T00:00:00+00:00",
    )
    merged = merge_state_rows([*hotspot, *inundation])
    assert len(merged) == 1
    assert merged[0].state == "BLOCKED"
    assert merged[0].conflict is True


def test_rainfall_rule_forbids_closure_from_precipitation() -> None:
    text = rainfall_does_not_assign_road_state()
    assert "never assign" in text
    assert "UNKNOWN" in text


def test_elevation_grid_rejects_degenerate_bounds() -> None:
    with pytest.raises(ValueError, match="positive width"):
        build_sample_grid((80.2, 13.0, 80.2, 13.1), rows=2, cols=2)
    grid = build_sample_grid((80.0, 13.0, 80.2, 13.2), rows=2, cols=2)
    assert len(grid) == 4
    assert grid[0] == (80.0, 13.0)
    assert grid[-1] == (80.2, 13.2)


def test_imerg_is_unavailable_without_earthdata() -> None:
    status = earthdata_imerg_status()
    assert "UNAVAILABLE" in status or "CREDENTIAL_FILE_PRESENT" in status


def test_graph_edges_to_gdf_requires_geometry() -> None:
    graph = nx.MultiDiGraph(crs="EPSG:4326")
    graph.add_node(1, x=80.0, y=13.0)
    graph.add_node(2, x=80.1, y=13.1)
    graph.add_edge(1, 2, key=0, stage3_arc_id="arc-1")
    with pytest.raises(ValueError, match="no edge geometries"):
        graph_edges_to_gdf(graph)
    graph[1][2][0]["geometry"] = LineString([(80.0, 13.0), (80.1, 13.1)])
    edges = graph_edges_to_gdf(graph)
    assert len(edges) == 1
    assert edges.iloc[0]["stage3_arc_id"] == "arc-1"


class _RainfallResponse:
    def __init__(self, payload: dict[str, object]):
        self._payload = payload
        self.url = "https://archive-api.open-meteo.com/v1/archive?models=era5"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _RainfallSession:
    def get(self, url: str, **_kwargs: object) -> _RainfallResponse:
        return _RainfallResponse(
            {
                "hourly": {
                    "time": ["2015-11-01T00:00", "2015-11-01T01:00"],
                    "precipitation": [1.5, 2.5],
                }
            }
        )


def test_open_meteo_rainfall_is_labelled_modelled(tmp_path: Path) -> None:
    from chennai_routing.data.rainfall import fetch_open_meteo_era5_precipitation

    _raw, table, provenance = fetch_open_meteo_era5_precipitation(
        tmp_path,
        session=_RainfallSession(),  # type: ignore[arg-type]
        retrieved_at_utc="2026-09-08T00:00:00+00:00",
    )
    assert provenance.evidence_class == "MODELLED"
    assert provenance.hourly_row_count == 2
    assert provenance.total_precipitation_mm == 4.0
    assert "not prove street flooding" in provenance.claim_limit
    assert table.is_file()
