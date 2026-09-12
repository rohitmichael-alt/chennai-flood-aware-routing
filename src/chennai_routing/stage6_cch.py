"""Stage 6: Chennai CCH mapping, quantization, and Dijkstra differential."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from types import MappingProxyType

import networkx as nx

try:  # Unix-only; Windows records memory as unavailable instead of failing.
    import resource
except ImportError:  # pragma: no cover - platform dependent
    resource = None  # type: ignore[assignment]

from chennai_routing.config import get_project_paths
from chennai_routing.preprocessing.roads import parse_explicit_osm_maxspeed_kph
from chennai_routing.routing.cch_engine import (
    RoutingKitCCHEngine,
    compute_contraction_order,
    node_latitudes_longitudes,
)
from chennai_routing.routing.engine import EdgeId, MetricSnapshot, NodeId
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine
from chennai_routing.routing.quantization import (
    GEOGRAPHIC_DETOUR_FACTOR,
    QUANTIZATION_UNIT,
    ROUTINGKIT_INFINITY,
    SCENARIO_DEFAULT_SPEED_KPH,
    QuantizationPolicy,
    bbox_diameter_m,
    geographic_overflow_bound_ms,
    path_quantization_error_bound_ms,
    quantize_travel_time_ms,
)

STAGE6_SEED = 8597
TURN_MODEL_DECISION = "RESTRICTED_TOPOLOGY_NO_TURN_EXPANSION"


@dataclass(frozen=True)
class Stage6Result:
    """Paths and the Stage 6 evidence-gate decision."""

    evidence_path: str
    decision: str
    turn_model: str
    order_method: str
    differential_mismatch_count: int
    claim_limit: str
    next_gate: str


def _repository_relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coerce_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number == number else None
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if number == number else None


def load_stage3_graphml(path: Path) -> nx.MultiDiGraph:
    """Load the Stage 3 GraphML without OSMnx oneway boolean coercion."""

    graph = nx.read_graphml(path)
    if not isinstance(graph, nx.MultiDiGraph):
        graph = nx.MultiDiGraph(graph)
    return graph


def decide_turn_model(graph: nx.MultiDiGraph) -> dict[str, object]:
    """Record that Stage 6 does not evaluate OSM turn restrictions.

    The dated pyrosm driving graph retains directed OSM arcs. Restriction
    relations are not present as graph attributes, so the evaluated topology
    allows any turn that exists as a pair of incoming and outgoing arcs.
    """

    attribute_names: set[str] = set()
    for key in graph.graph:
        lowered = str(key).lower()
        if "restriction" in lowered or lowered in {"except", "turn"}:
            attribute_names.add(str(key))
    sampled_edges = 0
    for _, _, _, data in graph.edges(keys=True, data=True):
        sampled_edges += 1
        for key in data:
            lowered = str(key).lower()
            if "restriction" in lowered or lowered in {"except", "turn:lanes"}:
                attribute_names.add(str(key))
        if sampled_edges >= 1 and not attribute_names:
            # Stage 3 GraphML keys are schema-uniform; one edge is enough when
            # no restriction attributes exist on the first edge.
            break
    return {
        "decision": TURN_MODEL_DECISION,
        "classification": "UNAVAILABLE",
        "restriction_attribute_names": sorted(attribute_names),
        "restriction_attribute_count": len(attribute_names),
        "evaluated_topology": (
            "Directed OSM arc graph from Stage 3. Node turns are unrestricted "
            "except where OSM oneway or a missing reverse arc already removes "
            "the movement."
        ),
        "claim_limit": (
            "This is not a Chennai turn-restriction model. Legal U-turn and "
            "signed-turn constraints were not imported from OSM relations."
        ),
    }


def build_quantized_weights(
    graph: nx.MultiDiGraph,
    *,
    policy: QuantizationPolicy | None = None,
) -> dict[str, object]:
    """Build a complete integer millisecond metric for the Stage 3 graph."""

    chosen = policy or QuantizationPolicy()
    weights: dict[EdgeId, int] = {}
    classifications: dict[EdgeId, str] = {}
    arc_ids: dict[EdgeId, str] = {}
    observed = scenario = 0
    max_arc_ms = 0
    min_speed = None
    for u, v, key, data in graph.edges(keys=True, data=True):
        edge: EdgeId = (u, v, key)
        length_m = _coerce_float(data.get("length"))
        if length_m is None or length_m <= 0:
            raise ValueError(f"Stage 6 requires a positive length on arc {edge!r}.")
        speed_kph = parse_explicit_osm_maxspeed_kph(data.get("maxspeed"))
        if speed_kph is None:
            speed_kph = _coerce_float(data.get("stage3_explicit_speed_kph"))
        if speed_kph is None or speed_kph <= 0:
            speed_kph = chosen.scenario_default_speed_kph
            classifications[edge] = "SCENARIO"
            scenario += 1
        else:
            classifications[edge] = "OBSERVED"
            observed += 1
        min_speed = speed_kph if min_speed is None else min(min_speed, speed_kph)
        quantized = quantize_travel_time_ms(length_m, speed_kph, chosen)
        weights[edge] = quantized
        max_arc_ms = max(max_arc_ms, quantized)
        arc_ids[edge] = str(data.get("stage3_arc_id") or f"{u}|{v}|{key}")
    lons: list[float] = []
    lats: list[float] = []
    for _, data in graph.nodes(data=True):
        lon = _coerce_float(data.get("x"))
        lat = _coerce_float(data.get("y"))
        if lon is None or lat is None:
            raise ValueError("Stage 6 requires numeric node coordinates.")
        lons.append(lon)
        lats.append(lat)
    diameter_m = bbox_diameter_m(min(lons), min(lats), max(lons), max(lats))
    overflow = geographic_overflow_bound_ms(
        diameter_m=diameter_m,
        min_speed_kph=float(min_speed),
        max_arc_ms=max_arc_ms,
        policy=chosen,
    )
    return {
        "weights": weights,
        "classifications": classifications,
        "arc_ids": arc_ids,
        "observed_speed_count": observed,
        "scenario_speed_count": scenario,
        "scenario_default_speed_kph": chosen.scenario_default_speed_kph,
        "min_speed_kph": float(min_speed),
        "max_arc_ms": max_arc_ms,
        "node_count": graph.number_of_nodes(),
        "arc_count": graph.number_of_edges(),
        "bbox_wgs84": [min(lons), min(lats), max(lons), max(lats)],
        "overflow": overflow,
        "quantization": {
            "unit": chosen.unit,
            "scale": chosen.scale,
            "rounding": chosen.rounding,
            "per_arc_error_bound_ms": chosen.per_arc_error_bound_ms,
            "longest_simple_path_error_bound_ms": path_quantization_error_bound_ms(
                max(0, graph.number_of_nodes() - 1),
                chosen,
            ),
            "classification_note": (
                "Millisecond rounding is a declared representation. Missing OSM "
                "maxspeed uses a labelled SCENARIO 30 km/h default matching Stage 5."
            ),
        },
    }


def osm_to_cch_maps(
    engine: RoutingKitCCHEngine,
    arc_ids: dict[EdgeId, str],
) -> dict[str, object]:
    """Exact OSM-to-CCH index maps for the engine's node and arc order."""

    nodes = [
        {"osm_id": str(node), "cch_index": index}
        for node, index in engine.node_to_index.items()
    ]
    arcs = [
        {
            "cch_index": index,
            "u": str(edge[0]),
            "v": str(edge[1]),
            "key": str(edge[2]),
            "stage3_arc_id": arc_ids[edge],
        }
        for index, edge in enumerate(engine.edge_ids)
    ]
    return {
        "node_count": len(nodes),
        "arc_count": len(arcs),
        "order_method": engine.order_method,
        "nodes": nodes,
        "arcs": arcs,
    }


def sample_od_pairs(
    nodes: Sequence[NodeId],
    count: int,
    *,
    seed: int = STAGE6_SEED,
) -> list[tuple[NodeId, NodeId]]:
    """Sample distinct origin-destination pairs with a fixed seed."""

    if count <= 0:
        raise ValueError("OD pair count must be positive.")
    unique_nodes = list(nodes)
    if len(unique_nodes) < 2:
        raise ValueError("Need at least two nodes to sample OD pairs.")
    rng = random.Random(seed)
    pairs: list[tuple[NodeId, NodeId]] = []
    seen: set[tuple[NodeId, NodeId]] = set()
    attempts = 0
    limit = max(count * 50, 1000)
    while len(pairs) < count and attempts < limit:
        attempts += 1
        source, target = rng.sample(unique_nodes, 2)
        pair = (source, target)
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    if len(pairs) < count:
        raise ValueError("Could not sample the requested number of distinct OD pairs.")
    return pairs


def compare_query(
    cch: RoutingKitCCHEngine,
    dijkstra: NetworkXDijkstraEngine,
    source: NodeId,
    target: NodeId,
    *,
    closed_edges: set[EdgeId] | None = None,
) -> dict[str, object]:
    """Compare one unpacked CCH query with the Dijkstra oracle."""

    cch_started = perf_counter_ns()
    cch_result = cch.query(source, target)
    cch_ns = perf_counter_ns() - cch_started
    dij_started = perf_counter_ns()
    dij_result = dijkstra.query(source, target)
    dij_ns = perf_counter_ns() - dij_started
    closed = closed_edges or set()
    cch_used_closed = False
    if cch_result.path is not None:
        cch_used_closed = any(edge in closed for edge in cch_result.path.edges)
    mismatch = (
        cch_result.status != dij_result.status
        or (
            cch_result.path is not None
            and dij_result.path is not None
            and cch_result.path.cost != dij_result.path.cost
        )
        or (cch_result.path is None) != (dij_result.path is None)
    )
    return {
        "source": str(source),
        "target": str(target),
        "cch_status": cch_result.status,
        "dijkstra_status": dij_result.status,
        "cch_cost_ms": None if cch_result.path is None else int(cch_result.path.cost),
        "dijkstra_cost_ms": None if dij_result.path is None else int(dij_result.path.cost),
        "cch_arc_count": 0 if cch_result.path is None else len(cch_result.path.edges),
        "cch_used_closed_edge": cch_used_closed,
        "cost_mismatch": mismatch,
        "cch_query_ns": cch_ns,
        "dijkstra_query_ns": dij_ns,
    }


def _mean_ns(samples: list[int]) -> float:
    return float(sum(samples) / len(samples)) if samples else 0.0


def _blocked_arc_ids(road_state_csv: Path, limit: int) -> list[str]:
    if not road_state_csv.is_file():
        return []
    import csv

    ids: list[str] = []
    with road_state_csv.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("state") != "BLOCKED":
                continue
            arc_id = row.get("arc_id")
            if arc_id:
                ids.append(arc_id)
            if len(ids) >= limit:
                break
    return ids


def collect_software_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0]}
    for package in ("networkx", "routingkit-cch"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "UNAVAILABLE"
    return versions


def evaluate_graph(
    graph: nx.MultiDiGraph,
    *,
    differential_query_count: int,
    cch_query_count: int,
    seed: int = STAGE6_SEED,
    closed_arc_ids: Sequence[str] = (),
    order_method: str = "inertial",
) -> dict[str, object]:
    """Run Stage 6 mapping, CCH customization, and Dijkstra comparison."""

    print("Stage 6: deciding turn model and building quantized metric", flush=True)
    turn_model = decide_turn_model(graph)
    metric_bundle = build_quantized_weights(graph)
    print(
        f"Stage 6: metric observed={metric_bundle['observed_speed_count']} "
        f"scenario={metric_bundle['scenario_speed_count']} "
        f"max_arc_ms={metric_bundle['max_arc_ms']}",
        flush=True,
    )
    weights: dict[EdgeId, int] = metric_bundle["weights"]
    arc_ids: dict[EdgeId, str] = metric_bundle["arc_ids"]
    overflow = metric_bundle["overflow"]
    max_finite_weight = int(overflow["bound_ms"])
    latitudes, longitudes = node_latitudes_longitudes(graph, tuple(graph.nodes))
    tails = []
    heads = []
    node_to_index = {node: index for index, node in enumerate(graph.nodes)}
    edge_ids = tuple((u, v, key) for u, v, key in graph.edges(keys=True))
    for u, v, _key in edge_ids:
        tails.append(node_to_index[u])
        heads.append(node_to_index[v])

    print(f"Stage 6: computing {order_method} contraction order", flush=True)
    order_started = perf_counter_ns()
    order = compute_contraction_order(
        node_count=graph.number_of_nodes(),
        tails=tails,
        heads=heads,
        method=order_method,
        latitudes=latitudes,
        longitudes=longitudes,
    )
    order_ns = perf_counter_ns() - order_started

    print("Stage 6: constructing CCH", flush=True)
    build_started = perf_counter_ns()
    cch = RoutingKitCCHEngine(
        graph,
        order_method=order_method,
        order=order,
        max_finite_weight=max_finite_weight,
        latitudes=latitudes,
        longitudes=longitudes,
    )
    build_ns = perf_counter_ns() - build_started
    snapshot = MetricSnapshot(
        topology_id=cch.topology_id,
        version=0,
        weights=MappingProxyType(weights),
    )
    print("Stage 6: customizing CCH metric", flush=True)
    customize_started = perf_counter_ns()
    cch.synchronize(snapshot)
    customize_ns = perf_counter_ns() - customize_started

    vector = [weights[edge] for edge in cch.edge_ids]
    reset_started = perf_counter_ns()
    cch.reset_metric_vector(vector)
    reset_ns = perf_counter_ns() - reset_started

    rng = random.Random(seed)
    partial_edges = [cch.edge_ids[index] for index in rng.sample(range(len(cch.edge_ids)), k=min(50, len(cch.edge_ids)))]
    partial = {edge: weights[edge] for edge in partial_edges}
    partial_started = perf_counter_ns()
    cch.apply_partial_updates(partial)
    partial_ns = perf_counter_ns() - partial_started

    dijkstra = NetworkXDijkstraEngine(graph)
    print("Stage 6: synchronizing Dijkstra oracle", flush=True)
    dijkstra.synchronize(
        MetricSnapshot(
            topology_id=dijkstra.topology_id,
            version=0,
            weights=MappingProxyType(weights),
        )
    )

    pairs = sample_od_pairs(cch.nodes, differential_query_count, seed=seed)
    print(
        f"Stage 6: Dijkstra differential on {differential_query_count} queries",
        flush=True,
    )
    differential = []
    for index, (source, target) in enumerate(pairs, start=1):
        differential.append(compare_query(cch, dijkstra, source, target))
        if index == 1 or index == differential_query_count or index % 4 == 0:
            print(f"Stage 6: differential {index}/{differential_query_count}", flush=True)
    mismatch_count = sum(1 for row in differential if row["cost_mismatch"])

    extra_pairs = sample_od_pairs(
        cch.nodes,
        cch_query_count,
        seed=seed + 1,
    )
    print(f"Stage 6: CCH-only query benchmark ({cch_query_count})", flush=True)
    cch_query_samples: list[int] = []
    for source, target in extra_pairs:
        started = perf_counter_ns()
        cch.query(source, target)
        cch_query_samples.append(perf_counter_ns() - started)

    id_to_edge = {arc_id: edge for edge, arc_id in arc_ids.items()}
    closed_edges = [id_to_edge[arc_id] for arc_id in closed_arc_ids if arc_id in id_to_edge]
    closure_report: dict[str, object]
    if closed_edges:
        sentinel = max_finite_weight
        closed_set = set(closed_edges)
        replacements = {edge: sentinel for edge in closed_edges}
        closed_weights = dict(weights)
        closed_weights.update(replacements)
        cch.apply_partial_updates(replacements)
        dijkstra.synchronize(
            MetricSnapshot(
                topology_id=dijkstra.topology_id,
                version=1,
                weights=MappingProxyType(closed_weights),
            )
        )
        closure_rows = [
            compare_query(cch, dijkstra, source, target, closed_edges=closed_set)
            for source, target in pairs[: min(8, len(pairs))]
        ]
        cch.reset_metric_vector(vector)
        dijkstra.synchronize(
            MetricSnapshot(
                topology_id=dijkstra.topology_id,
                version=2,
                weights=MappingProxyType(weights),
            )
        )
        recovery_rows = [
            compare_query(cch, dijkstra, source, target)
            for source, target in pairs[: min(4, len(pairs))]
        ]
        closure_report = {
            "representation": "finite_sentinel",
            "sentinel_ms": sentinel,
            "closed_arc_count": len(closed_edges),
            "closed_arc_class": "SCENARIO historical-hotspot overlay, not observed closures",
            "queries": closure_rows,
            "mismatch_count": sum(1 for row in closure_rows if row["cost_mismatch"]),
            "paths_using_closed_edge": sum(
                1 for row in closure_rows if row["cch_used_closed_edge"]
            ),
            "recovery_mismatch_count": sum(1 for row in recovery_rows if row["cost_mismatch"]),
            "overflow_note": (
                "Closed arcs use the declared geographic bound as a finite "
                "weight. Dijkstra and CCH receive the same integer metric."
            ),
        }
    else:
        closure_report = {
            "representation": "finite_sentinel",
            "closed_arc_count": 0,
            "note": "No matching Stage 4 BLOCKED arc IDs were supplied.",
        }

    rss_kb = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if resource is not None
        else None
    )
    mean_cch_ns = _mean_ns(cch_query_samples)
    mean_diff_cch_ns = _mean_ns([int(row["cch_query_ns"]) for row in differential])
    mean_dij_ns = _mean_ns([int(row["dijkstra_query_ns"]) for row in differential])
    query_advantage_ns = mean_dij_ns - mean_cch_ns
    if query_advantage_ns > 0:
        break_even_queries = customize_ns / query_advantage_ns
        engine_decision = (
            "CCH is faster per query than Dijkstra on this represented metric. "
            "Retain CCH for repeated queries after one customization."
        )
    else:
        break_even_queries = None
        engine_decision = (
            "CCH was not faster per query than Dijkstra on this measured "
            "workload. Dijkstra remains the oracle; ALT is still unimplemented."
        )
    if mismatch_count:
        engine_decision = (
            "Do not retain CCH for publication queries: unpacked costs did not "
            "match Dijkstra on the declared metric."
        )

    maps = osm_to_cch_maps(cch, arc_ids)
    return {
        "turn_model": turn_model,
        "metric": {
            "observed_speed_count": metric_bundle["observed_speed_count"],
            "scenario_speed_count": metric_bundle["scenario_speed_count"],
            "scenario_default_speed_kph": metric_bundle["scenario_default_speed_kph"],
            "min_speed_kph": metric_bundle["min_speed_kph"],
            "max_arc_ms": metric_bundle["max_arc_ms"],
            "bbox_wgs84": metric_bundle["bbox_wgs84"],
            "overflow": overflow,
            "quantization": metric_bundle["quantization"],
            "unit": QUANTIZATION_UNIT,
            "detour_factor": GEOGRAPHIC_DETOUR_FACTOR,
        },
        "maps_summary": {
            "node_count": maps["node_count"],
            "arc_count": maps["arc_count"],
            "order_method": maps["order_method"],
            "sample_nodes": maps["nodes"][:5],
            "sample_arcs": maps["arcs"][:5],
        },
        "maps": maps,
        "benchmark": {
            "order_method": order_method,
            "order_ns": order_ns,
            "cch_construct_ns": build_ns,
            "full_customize_ns": customize_ns,
            "metric_reset_ns": reset_ns,
            "partial_update_arc_count": len(partial),
            "partial_update_ns": partial_ns,
            "differential_query_count": differential_query_count,
            "cch_query_count": cch_query_count,
            "mean_cch_query_ns": mean_cch_ns,
            "mean_differential_cch_query_ns": mean_diff_cch_ns,
            "mean_dijkstra_query_ns": mean_dij_ns,
            "maxrss_kb": rss_kb,
            "break_even_queries_vs_dijkstra": break_even_queries,
        },
        "differential": {
            "seed": seed,
            "mismatch_count": mismatch_count,
            "queries": differential,
        },
        "closure": closure_report,
        "engine_selection": engine_decision,
        "topology_id": cch.topology_id,
        "max_finite_weight": max_finite_weight,
        "routingkit_infinity": ROUTINGKIT_INFINITY,
    }


def run_stage6_cch(
    *,
    differential_query_count: int = 24,
    cch_query_count: int = 80,
    closed_arc_limit: int = 20,
) -> Stage6Result:
    """Map the Stage 3 graph into CCH and write the Stage 6 evidence package."""

    paths = get_project_paths()
    graphml = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    if not graphml.is_file():
        raise FileNotFoundError("Stage 6 requires the Stage 3 GraphML road graph.")
    print(f"Stage 6: loading {graphml}", flush=True)
    graph = load_stage3_graphml(graphml)
    print(
        f"Stage 6: loaded {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} arcs",
        flush=True,
    )
    road_states = paths.processed_road_state / "stage4_road_states.csv"
    closed_ids = _blocked_arc_ids(road_states, closed_arc_limit)
    evaluation = evaluate_graph(
        graph,
        differential_query_count=differential_query_count,
        cch_query_count=cch_query_count,
        seed=STAGE6_SEED,
        closed_arc_ids=closed_ids,
        order_method="inertial",
    )
    cch_dir = paths.processed_data / "cch"
    cch_dir.mkdir(parents=True, exist_ok=True)
    print("Stage 6: writing OSM-to-CCH maps and evidence", flush=True)
    maps_path = cch_dir / "stage6_osm_to_cch_maps.json"
    maps_path.write_text(
        json.dumps(evaluation.pop("maps"), separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    mismatch_count = int(evaluation["differential"]["mismatch_count"])
    closure_mismatch = int(evaluation["closure"].get("mismatch_count", 0) or 0)
    recovery_mismatch = int(evaluation["closure"].get("recovery_mismatch_count", 0) or 0)
    if mismatch_count or closure_mismatch or recovery_mismatch:
        decision = "FAIL"
    else:
        decision = "PASS WITH LIMITATIONS"
    claim_limit = (
        "Stage 6 validates inertial CCH against Dijkstra on a labelled "
        "integer millisecond metric for the Stage 3 graph. Missing OSM "
        "maxspeed uses SCENARIO 30 km/h. Turn restrictions are not modelled. "
        "BLOCKED sentinels are Stage 4 scenario overlays, not observed 2015 "
        "closures. Timings are one-machine measurements, not traffic outcomes."
    )
    next_gate = (
        "Stage 7 stable projected-load rerouting, only after this Stage 6 "
        "differential test is not FAIL."
    )
    evidence_path = paths.root / "docs" / "evidence" / "STAGE6_CCH_RESULTS.json"
    payload = {
        "stage": 6,
        "decision": decision,
        "seed": STAGE6_SEED,
        "claim_limit": claim_limit,
        "next_gate": next_gate,
        "software_versions": collect_software_versions(),
        "graphml": _repository_relative(graphml, paths.root),
        "maps_path": _repository_relative(maps_path, paths.root),
        "maps_sha256": _sha256_file(maps_path),
        **evaluation,
    }
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return Stage6Result(
        evidence_path=_repository_relative(evidence_path, paths.root),
        decision=decision,
        turn_model=str(evaluation["turn_model"]["decision"]),
        order_method="inertial",
        differential_mismatch_count=mismatch_count,
        claim_limit=claim_limit,
        next_gate=next_gate,
    )
