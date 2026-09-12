from pathlib import Path

import pytest

from chennai_routing.simulation.sumo import (
    count_trip_elements,
    write_scenario_vehicle_types,
    write_sumo_config,
    write_traffic_feasibility_report,
)


def test_traffic_feasibility_is_labelled_synthetic(tmp_path: Path) -> None:
    report = write_traffic_feasibility_report(tmp_path / "feasibility.json")
    assert report.demand_class == "SYNTHETIC"
    assert report.calibration_class == "SYNTHETIC"
    assert report.observed_od_matrix == "UNAVAILABLE"
    assert "not traffic counts" in report.notes


def test_vehicle_types_are_scenario_labels(tmp_path: Path) -> None:
    path = write_scenario_vehicle_types(tmp_path / "types.add.xml")
    text = path.read_text(encoding="utf-8")
    assert "SCENARIO labels only" in text
    assert 'id="emergency"' in text


def test_sumo_config_embeds_seed(tmp_path: Path) -> None:
    config = write_sumo_config(
        tmp_path / "run.sumocfg",
        net_file=tmp_path / "net.xml",
        route_file=tmp_path / "trips.xml",
        additional_files=[tmp_path / "types.add.xml"],
        seed=8597,
        end_seconds=120,
    )
    text = config.read_text(encoding="utf-8")
    assert '<seed value="8597"/>' in text
    assert '<end value="120"/>' in text


def test_trip_counter_reads_trip_elements(tmp_path: Path) -> None:
    trips = tmp_path / "trips.xml"
    trips.write_text(
        """<?xml version="1.0"?>
<routes>
  <trip id="0" depart="0" from="a" to="b"/>
  <trip id="1" depart="5" from="c" to="d"/>
</routes>
""",
        encoding="utf-8",
    )
    assert count_trip_elements(trips) == 2


def test_plain_sumo_writer_labels_missing_speed_as_scenario(tmp_path: Path) -> None:
    import networkx as nx

    from chennai_routing.simulation.sumo import write_plain_sumo_from_graphml

    graph = nx.DiGraph()
    graph.add_node("1", x="80.27", y="13.08")
    graph.add_node("2", x="80.28", y="13.08")
    graph.add_edge("1", "2", maxspeed="50", lanes="2", stage3_arc_id="arc-obs")
    graph.add_edge("2", "1", maxspeed="nan", lanes="nan", stage3_arc_id="arc-scen")
    graphml = tmp_path / "g.graphml"
    nx.write_graphml(graph, graphml)
    counts = write_plain_sumo_from_graphml(
        graphml,
        tmp_path / "nodes.xml",
        tmp_path / "edges.xml",
    )
    assert counts["observed_speed_count"] == 1
    assert counts["scenario_speed_count"] == 1
    edges = (tmp_path / "edges.xml").read_text(encoding="utf-8")
    assert 'id="arc-obs"' in edges
    assert 'numLanes="2"' in edges


def test_netconvert_missing_binary_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    from chennai_routing.simulation import sumo as sumo_mod

    monkeypatch.setattr(sumo_mod.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="netconvert is required"):
        sumo_mod.require_netconvert()
