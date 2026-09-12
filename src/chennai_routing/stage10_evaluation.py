"""Stage 10 evidence synthesis without inventing unexecuted experiments."""

from __future__ import annotations

import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

from chennai_routing.config import get_project_paths


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mean_ci95(values: list[float]) -> dict[str, object]:
    mean = statistics.fmean(values)
    if len(values) < 2:
        return {"n": len(values), "mean": mean, "ci95": None}
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return {"n": len(values), "mean": mean, "ci95": [mean - half, mean + half]}


def run_stage10_evaluation() -> dict[str, object]:
    paths = get_project_paths()
    evidence_dir = paths.root / "docs" / "evidence"
    sources = {
        "stage1": "STAGE1_PUBLICATION_RESULTS.json",
        "stage2": "CERTIFIED_LAZY_SYNC_RESULTS.json",
        "stage3": "STAGE3_GRAPH_RESULTS.json",
        "stage4": "STAGE4_ROAD_STATE_RESULTS.json",
        "stage5": "STAGE5_SUMO_RESULTS.json",
        "stage6": "STAGE6_CCH_RESULTS.json",
        "stage7": "STAGE7_RESERVATION_RESULTS.json",
        "stage8": "STAGE8_ACCESSIBILITY_RESULTS.json",
        "stage9": "STAGE9_EMERGENCY_RESULTS.json",
    }
    loaded = {name: _load(evidence_dir / filename) for name, filename in sources.items()}
    stage7_runs = loaded["stage7"]["runs"]
    compliance_statistics = {}
    for compliance in (0.0, 0.25, 0.5, 0.75, 1.0):
        rows = [row for row in stage7_runs if float(row["compliance"]) == compliance]
        compliance_statistics[str(compliance)] = {
            "mean_realized_bpr_seconds": _mean_ci95(
                [float(row["mean_realized_bpr_seconds"]) for row in rows]
            ),
            "maximum_volume_capacity_ratio": _mean_ci95(
                [float(row["maximum_volume_capacity_ratio"]) for row in rows]
            ),
        }
    stage9_runs = loaded["stage9"]["paired_runs"]
    evidence = {
        "stage": 10,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision": "PARTIAL — PUBLICATION PACKAGE WITH EXPLICIT EXPERIMENT GAPS",
        "source_evidence": sources,
        "evidence_gate_decisions": {
            name: value.get("decision", "PRELIMINARY SYNTHETIC EVIDENCE")
            for name, value in loaded.items()
        },
        "baseline_matrix": {
            "route_once_dijkstra": "EXECUTED: dated Stage 1 route-change demonstration",
            "eager_repeated_dijkstra": "EXECUTED: Stage 2 synthetic fixed-topology sweep",
            "eager_cch": "EXECUTED: Stage 2 synthetic sweep and Stage 6 city metric validation",
            "certificate_gated_cch": "EXECUTED: Stage 2 synthetic sweep; city policy outcome not executed",
            "sumo_periodic": "NOT EXECUTED",
            "independent_assignment": "EXECUTED only on the Stage 7 four-node scenario",
            "projected_load_assignment": "EXECUTED only on the Stage 7 four-node scenario",
            "alt": "NOT IMPLEMENTED; excluded",
        },
        "scenario_matrix": {
            "dry_off_peak": "NOT EXECUTED in SUMO",
            "dry_peak": "NOT EXECUTED in SUMO",
            "flood_only": "EXECUTED as historical-evidence-conditioned SCENARIO overlay",
            "incident_only": "NOT EXECUTED citywide",
            "compound_flood_incident_peak": "NOT EXECUTED",
            "false_positive_delayed_evidence": "METHOD/UNIT TESTS ONLY; no city outcome",
            "recovery_decrease": "EXECUTED as Stage 6 routing-engine differential",
            "emergency": "EXECUTED on a paired SCENARIO candidate set",
            "compliance": "EXECUTED on the Stage 7 four-node SCENARIO network",
        },
        "ablation_matrix": {
            "certificate_on_off": "EXECUTED Stage 2 synthetic",
            "cch_vs_dijkstra_same_policy": "EXECUTED Stage 2 and Stage 6; zero cost mismatches",
            "stability_on_off": "NOT EXECUTED as a matched outcome ablation",
            "reservations_on_off": "EXECUTED Stage 7 four-node SCENARIO",
            "emergency_priority_on_off": "EXECUTED Stage 9 paired SCENARIO",
            "population_weighting_on_off": "NOT EXECUTED as a matched ablation",
        },
        "statistics": {
            "compliance_three_seed_normal_approximation_ci95": compliance_statistics,
            "emergency_arrival_change_seconds": _mean_ci95(
                [float(row["emergency_arrival_change_seconds"]) for row in stage9_runs]
            ),
            "ordinary_external_delay_change_seconds": _mean_ci95(
                [float(row["ordinary_external_delay_change_seconds"]) for row in stage9_runs]
            ),
            "qualification": "Three identical deterministic-seed outcomes yield zero-width normal-approximation intervals; this is not evidence of real-world variance.",
        },
        "key_results": {
            "stage3_node_count": loaded["stage3"]["audit"]["node_count"],
            "stage3_arc_count": loaded["stage3"]["audit"]["arc_count"],
            "stage3_reproducible_ids": loaded["stage3"]["reproducibility_check"]["topology_and_arc_id_digests_match"],
            "stage6_differential_mismatches": loaded["stage6"]["differential"]["mismatch_count"],
            "stage8_represented_population": loaded["stage8"]["population_provenance"]["represented_population"],
            "stage8_scenario_disconnected_population": loaded["stage8"]["stage4_blocked_overlay"]["accessibility"]["fire"]["disconnected_population"],
        },
        "negative_results": [
            "At 25% and 50% compliance, the Stage 7 scenario showed no mean travel-time benefit over 0% compliance.",
            "A direct OSM-to-SUMO attempt with SUMO 1.18 failed; the successful reproducible path used Stage 3 GraphML plain node/edge import with netconvert 1.27.1.",
            "The relief-centre PDF was excluded because coordinates were not independently verified.",
            "Matched citywide SUMO scenarios, stability ablation, and population-weighting ablation remain unexecuted.",
        ],
        "positioning": (
            "The defensible contribution is integration and evaluation of a Chennai-oriented compound-disruption framework. "
            "The certificate is an established bounded-cost CCH refresh gate, not a new shortest-path algorithm."
        ),
        "claim_limit": (
            "This evidence package combines a dated Chennai topology and historical/modelled public data with synthetic traffic, "
            "reservation, and emergency scenarios. It is not a calibrated 2015 flood reconstruction, live routing system, "
            "operational emergency policy, or complete execution of every planned Stage 10 comparator."
        ),
    }
    output = evidence_dir / "STAGE10_EVALUATION_RESULTS.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence
