"""Stage 5 SUMO import and synthetic-demand evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from chennai_routing.config import get_project_paths
from chennai_routing.simulation.sumo import (
    SYNTHETIC_SEED,
    VEHICLE_TYPE_CLASS,
    convert_graphml_to_sumo_net,
    count_trip_elements,
    write_scenario_vehicle_types,
    write_sumo_config,
    write_synthetic_trips,
    write_traffic_feasibility_report,
)


@dataclass(frozen=True)
class Stage5Result:
    """Paths and labels for the Stage 5 SUMO evidence package."""

    evidence_path: str
    feasibility_path: str
    net_path: str
    trips_path: str
    config_path: str
    decision: str
    demand_class: str
    calibration_class: str
    claim_limit: str


def _repository_relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def run_stage5_sumo() -> Stage5Result:
    """Import the Stage 3 OSM extract into SUMO and write synthetic demand."""

    paths = get_project_paths()
    sumo_dir = paths.processed_data / "sumo"
    sumo_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = paths.root / "docs" / "evidence"

    feasibility_path = evidence_dir / "STAGE5_TRAFFIC_FEASIBILITY.json"
    feasibility = write_traffic_feasibility_report(feasibility_path)

    osm_pbf = paths.raw_osm / "chennai_gcc_2022_india-260901.osm.pbf"
    graphml = paths.processed_roads / "stage3_chennai_gcc_2022.graphml"
    if not graphml.is_file():
        raise FileNotFoundError("Stage 5 requires the Stage 3 GraphML road graph.")
    osm_netconvert_status = (
        "ARCHIVED FAILURE: Ubuntu SUMO 1.18.0 netconvert aborted on the GCC-clipped "
        "OSM extract with RTree/junction-angle assertions. The reproducible current "
        "path imported the Stage 3 GraphML as plain SUMO node/edge files with "
        "portable Eclipse SUMO netconvert 1.27.1."
    )
    if osm_pbf.is_file():
        failure_note = evidence_dir / "STAGE5_OSM_NETCONVERT_FAILURE.txt"
        failure_note.write_text(osm_netconvert_status + "\n", encoding="utf-8")
    net_path = sumo_dir / "chennai_gcc_2022.net.xml"
    _net, conversion = convert_graphml_to_sumo_net(
        graphml,
        net_path,
        osm_netconvert_status=osm_netconvert_status,
    )

    types_path = write_scenario_vehicle_types(sumo_dir / "scenario_vtypes.add.xml")
    trips_path = write_synthetic_trips(
        net_path,
        sumo_dir / "synthetic_trips.trips.xml",
        seed=SYNTHETIC_SEED,
        period_seconds=5.0,
        end_seconds=300,
    )
    config_path = write_sumo_config(
        sumo_dir / "synthetic_smoke.sumocfg",
        net_file=net_path,
        route_file=trips_path,
        additional_files=[types_path],
        seed=SYNTHETIC_SEED,
        end_seconds=300,
    )

    claim_limit = (
        "Stage 5 imported the Stage 3 graph into SUMO with portable netconvert "
        "1.27.1; a prior direct-OSM SUMO 1.18 attempt is archived as failed. "
        "Demand and calibration classes are SYNTHETIC. "
        "Most free-flow speeds and lanes are labelled SCENARIO defaults, not "
        "observed Chennai values. SUMO output is simulated traffic."
    )
    evidence_path = evidence_dir / "STAGE5_SUMO_RESULTS.json"
    payload = {
        "stage": 5,
        "decision": "PASS WITH LIMITATIONS",
        "demand_class": "SYNTHETIC",
        "calibration_class": "SYNTHETIC",
        "vehicle_type_class": VEHICLE_TYPE_CLASS,
        "seed": SYNTHETIC_SEED,
        "synthetic_trip_count": count_trip_elements(trips_path),
        "claim_limit": claim_limit,
        "feasibility": asdict(feasibility),
        "conversion": asdict(conversion),
        "artifacts": {
            "feasibility": _repository_relative(feasibility_path, paths.root),
            "net": _repository_relative(net_path, paths.root),
            "trips": _repository_relative(trips_path, paths.root),
            "config": _repository_relative(config_path, paths.root),
            "vehicle_types": _repository_relative(types_path, paths.root),
        },
    }
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return Stage5Result(
        evidence_path=_repository_relative(evidence_path, paths.root),
        feasibility_path=_repository_relative(feasibility_path, paths.root),
        net_path=_repository_relative(net_path, paths.root),
        trips_path=_repository_relative(trips_path, paths.root),
        config_path=_repository_relative(config_path, paths.root),
        decision="PASS WITH LIMITATIONS",
        demand_class="SYNTHETIC",
        calibration_class="SYNTHETIC",
        claim_limit=claim_limit,
    )
