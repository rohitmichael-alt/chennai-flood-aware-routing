"""Rerun Stage 1 on a documented extract of the dated Stage 3 graph."""

from __future__ import annotations

import json

from chennai_routing.stage1_publication import run_stage1_publication


if __name__ == "__main__":
    print(json.dumps(run_stage1_publication(), indent=2, sort_keys=True))
