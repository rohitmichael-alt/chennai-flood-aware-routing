"""Synthesize the generated Stage 1–9 evidence into Stage 10."""

from __future__ import annotations

import json

from chennai_routing.stage10_evaluation import run_stage10_evaluation


if __name__ == "__main__":
    print(json.dumps(run_stage10_evaluation(), indent=2, sort_keys=True))
