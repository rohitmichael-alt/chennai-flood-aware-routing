"""Regenerate the committed certificate experiment evidence manifest."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime

from chennai_routing.config import get_project_paths
from chennai_routing.evaluation.experiments import (
    LazySyncExperimentConfig,
    run_certified_lazy_experiment,
)


def main() -> int:
    paths = get_project_paths()
    main_results = []
    sensitivity_results = []
    failed = False

    for engine in ("networkx", "cch"):
        for mode in ("increases_only", "mixed"):
            summary = run_certified_lazy_experiment(
                LazySyncExperimentConfig(
                    seed=8597,
                    node_count=200,
                    extra_edge_count=600,
                    epochs=100,
                    updates_per_epoch=5,
                    queries_per_epoch=50,
                    update_mode=mode,
                    engine=engine,
                    epsilon_numerator=5,
                    epsilon_denominator=100,
                ),
                paths.output_tables,
            )
            result = asdict(summary)
            main_results.append(result)
            failed = failed or any(
                (
                    summary.certificate_violation_count,
                    summary.exact_after_refresh_mismatch_count,
                    summary.engine_oracle_mismatch_count,
                )
            )

    for mode in ("increases_only", "mixed"):
        for epsilon in (0, 1, 5, 10):
            summary = run_certified_lazy_experiment(
                LazySyncExperimentConfig(
                    seed=8597,
                    node_count=200,
                    extra_edge_count=600,
                    epochs=50,
                    updates_per_epoch=5,
                    queries_per_epoch=50,
                    update_mode=mode,
                    engine="cch",
                    epsilon_numerator=epsilon,
                    epsilon_denominator=100,
                ),
                paths.output_tables,
            )
            result = asdict(summary)
            sensitivity_results.append(result)
            failed = failed or any(
                (
                    summary.certificate_violation_count,
                    summary.exact_after_refresh_mismatch_count,
                    summary.engine_oracle_mismatch_count,
                )
            )

    manifest = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "qualification": (
            "Synthetic fixed-topology evidence. Timings are single-run "
            "wall-clock measurements and do not establish Chennai outcomes."
        ),
        "main_results": main_results,
        "cch_epsilon_sensitivity": sensitivity_results,
    }
    evidence_path = (
        paths.root
        / "docs"
        / "evidence"
        / "CERTIFIED_LAZY_SYNC_RESULTS.json"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(evidence_path)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
