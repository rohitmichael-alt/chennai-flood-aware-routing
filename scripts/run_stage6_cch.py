"""Map the Stage 3 graph into CCH and compare unpacked paths with Dijkstra."""

from __future__ import annotations

import json

from chennai_routing.stage6_cch import run_stage6_cch


def main() -> None:
    result = run_stage6_cch()
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
