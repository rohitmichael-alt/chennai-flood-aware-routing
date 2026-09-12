"""Import the Stage 3 OSM extract into SUMO and write synthetic demand."""

from __future__ import annotations

import json

from chennai_routing.stage5_sumo import run_stage5_sumo


def main() -> None:
    result = run_stage5_sumo()
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
