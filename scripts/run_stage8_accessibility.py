"""Run Stage 8 facility and WorldPop accessibility evaluation."""

from __future__ import annotations

import json

from chennai_routing.stage8_accessibility import run_stage8_accessibility


if __name__ == "__main__":
    print(json.dumps(run_stage8_accessibility(), indent=2, sort_keys=True))
