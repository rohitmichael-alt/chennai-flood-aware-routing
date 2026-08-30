"""Run the Stage 1 Chennai flood-aware routing proof of concept."""

from __future__ import annotations

from chennai_routing.stage1_poc import run_stage1_poc


def main() -> None:
    result = run_stage1_poc()
    print("Stage 1 proof of concept completed.")
    print(f"Graph: {result.graph_path}")
    print(f"Flood KML: {result.flood_kml_path}")
    print(f"Affected roads CSV: {result.affected_roads_csv}")
    print(f"Route summary CSV: {result.route_summary_csv}")
    print(f"Map: {result.map_path}")
    print(f"Before route nodes: {result.before_route}")
    print(f"After route nodes: {result.after_route}")
    print(f"Affected edge: {result.affected_edge}")


if __name__ == "__main__":
    main()
