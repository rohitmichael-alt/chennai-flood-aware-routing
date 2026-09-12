"""Stage 8 public-facility and WorldPop accessibility evaluation.

The Stage 3 GraphML is streamed into compact arrays to avoid NetworkX's
large Python-object overhead for the city-scale multigraph.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import mapping

from chennai_routing.config import get_project_paths
from chennai_routing.data.flood import parse_kml_points
from chennai_routing.evaluation.metrics import summarize_accessibility
from chennai_routing.routing.quantization import QuantizationPolicy, quantize_travel_time_ms

FACILITY_SOURCES = {
    "uphc": {
        "file": "uphc.kml",
        "url": "https://data.opencity.in/dataset/e08b7485-40ab-4401-861f-f790ed8e5328/resource/5a81427f-0aa1-4270-8df4-5d4cef250912/download/a33b403b-f341-4214-8613-88e2ec227359.kml",
        "expected_sha256": "a700d7e837a5466d38e99a6ed1b67a2ff27be9638605f77b5051fef3b85055eb",
        "meaning": "Primary health centre catalogue; not a trauma-hospital list.",
    },
    "uchc": {
        "file": "uchc.kml",
        "url": "https://data.opencity.in/dataset/e08b7485-40ab-4401-861f-f790ed8e5328/resource/cd4effee-997f-4fe0-b376-8801080c6962/download/a604ea86-6bed-45ab-89cf-074fb5a59bfc.kml",
        "expected_sha256": "45e31b7dc026f54dd4e03191c2b91278a9722af5ace5425ebeb44de5c1c637ed",
        "meaning": "Community health centre catalogue; capability/status unverified.",
    },
    "fire": {
        "file": "fire_stations.kml",
        "url": "https://data.opencity.in/dataset/ea5bb2ae-3fa7-46cd-8af6-9e8da42810bb/resource/39d3601b-cd42-4c11-a6c3-8fc4b057b38a/download/9097a4c9-cd79-4df1-8552-1c67f280ede3.kml",
        "expected_sha256": "f41a5afb44e316aea26403f8403b08e14fcac9f13c2d5947d3e5ba859736dad9",
        "meaning": "Fire-station catalogue; operating readiness unverified.",
    },
}
WORLDPOP_SOURCE = {
    "file": "ind_pop_2015_CN_1km_R2025A_UA_v1.tif",
    "url": "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2015/IND/v1/1km_ua/constrained/ind_pop_2015_CN_1km_R2025A_UA_v1.tif",
    "item": "ind_pop_2015_CN_1km_R2025A_UA_v1",
    "expected_sha256": "e4c629155db214d22fc5f2b3bb29e018e6261e8855e30f727131f5c1d9a25013",
}
GRAPHML_NS = "{http://graphml.graphdrawing.org/xmlns}"


@dataclass(frozen=True)
class CompactRoadGraph:
    node_ids: np.ndarray
    longitudes: np.ndarray
    latitudes: np.ndarray
    reverse_csr: csr_matrix
    pair_records: dict[tuple[int, int], tuple[float, str, str, str]]
    observed_arc_count: int
    scenario_arc_count: int
    original_arc_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_compact_graph(path: Path) -> CompactRoadGraph:
    """Stream GraphML and retain the least-cost parallel arc per ordered pair."""

    key_names: dict[str, str] = {}
    node_ids: list[str] = []
    lons: list[float] = []
    lats: list[float] = []
    node_index: dict[str, int] = {}
    best: dict[tuple[int, int], tuple[float, str, str, str]] = {}
    observed = scenario = original_arcs = 0
    policy = QuantizationPolicy()
    for _event, elem in ET.iterparse(path, events=("end",)):
        tag = elem.tag.removeprefix(GRAPHML_NS)
        if tag == "key":
            key_names[str(elem.get("id"))] = str(elem.get("attr.name"))
        elif tag == "node":
            values = {key_names.get(str(child.get("key")), ""): child.text for child in elem}
            node_id = str(elem.get("id"))
            node_index[node_id] = len(node_ids)
            node_ids.append(node_id)
            lons.append(float(values["x"]))
            lats.append(float(values["y"]))
            elem.clear()
        elif tag == "edge":
            original_arcs += 1
            values = {key_names.get(str(child.get("key")), ""): child.text for child in elem}
            explicit = values.get("stage3_explicit_speed_kph")
            try:
                speed = float(explicit) if explicit not in (None, "", "nan") else math.nan
            except ValueError:
                speed = math.nan
            if not math.isfinite(speed) or speed <= 0:
                speed = policy.scenario_default_speed_kph
                scenario += 1
            else:
                observed += 1
            weight = quantize_travel_time_ms(float(values["length"]), speed, policy) / 1000.0
            pair = (node_index[str(elem.get("source"))], node_index[str(elem.get("target"))])
            record = (
                weight,
                str(values.get("stage3_arc_id", "UNAVAILABLE")),
                str(values.get("osmid", "UNAVAILABLE")),
                str(elem.get("id", "0")),
            )
            if pair not in best or record[0] < best[pair][0]:
                best[pair] = record
            elem.clear()
    tails = np.fromiter((pair[0] for pair in best), dtype=np.int32)
    heads = np.fromiter((pair[1] for pair in best), dtype=np.int32)
    weights = np.fromiter((record[0] for record in best.values()), dtype=np.float64)
    reverse = coo_matrix((weights, (heads, tails)), shape=(len(node_ids), len(node_ids))).tocsr()
    return CompactRoadGraph(
        np.asarray(node_ids, dtype=object),
        np.asarray(lons),
        np.asarray(lats),
        reverse,
        best,
        observed,
        scenario,
        original_arcs,
    )


def _nearest_indices(
    graph: CompactRoadGraph, longitudes: np.ndarray, latitudes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    project = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    node_x, node_y = project.transform(graph.longitudes, graph.latitudes)
    query_x, query_y = project.transform(longitudes, latitudes)
    distances, indices = cKDTree(np.column_stack((node_x, node_y))).query(
        np.column_stack((query_x, query_y)), k=1
    )
    return np.asarray(indices, dtype=np.int32), np.asarray(distances, dtype=float)


def _nearest_nodes(
    graph: object, longitudes: np.ndarray, latitudes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Compatibility helper used by the unit-scale projected-CRS test."""

    nodes = np.asarray(list(graph.nodes), dtype=object)  # type: ignore[attr-defined]
    compact = CompactRoadGraph(
        node_ids=nodes,
        longitudes=np.asarray([float(graph.nodes[node]["x"]) for node in nodes]),  # type: ignore[attr-defined]
        latitudes=np.asarray([float(graph.nodes[node]["y"]) for node in nodes]),  # type: ignore[attr-defined]
        reverse_csr=csr_matrix((len(nodes), len(nodes))),
        pair_records={},
        observed_arc_count=0,
        scenario_arc_count=0,
        original_arc_count=0,
    )
    indices, distances = _nearest_indices(compact, longitudes, latitudes)
    return nodes[indices], distances


def _population_cells(tif_path: Path, boundary_path: Path) -> tuple[np.ndarray, ...]:
    import rasterio
    from rasterio.mask import mask

    boundary = gpd.read_file(boundary_path).to_crs("EPSG:4326")
    with rasterio.open(tif_path) as dataset:
        geometry = boundary.to_crs(dataset.crs).geometry.union_all()
        values, transform = mask(dataset, [mapping(geometry)], crop=True, filled=False)
        band = values[0]
        rows, cols = np.where((~band.mask) & np.isfinite(band.data) & (band.data > 0))
        populations = band.data[rows, cols].astype(float)
        # Apply the affine transform directly.  This avoids a Windows GDAL
        # runtime lookup performed by rasterio.transform.xy while producing
        # the same pixel-centre coordinates.
        xs = transform.c + (cols + 0.5) * transform.a + (rows + 0.5) * transform.b
        ys = transform.f + (cols + 0.5) * transform.d + (rows + 0.5) * transform.e
        to_wgs84 = Transformer.from_crs(dataset.crs, "EPSG:4326", always_xy=True)
        lons, lats = to_wgs84.transform(np.asarray(xs), np.asarray(ys))
    return np.asarray(lons), np.asarray(lats), populations


def _facility_points(raw_dir: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    provenance: dict[str, object] = {}
    for facility_class, source in FACILITY_SOURCES.items():
        path = raw_dir / str(source["file"])
        digest = _sha256(path)
        if digest != source["expected_sha256"]:
            raise ValueError(f"Checksum mismatch for {path.name}: {digest}")
        frame = parse_kml_points(path)
        provenance[facility_class] = {
            **source,
            "sha256": digest,
            "bytes": path.stat().st_size,
            "feature_count": len(frame),
            "classification": "OBSERVED_CATALOGUE",
        }
        path.with_suffix(path.suffix + ".provenance.json").write_text(
            json.dumps(provenance[facility_class], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for index, record in frame.iterrows():
            rows.append(
                {
                    "facility_id": f"{facility_class}_{index}",
                    "facility_class": facility_class,
                    "name": str(record.get("name", "")),
                    "longitude": float(record.geometry.x),
                    "latitude": float(record.geometry.y),
                }
            )
    return rows, provenance


def _reverse_without_blocked(
    graph: CompactRoadGraph, blocked_arc_ids: set[str]
) -> tuple[csr_matrix, int]:
    retained = [(pair, record) for pair, record in graph.pair_records.items() if record[1] not in blocked_arc_ids]
    tails = np.fromiter((pair[0] for pair, _ in retained), dtype=np.int32)
    heads = np.fromiter((pair[1] for pair, _ in retained), dtype=np.int32)
    weights = np.fromiter((record[0] for _, record in retained), dtype=np.float64)
    matrix = coo_matrix((weights, (heads, tails)), shape=graph.reverse_csr.shape).tocsr()
    return matrix, len(graph.pair_records) - len(retained)


def _accessibility(
    reverse_graph: csr_matrix,
    facility_rows: list[dict[str, object]],
    facility_indices: np.ndarray,
    origin_populations: dict[int, float],
    threshold: float,
) -> dict[str, object]:
    result: dict[str, object] = {}
    origins = np.fromiter(origin_populations, dtype=np.int32)
    weights = list(origin_populations.values())
    for facility_class in sorted(FACILITY_SOURCES):
        targets = np.asarray(
            [index for row, index in zip(facility_rows, facility_indices) if row["facility_class"] == facility_class],
            dtype=np.int32,
        )
        distances = dijkstra(reverse_graph, directed=True, indices=targets, min_only=True)
        result[facility_class] = asdict(
            summarize_accessibility([float(value) for value in distances[origins]], weights, threshold=threshold)
        )
    return result


def _dependency_rankings(
    graph: CompactRoadGraph,
    facility_indices: set[int],
    origin_populations: dict[int, float],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    outcome = dijkstra(
        graph.reverse_csr,
        directed=True,
        indices=np.asarray(sorted(facility_indices), dtype=np.int32),
        min_only=True,
        return_predecessors=True,
    )
    distances, predecessors = outcome[0], outcome[1]
    exposure: dict[tuple[int, int], float] = {}
    for origin, population in origin_populations.items():
        current = origin
        seen: set[int] = set()
        while current not in facility_indices and current not in seen and math.isfinite(float(distances[current])):
            seen.add(current)
            following = int(predecessors[current])
            if following < 0:
                break
            pair = (current, following)
            if pair not in graph.pair_records:
                break
            exposure[pair] = exposure.get(pair, 0.0) + population
            current = following
    ranked = sorted(exposure.items(), key=lambda item: (-item[1], item[0]))
    arc_rows: list[dict[str, object]] = []
    way_totals: dict[str, float] = {}
    for rank, (pair, population) in enumerate(ranked, start=1):
        _weight, arc_id, way_id, edge_key = graph.pair_records[pair]
        way_totals[way_id] = way_totals.get(way_id, 0.0) + population
        if rank <= 50:
            arc_rows.append(
                {
                    "rank": rank,
                    "stage3_arc_id": arc_id,
                    "osm_way_id": way_id,
                    "u": str(graph.node_ids[pair[0]]),
                    "v": str(graph.node_ids[pair[1]]),
                    "key": edge_key,
                    "dependent_population": float(population),
                }
            )
    way_rows = [
        {"rank": rank, "osm_way_id": way, "summed_arc_dependency_population": float(pop)}
        for rank, (way, pop) in enumerate(
            sorted(way_totals.items(), key=lambda item: (-item[1], item[0]))[:50], start=1
        )
    ]
    return arc_rows, way_rows


def run_stage8_accessibility(*, threshold_seconds: float = 1800.0) -> dict[str, object]:
    paths = get_project_paths()
    graph_path = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    boundary_path = paths.processed_boundary / "gcc_boundary_2022.geojson"
    if not graph_path.is_file() or not boundary_path.is_file():
        raise FileNotFoundError("Stage 8 requires the regenerated Stage 3 graph and boundary.")
    print("Stage 8: validating facility catalogues and WorldPop raster", flush=True)
    facility_rows, facility_provenance = _facility_points(paths.raw_data / "facilities")
    tif_path = paths.raw_data / "population" / str(WORLDPOP_SOURCE["file"])
    population_sha = _sha256(tif_path)
    if population_sha != WORLDPOP_SOURCE["expected_sha256"]:
        raise ValueError(f"WorldPop checksum mismatch: {population_sha}")
    pop_lons, pop_lats, populations = _population_cells(tif_path, boundary_path)

    print("Stage 8: streaming compact Stage 3 graph", flush=True)
    graph = _stream_compact_graph(graph_path)
    print(
        f"Stage 8: streamed {len(graph.node_ids)} nodes and "
        f"{graph.original_arc_count} arcs into {len(graph.pair_records)} ordered pairs",
        flush=True,
    )
    facility_indices, facility_distances = _nearest_indices(
        graph,
        np.asarray([row["longitude"] for row in facility_rows]),
        np.asarray([row["latitude"] for row in facility_rows]),
    )
    for row, index, distance in zip(facility_rows, facility_indices, facility_distances):
        row["node"] = str(graph.node_ids[index])
        row["snap_distance_m"] = float(distance)
    population_indices, population_distances = _nearest_indices(graph, pop_lons, pop_lats)
    origin_populations: dict[int, float] = {}
    for index, population in zip(population_indices, populations):
        origin_populations[int(index)] = origin_populations.get(int(index), 0.0) + float(population)

    print("Stage 8: baseline accessibility", flush=True)
    accessibility = _accessibility(graph.reverse_csr, facility_rows, facility_indices, origin_populations, threshold_seconds)
    road_state_csv = paths.processed_data / "road_state" / "stage4_road_states.csv"
    with road_state_csv.open(encoding="utf-8") as handle:
        blocked_ids = {
            str(row["arc_id"])
            for row in csv.DictReader(handle)
            if row.get("state") == "BLOCKED" and row.get("arc_id")
        }
    disrupted_graph, removed_count = _reverse_without_blocked(graph, blocked_ids)
    print("Stage 8: historical-flood scenario accessibility", flush=True)
    disrupted_accessibility = _accessibility(
        disrupted_graph, facility_rows, facility_indices, origin_populations, threshold_seconds
    )
    fire_indices = {
        int(index)
        for row, index in zip(facility_rows, facility_indices)
        if row["facility_class"] == "fire"
    }
    print("Stage 8: directed-arc and OSM-way dependency rankings", flush=True)
    critical_arcs, critical_ways = _dependency_rankings(graph, fire_indices, origin_populations)

    compliance_path = paths.root / "docs" / "evidence" / "STAGE7_RESERVATION_RESULTS.json"
    compliance_evidence = json.loads(compliance_path.read_text(encoding="utf-8"))
    compliance = [
        {
            "seed": row["seed"],
            "compliance": row["compliance"],
            "mean_realized_bpr_seconds": row["mean_realized_bpr_seconds"],
            "maximum_volume_capacity_ratio": row["maximum_volume_capacity_ratio"],
        }
        for row in compliance_evidence["runs"]
    ]

    evidence = {
        "stage": 8,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision": "PASS WITH LIMITATIONS",
        "facility_provenance": facility_provenance,
        "relief_centres": {
            "file": "relief_centres_2024.pdf",
            "sha256": _sha256(paths.raw_data / "facilities" / "relief_centres_2024.pdf"),
            "status": "EXCLUDED_UNVERIFIED_COORDINATES",
            "claim_limit": "The PDF address list is preserved but not geocoded or treated as activated centres.",
        },
        "population_provenance": {
            **WORLDPOP_SOURCE,
            "sha256": population_sha,
            "bytes": tif_path.stat().st_size,
            "classification": "MODELLED",
            "positive_cells_in_boundary": int(len(populations)),
            "represented_population": float(populations.sum()),
        },
        "graph_projection": {
            "method": "Streaming GraphML; least-cost arc retained for each ordered node pair",
            "node_count": int(len(graph.node_ids)),
            "original_directed_arc_count": graph.original_arc_count,
            "projected_ordered_pair_count": len(graph.pair_records),
        },
        "snapping": {
            "method": "EPSG:32644 Euclidean nearest Stage 3 node",
            "facility_count": len(facility_rows),
            "facility_max_distance_m": float(facility_distances.max()),
            "population_origin_node_count": len(origin_populations),
            "population_cell_max_distance_m": float(population_distances.max()),
        },
        "metric": {
            "unit": "seconds",
            "observed_speed_arc_count": graph.observed_arc_count,
            "scenario_speed_arc_count": graph.scenario_arc_count,
            "scenario_default_speed_kph": QuantizationPolicy().scenario_default_speed_kph,
        },
        "accessibility": accessibility,
        "stage4_blocked_overlay": {
            "classification": "SCENARIO from historical evidence",
            "matched_projected_directed_arc_count": removed_count,
            "accessibility": disrupted_accessibility,
        },
        "compliance_sweep": {
            "classification": "SYNTHETIC / SCENARIO",
            "probabilities": [0.0, 0.25, 0.5, 0.75, 1.0],
            "seeds": [8597, 8598, 8599],
            "source_evidence": "docs/evidence/STAGE7_RESERVATION_RESULTS.json",
            "runs": compliance,
        },
        "directed_arc_criticality": {
            "facility_class": "fire",
            "metric": "Population whose deterministic baseline nearest-facility path uses the directed arc.",
            "ranking_scope": "All projected directed arcs used by represented population origins; top 50 reported.",
            "claim_limit": "Dependency exposure is not recomputed closure impact and is not causal road importance.",
            "directed_arc_ranking": critical_arcs,
            "osm_way_group_ranking": critical_ways,
        },
        "claim_limit": (
            "Catalogue and modelled-population accessibility on a declared Stage 3 projection. "
            "Most road speeds use a labelled SCENARIO value; facility capacity, opening status, "
            "trauma capability, turn restrictions, and traffic calibration are unavailable. "
            "Population weighting is not an equity measure."
        ),
    }
    evidence_path = paths.root / "docs" / "evidence" / "STAGE8_ACCESSIBILITY_RESULTS.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tif_path.with_suffix(tif_path.suffix + ".provenance.json").write_text(
        json.dumps(evidence["population_provenance"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence
