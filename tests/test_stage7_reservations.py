from chennai_routing.stage7_reservations import run_assignment


def test_reservations_reduce_synthetic_herding_at_full_compliance() -> None:
    independent = run_assignment(vehicle_count=40, compliance=0.0, seed=8597)
    reserved = run_assignment(vehicle_count=40, compliance=1.0, seed=8597)
    assert reserved["maximum_volume_capacity_ratio"] < independent["maximum_volume_capacity_ratio"]
    assert reserved["mean_realized_bpr_seconds"] < independent["mean_realized_bpr_seconds"]
