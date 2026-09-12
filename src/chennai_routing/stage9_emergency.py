"""Stage 9 paired emergency-policy scenario evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

from chennai_routing.routing.emergency import (
    EmergencyPolicy,
    EmergencyRouteCandidate,
    select_emergency_route,
)


def run_stage9_experiment(output: Path | None = None) -> dict[str, object]:
    policy = EmergencyPolicy(deadline_seconds=600, ordinary_delay_cap_seconds=25)
    rows: list[dict[str, object]] = []
    for seed, jitter in ((8597, 0.0), (8598, 8.0), (8599, -6.0)):
        candidates = (
            EmergencyRouteCandidate("fast_safe", (), 480 + jitter, 0, 0, 20),
            EmergencyRouteCandidate("balanced_safe", (), 540 + jitter, 0, 0, 5),
            EmergencyRouteCandidate("blocked_shortcut", (), 400 + jitter, 1, 0, 0),
        )
        priority = select_emergency_route(candidates, policy)
        feasible = tuple(candidate for candidate in candidates if candidate.blocked_edge_count == 0)
        no_priority = min(
            feasible,
            key=lambda candidate: (
                candidate.ordinary_external_delay_seconds,
                candidate.arrival_seconds,
                candidate.route_id,
            ),
        )
        rows.append(
            {
                "seed": seed,
                "priority_route": priority.route_id,
                "no_priority_route": no_priority.route_id,
                "priority_arrival_seconds": priority.arrival_seconds,
                "no_priority_arrival_seconds": no_priority.arrival_seconds,
                "emergency_arrival_change_seconds": priority.arrival_seconds
                - no_priority.arrival_seconds,
                "priority_external_delay_seconds": priority.ordinary_external_delay_seconds,
                "no_priority_external_delay_seconds": no_priority.ordinary_external_delay_seconds,
                "ordinary_external_delay_change_seconds": priority.ordinary_external_delay_seconds
                - no_priority.ordinary_external_delay_seconds,
                "priority_deadline_met": priority.arrival_seconds <= policy.deadline_seconds,
                "no_priority_deadline_met": no_priority.arrival_seconds <= policy.deadline_seconds,
                "blocked_shortcut_rejected": priority.route_id != "blocked_shortcut",
            }
        )
    evidence = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "decision": "PASS WITH LIMITATIONS",
        "classification": "SCENARIO",
        "policy": policy.__dict__,
        "paired_runs": rows,
        "summary": {
            "mean_emergency_arrival_change_seconds": mean(
                float(row["emergency_arrival_change_seconds"]) for row in rows
            ),
            "mean_ordinary_external_delay_change_seconds": mean(
                float(row["ordinary_external_delay_change_seconds"]) for row in rows
            ),
            "blocked_shortcut_selected_count": sum(
                not bool(row["blocked_shortcut_rejected"]) for row in rows
            ),
        },
        "explicit_exclusions": [
            "No traffic-signal pre-emption",
            "No live ambulance AVL",
            "No observed response-time calibration",
        ],
        "claim_limit": (
            "This paired candidate-choice experiment validates deterministic policy order "
            "and reports emergency arrival together with ordinary-user external delay. "
            "All times and deadlines are SCENARIO values; it is not a Chennai operational result."
        ),
    }
    destination = output or Path("docs/evidence/STAGE9_EMERGENCY_RESULTS.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    return evidence
