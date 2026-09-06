"""Run reproducible certificate-gated synchronization experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from chennai_routing.config import get_project_paths
from chennai_routing.evaluation.experiments import (
    LazySyncExperimentConfig,
    run_certified_lazy_experiment,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare certificate-gated metric synchronization with eager "
            "repeated-snapshot NetworkX Dijkstra."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("increases_only", "mixed", "both"),
        default="both",
    )
    parser.add_argument("--seed", type=int, default=8597)
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--extra-edges", type=int, default=250)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--updates-per-epoch", type=int, default=4)
    parser.add_argument("--queries-per-epoch", type=int, default=25)
    parser.add_argument("--epsilon-percent", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    modes = (
        ("increases_only", "mixed")
        if args.mode == "both"
        else (args.mode,)
    )
    output_dir = get_project_paths().output_tables
    failed = False
    for mode in modes:
        config = LazySyncExperimentConfig(
            seed=args.seed,
            node_count=args.nodes,
            extra_edge_count=args.extra_edges,
            epochs=args.epochs,
            updates_per_epoch=args.updates_per_epoch,
            queries_per_epoch=args.queries_per_epoch,
            update_mode=mode,
            epsilon_numerator=args.epsilon_percent,
            epsilon_denominator=100,
        )
        summary = run_certified_lazy_experiment(config, output_dir)
        print(json.dumps(asdict(summary), indent=2, sort_keys=True))
        failed = failed or summary.certificate_violation_count != 0
        failed = failed or summary.exact_after_refresh_mismatch_count != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
