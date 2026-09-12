"""Run the seeded Stage 7 projected-load experiment."""

import json

from chennai_routing.stage7_reservations import run_stage7_experiment


if __name__ == "__main__":
    print(json.dumps(run_stage7_experiment(), indent=2, sort_keys=True))
