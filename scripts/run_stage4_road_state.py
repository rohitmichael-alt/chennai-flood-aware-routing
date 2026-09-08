"""Acquire Stage 4 flood/rainfall/elevation evidence and explained road states."""

from __future__ import annotations

import json

from chennai_routing.stage4_road_state import run_stage4_road_state


def main() -> None:
    result = run_stage4_road_state()
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
