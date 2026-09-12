from chennai_routing.stage9_emergency import run_stage9_experiment


def test_stage9_reports_benefit_and_external_delay(tmp_path) -> None:
    evidence = run_stage9_experiment(tmp_path / "stage9.json")
    assert evidence["summary"]["mean_emergency_arrival_change_seconds"] < 0
    assert evidence["summary"]["mean_ordinary_external_delay_change_seconds"] > 0
    assert evidence["summary"]["blocked_shortcut_selected_count"] == 0
