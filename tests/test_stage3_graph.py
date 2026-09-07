import gzip
import hashlib
import json
import math
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pytest
from shapely.geometry import Polygon

from chennai_routing.data.boundary import (
    GCC_2022_WARD_RESOURCE_ID,
    GCC_WARD_PACKAGE_API,
    download_gcc_2022_wards,
    load_and_audit_gcc_2022_wards,
    write_boundary_evidence,
)
from chennai_routing.preprocessing.roads import (
    audit_road_graph,
    normalize_road_graph,
    parse_explicit_osm_maxspeed_kph,
)


class _FakeResponse:
    def __init__(self, *, payload: dict[str, object] | None = None, content: bytes = b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        if self._payload is None:
            raise AssertionError("JSON was not configured for this fake response.")
        return self._payload


class _FakeSession:
    def __init__(self, package: dict[str, object], content: bytes):
        self.package = package
        self.content = content
        self.calls: list[str] = []

    def get(self, url: str, **_kwargs: object) -> _FakeResponse:
        self.calls.append(url)
        if url == GCC_WARD_PACKAGE_API:
            return _FakeResponse(payload=self.package)
        return _FakeResponse(content=self.content)


def _package_payload(resource_url: str) -> dict[str, object]:
    return {
        "success": True,
        "result": {
            "name": "gcc-ward-information",
            "title": "GCC Ward Information",
            "metadata_modified": "2026-03-02T06:30:59.799959",
            "organization": {"title": "Greater Chennai Corporation (GCC)"},
            "resources": [
                {
                    "id": GCC_2022_WARD_RESOURCE_ID,
                    "name": "Chennai GCC Ward Map - 2022",
                    "url": resource_url,
                    "format": "KML",
                    "state": "active",
                    "last_modified": "2025-11-25T14:04:12.009306",
                    "source": "https://chennaicorporation.gov.in",
                    "license_id": "Public Domain",
                }
            ],
        },
    }


def _two_ward_fixture(path: Path) -> Path:
    wards = gpd.GeoDataFrame(
        {"Name": ["Ward 1", "Ward 2"]},
        geometry=[
            Polygon([(80.0, 13.0), (80.1, 13.0), (80.1, 13.1), (80.0, 13.1)]),
            Polygon([(80.1, 13.0), (80.2, 13.0), (80.2, 13.1), (80.1, 13.1)]),
        ],
        crs="EPSG:4326",
    )
    wards.to_file(path, driver="GeoJSON")
    return path


def test_boundary_download_pins_resource_and_records_integrity(tmp_path: Path) -> None:
    resource_url = "https://example.test/gcc-wards-2022.kml"
    content = b"<kml>fixture</kml>"
    session = _FakeSession(_package_payload(resource_url), content)

    kml_path, metadata_path, provenance = download_gcc_2022_wards(
        tmp_path,
        session=session,  # type: ignore[arg-type]
        retrieved_at_utc="2026-09-07T00:00:00+00:00",
    )

    assert session.calls == [GCC_WARD_PACKAGE_API, resource_url]
    assert kml_path.read_bytes() == content
    assert provenance.resource_id == GCC_2022_WARD_RESOURCE_ID
    assert provenance.resource_license == "Public Domain"
    assert provenance.content_sha256 == hashlib.sha256(content).hexdigest()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["provenance"]["retrieved_at_utc"] == "2026-09-07T00:00:00+00:00"


def test_boundary_download_rejects_missing_pinned_resource(tmp_path: Path) -> None:
    package = _package_payload("https://example.test/resource.kml")
    package["result"]["resources"] = []  # type: ignore[index]
    session = _FakeSession(package, b"unused")

    with pytest.raises(ValueError, match="Expected exactly one"):
        download_gcc_2022_wards(tmp_path, session=session)  # type: ignore[arg-type]


def test_boundary_audit_enforces_count_and_builds_valid_union(tmp_path: Path) -> None:
    source = _two_ward_fixture(tmp_path / "wards.geojson")

    wards, union, audit = load_and_audit_gcc_2022_wards(
        source,
        expected_feature_count=2,
    )

    assert len(wards) == 2
    assert len(union) == 1
    assert audit.feature_count == 2
    assert audit.duplicate_name_count == 0
    assert audit.union_is_valid
    assert audit.bounds_wgs84 == pytest.approx((80.0, 13.0, 80.2, 13.1))

    with pytest.raises(ValueError, match="Expected 3"):
        load_and_audit_gcc_2022_wards(source, expected_feature_count=3)


def test_boundary_evidence_archives_exact_source_deterministically(tmp_path: Path) -> None:
    source = _two_ward_fixture(tmp_path / "wards.geojson")
    wards, union, audit = load_and_audit_gcc_2022_wards(
        source,
        expected_feature_count=2,
    )
    content = b"<kml>preserved source</kml>"
    raw_kml = tmp_path / "source.kml"
    raw_kml.write_bytes(content)
    provenance_session = _FakeSession(
        _package_payload("https://example.test/resource.kml"),
        content,
    )
    _, _, provenance = download_gcc_2022_wards(
        tmp_path / "download",
        session=provenance_session,  # type: ignore[arg-type]
        retrieved_at_utc="2026-09-07T00:00:00+00:00",
    )

    evidence = tmp_path / "docs" / "evidence" / "boundary.json"
    _, _, archive = write_boundary_evidence(
        wards=wards,
        union=union,
        audit=audit,
        provenance=provenance,
        processed_directory=tmp_path / "processed",
        evidence_path=evidence,
        raw_kml_path=raw_kml,
        artifact_root=tmp_path,
    )

    with gzip.open(archive, "rb") as compressed:
        assert compressed.read() == content
    manifest = json.loads(evidence.read_text(encoding="utf-8"))
    assert manifest["decision"] == "PASS"
    assert not Path(manifest["artifacts"]["archived_source"]).is_absolute()


def _road_graph(reverse_insertion: bool = False) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(crs="EPSG:4326")
    nodes = [(1, {"x": 80.0, "y": 13.0}), (2, {"x": 80.1, "y": 13.1})]
    for node, data in reversed(nodes) if reverse_insertion else nodes:
        graph.add_node(node, **data)
    edges = [
        (1, 2, 0, {"osmid": 100, "length": 100.0, "maxspeed": "50"}),
        (1, 2, 1, {"osmid": 101, "length": 120.0, "maxspeed": "30 mph"}),
    ]
    for u, v, key, data in reversed(edges) if reverse_insertion else edges:
        graph.add_edge(u, v, key=key, **data)
    return graph


def test_road_normalization_is_insertion_order_independent() -> None:
    first = normalize_road_graph(_road_graph())
    second = normalize_road_graph(_road_graph(reverse_insertion=True))

    first_ids = {
        (u, v, key): data["stage3_arc_id"]
        for u, v, key, data in first.edges(keys=True, data=True)
    }
    second_ids = {
        (u, v, key): data["stage3_arc_id"]
        for u, v, key, data in second.edges(keys=True, data=True)
    }

    assert first_ids == second_ids
    assert len(set(first_ids.values())) == 2


def test_explicit_speed_parser_does_not_guess_compound_or_special_values() -> None:
    assert parse_explicit_osm_maxspeed_kph("50") == 50.0
    assert parse_explicit_osm_maxspeed_kph("80 km/h") == 80.0
    assert parse_explicit_osm_maxspeed_kph("30 mph") == pytest.approx(48.28032)
    assert parse_explicit_osm_maxspeed_kph("50;60") is None
    assert parse_explicit_osm_maxspeed_kph("signals") is None
    assert parse_explicit_osm_maxspeed_kph(None) is None


def test_road_audit_reports_missingness_instead_of_imputing() -> None:
    graph = _road_graph()
    graph.add_edge(2, 1, key=0, osmid=102, length=100.0, maxspeed="signals")
    normalized = normalize_road_graph(graph)
    audit = audit_road_graph(normalized)

    assert audit.node_count == 2
    assert audit.arc_count == 3
    assert audit.directed_pairs_with_parallel_arcs == 1
    assert audit.arcs_in_parallel_directed_pairs == 2
    assert audit.explicit_speed_count == 2
    assert audit.unparseable_maxspeed_count == 1
    assert audit.free_flow_time_count == 2
    assert audit.missing_lanes_count == 3
    assert audit.duplicate_arc_id_count == 0
    assert normalized[2][1][0]["stage3_free_flow_time_seconds"] is None
    assert math.isfinite(normalized[1][2][0]["stage3_free_flow_time_seconds"])
