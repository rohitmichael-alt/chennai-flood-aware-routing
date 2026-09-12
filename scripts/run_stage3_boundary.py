"""Acquire and validate the Greater Chennai Corporation 2022 study boundary."""

from __future__ import annotations

import json

from chennai_routing.stage3_graph import run_stage3_boundary


def main() -> None:
    result = run_stage3_boundary()
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
