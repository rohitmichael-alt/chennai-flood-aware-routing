"""Stage 3 orchestration for the reproducible Greater Chennai graph."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point

from chennai_routing.config import get_project_paths
from chennai_routing.data.boundary import (
    BoundaryAudit,
    BoundaryProvenance,
    GCC_2022_WARD_RESOURCE_ID,
    download_gcc_2022_wards,
    load_and_audit_gcc_2022_wards,
    write_boundary_evidence,
)
from chennai_routing.data.osm_snapshot import (
    NETWORK_TYPE,
    OsmSnapshotProvenance,
    acquire_dated_india_pbf,
    build_driving_graph_from_pbf,
    clip_pbf_to_polygon,
    require_osmium,
    sha256_file,
    write_clip_geojson,
)
from chennai_routing.preprocessing.roads import (
    ROAD_GRAPH_DATA_DICTIONARY,
    audit_road_graph,
    normalize_road_graph,
    write_road_graph_audit,
)
from chennai_routing.visualization.maps import plot_stage3_qa_map


@dataclass(frozen=True)
class Stage3BoundaryResult:
    """Paths and checks for the completed Stage 3 boundary substage."""

    raw_kml_path: str
    raw_metadata_path: str
    processed_wards_path: str
    processed_union_path: str
    archived_source_path: str
    evidence_path: str
    provenance: dict[str, object]
    audit: dict[str, object]
    decision: str
    next_gate: str


@dataclass(frozen=True)
class Stage3GraphResult:
    """Paths and checks for the dated OSM graph substage."""

    india_pbf_path: str
    clipped_pbf_path: str
    graphml_path: str
    audit_path: str
    evidence_path: str
    qa_map_path: str
    data_dictionary_path: str
    provenance: dict[str, object]
    audit: dict[str, object]
    software_versions: dict[str, str]
    boundary_coverage: dict[str, int]
    decision: str
    claim_limit: str


def _repository_relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def collect_stage3_software_versions() -> dict[str, str]:
    """Record interpreter and library versions used to build the graph."""

    versions = {"python": sys.version.split()[0], "osmium": require_osmium()}
    for package in ("pyrosm", "osmnx", "networkx", "geopandas", "shapely", "pandas"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "UNAVAILABLE"
    return versions


def audit_nodes_against_boundary(
    graph,
    union: gpd.GeoDataFrame,
) -> dict[str, int]:
    """Count graph nodes that intersect the GCC union versus those outside it."""

    points = []
    for _, data in graph.nodes(data=True):
        x = data.get("x")
        y = data.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            points.append(Point(float(x), float(y)))
    if not points:
        return {
            "node_count": 0,
            "nodes_inside_or_touching_union": 0,
            "nodes_outside_union": 0,
        }
    node_frame = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
    boundary = union.to_crs("EPSG:4326")
    joined = node_frame.sjoin(boundary, predicate="intersects", how="left")
    inside = int(joined.index_right.notna().sum())
    return {
        "node_count": len(points),
        "nodes_inside_or_touching_union": inside,
        "nodes_outside_union": len(points) - inside,
    }


def _load_study_union() -> gpd.GeoDataFrame:
    """Reuse the processed GCC union when present; otherwise rebuild it."""

    paths = get_project_paths()
    union_path = paths.processed_boundary / "gcc_boundary_2022.geojson"
    if union_path.is_file():
        union = gpd.read_file(union_path)
    else:
        result = run_stage3_boundary()
        union = gpd.read_file(paths.root / result.processed_union_path)
    if len(union) != 1:
        raise ValueError("Processed GCC union must contain exactly one feature.")
    return union


def run_stage3_boundary() -> Stage3BoundaryResult:
    """Acquire, validate, and preserve the exact Stage 3 study boundary."""

    paths = get_project_paths()
    kml_path, metadata_path, provenance = download_gcc_2022_wards(paths.raw_boundary)
    wards, union, audit = load_and_audit_gcc_2022_wards(
        kml_path,
        repair_invalid=True,
    )
    evidence_path = paths.root / "docs" / "evidence" / "STAGE3_BOUNDARY_RESULTS.json"
    archived_path = (
        paths.root / "docs" / "evidence" / "sources" / "gcc_wards_2022.kml.gz"
    )
    wards_path, union_path, archived_path = write_boundary_evidence(
        wards=wards,
        union=union,
        audit=audit,
        provenance=provenance,
        processed_directory=paths.processed_boundary,
        evidence_path=evidence_path,
        raw_kml_path=kml_path,
        archived_kml_path=archived_path,
        artifact_root=paths.root,
    )
    return Stage3BoundaryResult(
        raw_kml_path=_repository_relative(kml_path, paths.root),
        raw_metadata_path=_repository_relative(metadata_path, paths.root),
        processed_wards_path=_repository_relative(wards_path, paths.root),
        processed_union_path=_repository_relative(union_path, paths.root),
        archived_source_path=_repository_relative(archived_path, paths.root),
        evidence_path=_repository_relative(evidence_path, paths.root),
        provenance=asdict(provenance),
        audit=asdict(audit),
        decision=(
            "PASS WITH DOCUMENTED SOURCE GEOMETRY REPAIR"
            if audit.repaired_geometry_count
            else "PASS"
        ),
        next_gate=(
            "Acquire a dated OSM source, normalize the full road graph, and pass "
            "the Stage 3 topology and missingness audit."
        ),
    )


def run_stage3_graph() -> Stage3GraphResult:
    """Clip the dated India extract to the GCC 2022 union and audit the graph."""

    paths = get_project_paths()
    union = _load_study_union()
    clip_geojson = paths.raw_osm / "gcc_boundary_2022_clip.geojson"
    write_clip_geojson(union, clip_geojson)

    india_pbf, download_record = acquire_dated_india_pbf(paths.raw_osm)
    clipped_pbf = paths.raw_osm / "chennai_gcc_2022_india-260901.osm.pbf"
    osmium_version = clip_pbf_to_polygon(india_pbf, clip_geojson, clipped_pbf)
    graph = normalize_road_graph(build_driving_graph_from_pbf(clipped_pbf))
    audit = audit_road_graph(graph)
    coverage = audit_nodes_against_boundary(graph, union)
    software_versions = collect_stage3_software_versions()

    graphml_path = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    graphml_path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=graphml_path)
    audit_path = paths.root / "docs" / "evidence" / "STAGE3_GRAPH_AUDIT.json"
    write_road_graph_audit(audit, audit_path)
    data_dictionary_path = paths.root / "docs" / "evidence" / "STAGE3_GRAPH_DATA_DICTIONARY.json"
    data_dictionary_path.write_text(
        json.dumps(ROAD_GRAPH_DATA_DICTIONARY, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    qa_map_path = paths.root / "docs" / "evidence" / "STAGE3_GRAPH_QA_MAP.png"
    plot_stage3_qa_map(graph, union, qa_map_path)

    provenance = OsmSnapshotProvenance(
        source_url=download_record["source_url"],
        checksum_url=download_record["checksum_url"],
        filename=download_record["filename"],
        retrieved_at_utc=download_record["retrieved_at_utc"],
        last_modified_header=download_record["last_modified_header"],
        etag_header=download_record["etag_header"],
        declared_content_length=download_record["declared_content_length"],
        downloaded_bytes=download_record["downloaded_bytes"],
        provider_md5=download_record["provider_md5"],
        computed_md5=download_record["computed_md5"],
        reused_existing_pbf=download_record["reused_existing_pbf"],
        osm_license=download_record["osm_license"],
        osm_license_url=download_record["osm_license_url"],
        osm_attribution=download_record["osm_attribution"],
        clip_boundary_resource_id=GCC_2022_WARD_RESOURCE_ID,
        clipped_pbf_bytes=clipped_pbf.stat().st_size,
        clipped_pbf_sha256=sha256_file(clipped_pbf),
        osmium_version=osmium_version,
        extract_strategy="smart",
        network_type=NETWORK_TYPE,
    )
    evidence_path = paths.root / "docs" / "evidence" / "STAGE3_GRAPH_RESULTS.json"
    if audit.duplicate_arc_id_count or audit.arc_count == 0:
        decision = "FAIL"
    else:
        decision = "PASS WITH REPORTED ATTRIBUTE MISSINGNESS"
    claim_limit = (
        "This is a dated, GCC-clipped driving graph with explicit-speed coverage "
        "reported. It does not assign capacity, demand, flood state, or calibrated "
        "free-flow time to arcs whose OSM maxspeed is missing or unparseable."
    )
    evidence_path.write_text(
        json.dumps(
            {
                "stage": 3,
                "component": "chennai_road_graph",
                "decision": decision,
                "claim_limit": claim_limit,
                "command": "python scripts/run_stage3_graph.py",
                "software_versions": software_versions,
                "boundary_coverage": coverage,
                "provenance": asdict(provenance),
                "audit": asdict(audit),
                "artifacts": {
                    "clipped_pbf": str(clipped_pbf.relative_to(paths.root)),
                    "graphml": str(graphml_path.relative_to(paths.root)),
                    "audit": str(audit_path.relative_to(paths.root)),
                    "data_dictionary": str(data_dictionary_path.relative_to(paths.root)),
                    "qa_map": str(qa_map_path.relative_to(paths.root)),
                    "india_pbf": str(india_pbf.relative_to(paths.root)),
                    "clip_geojson": str(clip_geojson.relative_to(paths.root)),
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return Stage3GraphResult(
        india_pbf_path=_repository_relative(india_pbf, paths.root),
        clipped_pbf_path=_repository_relative(clipped_pbf, paths.root),
        graphml_path=_repository_relative(graphml_path, paths.root),
        audit_path=_repository_relative(audit_path, paths.root),
        evidence_path=_repository_relative(evidence_path, paths.root),
        qa_map_path=_repository_relative(qa_map_path, paths.root),
        data_dictionary_path=_repository_relative(data_dictionary_path, paths.root),
        provenance=asdict(provenance),
        audit=asdict(audit),
        software_versions=software_versions,
        boundary_coverage=coverage,
        decision=decision,
        claim_limit=claim_limit,
    )


__all__ = [
    "BoundaryAudit",
    "BoundaryProvenance",
    "Stage3BoundaryResult",
    "Stage3GraphResult",
    "run_stage3_boundary",
    "run_stage3_graph",
]
