"""Run the paired Stage 9 emergency-policy scenario."""

import json

from chennai_routing.stage9_emergency import run_stage9_experiment


if __name__ == "__main__":
    print(json.dumps(run_stage9_experiment(), indent=2, sort_keys=True))
