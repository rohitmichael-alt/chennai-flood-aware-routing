"""Record or verify deterministic Stage 3 topology/arc-ID digests."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from chennai_routing.config import get_project_paths

NS = "{http://graphml.graphdrawing.org/xmlns}"


def digest_graphml(path: Path) -> dict[str, object]:
    keys: dict[str, str] = {}
    nodes: list[str] = []
    arcs: list[str] = []
    for _event, elem in ET.iterparse(path, events=("end",)):
        tag = elem.tag.removeprefix(NS)
        if tag == "key":
            keys[str(elem.get("id"))] = str(elem.get("attr.name"))
        elif tag == "node":
            nodes.append(str(elem.get("id")))
            elem.clear()
        elif tag == "edge":
            values = {keys.get(str(child.get("key")), ""): child.text for child in elem}
            arcs.append(str(values["stage3_arc_id"]))
            elem.clear()
    def sha(values: list[str]) -> str:
        return hashlib.sha256("\n".join(sorted(values)).encode()).hexdigest()
    return {
        "node_count": len(nodes),
        "arc_count": len(arcs),
        "sorted_node_id_sha256": sha(nodes),
        "sorted_stage3_arc_id_sha256": sha(arcs),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("record", "verify"))
    args = parser.parse_args()
    paths = get_project_paths()
    graphml = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    baseline_path = paths.root / ".tools" / "stage3_reproducibility_baseline.json"
    current = digest_graphml(graphml)
    if args.mode == "record":
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(current, indent=2, sort_keys=True))
        return 0
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    match = current == baseline
    evidence_path = paths.root / "docs" / "evidence" / "STAGE3_GRAPH_RESULTS.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["reproducibility_check"] = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "independent_build_count": 2,
        "baseline": baseline,
        "second_build": current,
        "topology_and_arc_id_digests_match": match,
    }
    if not match:
        evidence["decision"] = "FAIL"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence["reproducibility_check"], indent=2, sort_keys=True))
    return 0 if match else 1


if __name__ == "__main__":
    raise SystemExit(main())
