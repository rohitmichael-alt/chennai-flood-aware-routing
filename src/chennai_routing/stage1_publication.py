"""Publication-grade Stage 1 rerun on the dated Stage 3 graph."""

from __future__ import annotations

import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from chennai_routing.config import get_project_paths
from chennai_routing.stage8_accessibility import _stream_compact_graph


def _matrix(graph: object, excluded: set[tuple[int, int]] | None = None):
    omitted = excluded or set()
    retained = [(pair, record) for pair, record in graph.pair_records.items() if pair not in omitted]
    rows = np.fromiter((pair[0] for pair, _ in retained), dtype=np.int32)
    cols = np.fromiter((pair[1] for pair, _ in retained), dtype=np.int32)
    values = np.fromiter((record[0] for _, record in retained), dtype=float)
    return coo_matrix((values, (rows, cols)), shape=graph.reverse_csr.shape).tocsr()


def _path(predecessors: np.ndarray, source: int, target: int) -> list[int]:
    route = [target]
    current = target
    while current != source:
        current = int(predecessors[current])
        if current < 0:
            return []
        route.append(current)
    route.reverse()
    return route


def run_stage1_publication() -> dict[str, object]:
    paths = get_project_paths()
    graph_path = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    state_path = paths.processed_data / "road_state" / "stage4_road_states.csv"
    print("Stage 1: streaming the dated Stage 3 graph", flush=True)
    graph = _stream_compact_graph(graph_path)
    arc_to_pair = {record[1]: pair for pair, record in graph.pair_records.items()}
    with state_path.open(encoding="utf-8") as handle:
        blocked_ids = [
            str(row["arc_id"])
            for row in csv.DictReader(handle)
            if row.get("state") == "BLOCKED" and row.get("arc_id") in arc_to_pair
        ]
    candidate_pairs = list(dict.fromkeys(arc_to_pair[arc_id] for arc_id in blocked_ids))[:12]
    sources = np.asarray([pair[0] for pair in candidate_pairs], dtype=np.int32)
    baseline = _matrix(graph)
    disrupted = _matrix(graph, set(arc_to_pair[arc_id] for arc_id in blocked_ids))
    print(f"Stage 1: testing {len(candidate_pairs)} historical-hotspot candidates", flush=True)
    before_dist, before_pred = dijkstra(
        baseline, directed=True, indices=sources, return_predecessors=True
    )
    after_dist, after_pred = dijkstra(
        disrupted, directed=True, indices=sources, return_predecessors=True
    )
    chosen = None
    for row_index, pair in enumerate(candidate_pairs):
        before = _path(before_pred[row_index], pair[0], pair[1])
        after = _path(after_pred[row_index], pair[0], pair[1])
        if (
            len(before) == 2
            and len(after) > 2
            and math.isfinite(float(after_dist[row_index, pair[1]]))
        ):
            chosen = (row_index, pair, before, after)
            break
    if chosen is None:
        raise RuntimeError("No blocked Stage 4 candidate had a finite alternate path.")
    row_index, pair, before, after = chosen
    record = graph.pair_records[pair]
    output_graph = nx.MultiDiGraph(crs="EPSG:4326")
    selected_nodes = set(before) | set(after)
    for index in selected_nodes:
        output_graph.add_node(
            str(graph.node_ids[index]),
            x=float(graph.longitudes[index]),
            y=float(graph.latitudes[index]),
        )
    route_pairs = list(zip(before, before[1:])) + list(zip(after, after[1:]))
    for u, v in dict.fromkeys(route_pairs):
        weight, arc_id, way_id, key = graph.pair_records[(u, v)]
        output_graph.add_edge(
            str(graph.node_ids[u]),
            str(graph.node_ids[v]),
            key=key,
            weight_seconds=weight,
            stage3_arc_id=arc_id,
            osmid=way_id,
            scenario_blocked=(u, v) == pair,
        )
    artifact_dir = paths.processed_data / "stage1_publication"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    extract_path = artifact_dir / "stage1_dated_route_extract.graphml"
    nx.write_graphml(output_graph, extract_path)
    summary_path = paths.output_tables / "stage1_publication_routes.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario", "cost_seconds", "route_node_ids"])
        writer.writeheader()
        writer.writerow(
            {
                "scenario": "before_scenario_blockage",
                "cost_seconds": float(before_dist[row_index, pair[1]]),
                "route_node_ids": json.dumps([str(graph.node_ids[index]) for index in before]),
            }
        )
        writer.writerow(
            {
                "scenario": "after_historical_hotspot_scenario_blockage",
                "cost_seconds": float(after_dist[row_index, pair[1]]),
                "route_node_ids": json.dumps([str(graph.node_ids[index]) for index in after]),
            }
        )
    map_path = paths.output_maps / "stage1_publication_before_after.png"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    width, height, margin = 1400, 1000, 80
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    all_nodes = before + after
    min_lon, max_lon = float(graph.longitudes[all_nodes].min()), float(graph.longitudes[all_nodes].max())
    min_lat, max_lat = float(graph.latitudes[all_nodes].min()), float(graph.latitudes[all_nodes].max())
    lon_span, lat_span = max(max_lon - min_lon, 1e-9), max(max_lat - min_lat, 1e-9)

    def pixel(index: int) -> tuple[float, float]:
        x = margin + (float(graph.longitudes[index]) - min_lon) / lon_span * (width - 2 * margin)
        y = height - margin - (float(graph.latitudes[index]) - min_lat) / lat_span * (height - 2 * margin)
        return x, y

    draw.text((margin, 24), "Dated Stage 3 route response to a historical-hotspot SCENARIO blockage", fill="black")
    draw.line([pixel(index) for index in before], fill="#1f77b4", width=7)
    draw.line([pixel(index) for index in after], fill="#ff7f0e", width=7)
    for index in pair:
        x, y = pixel(index)
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill="#b2182b")
    draw.text((margin, height - 52), "blue: before | orange: after | red: blocked-arc endpoints", fill="black")
    image.save(map_path)
    evidence = {
        "stage": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision": "PASS WITH LIMITATIONS",
        "source_graph": "data/processed/roads/stage3_chennai_gcc_2022.graphml",
        "source_graph_arc_count": graph.original_arc_count,
        "graph_extract_definition": "Union of the before/after route arcs selected from the dated Stage 3 graph.",
        "blocked_arc": {
            "stage3_arc_id": record[1],
            "osm_way_id": record[2],
            "u": str(graph.node_ids[pair[0]]),
            "v": str(graph.node_ids[pair[1]]),
            "classification": "SCENARIO based on Stage 4 historical-hotspot overlay",
        },
        "before_cost_seconds": float(before_dist[row_index, pair[1]]),
        "after_cost_seconds": float(after_dist[row_index, pair[1]]),
        "scenario_uniform_capacity": 1200,
        "scenario_uniform_flow": 600,
        "artifacts": {
            "graphml": str(extract_path.relative_to(paths.root)),
            "csv": str(summary_path.relative_to(paths.root)),
            "png": str(map_path.relative_to(paths.root)),
        },
        "claim_limit": (
            "The blockage and uniform 1200/600 capacity-flow values are SCENARIO demonstration inputs, "
            "not a calibrated reconstruction or current Chennai road condition."
        ),
    }
    evidence_path = paths.root / "docs" / "evidence" / "STAGE1_PUBLICATION_RESULTS.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence
