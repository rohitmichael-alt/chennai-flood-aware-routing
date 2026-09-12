import networkx as nx

from chennai_routing.routing.emergency import (
    EmergencyPolicy,
    EmergencyRouteCandidate,
    select_emergency_route,
)
from chennai_routing.routing.engine import EnginePath, MetricSnapshot, topology_digest
from chennai_routing.routing.networkx_engine import NetworkXDijkstraEngine
from chennai_routing.routing.dynamic import CertifiedLazySynchronizer
from chennai_routing.routing.reservations import (
    ReservationLedger,
    ReservationPolicy,
    reservation_metric_replacements,
    route_after_reservation_update,
)
from types import MappingProxyType


def test_reservations_use_edge_entry_time_bins_and_skip_noncompliant() -> None:
    ab = ("a", "b", 0)
    bc = ("b", "c", 0)
    path = EnginePath(nodes=("a", "b", "c"), edges=(ab, bc), cost=12_000)
    ledger = ReservationLedger(ReservationPolicy(bin_seconds=10, vehicle_pce=1.5))
    assert ledger.reserve(
        path,
        departure_seconds=8,
        edge_travel_time_seconds={ab: 5, bc: 7},
        compliant=False,
    ) == ()
    assert ledger.reserve(
        path,
        departure_seconds=8,
        edge_travel_time_seconds={ab: 5, bc: 7},
        compliant=True,
    ) == ((ab, 0), (bc, 1))
    assert ledger.projected_pce(ab, 0) == 1.5
    assert ledger.projected_pce(bc, 1) == 1.5


def test_post_reservation_metric_is_applied_before_certificate_query() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key=0)
    graph.add_edge("b", "c", key=0)
    graph.add_edge("a", "c", key=0)
    edges = tuple(graph.edges(keys=True))
    weights = {edges[0]: 10_000, edges[1]: 10_000, edges[2]: 30_000}
    topology = topology_digest(tuple(graph.nodes), edges)
    synchronizer = CertifiedLazySynchronizer(
        NetworkXDijkstraEngine(graph),
        MetricSnapshot(topology, 0, MappingProxyType(weights)),
    )
    ledger = ReservationLedger()
    incumbent = EnginePath(
        nodes=("a", "b", "c"),
        edges=(("a", "b", 0), ("b", "c", 0)),
        cost=20_000,
    )
    ledger.reserve(
        incumbent,
        departure_seconds=0,
        edge_travel_time_seconds={("a", "b", 0): 10, ("b", "c", 0): 10},
        compliant=True,
        demand_pce=10,
    )
    replacements = reservation_metric_replacements(
        edges=edges,
        bin_index=0,
        ledger=ledger,
        free_flow_seconds={edge: weights[edge] / 1000 for edge in edges},
        base_entering_pce={edge: 0 for edge in edges},
        effective_capacity_pce_per_bin={edge: 10 for edge in edges},
    )
    result = route_after_reservation_update(
        synchronizer,
        source="a",
        target="c",
        version=1,
        replacements=replacements,
    )
    assert result.current_version == 1
    assert result.path is not None


def test_emergency_policy_prioritizes_safety_then_bounded_external_delay() -> None:
    unsafe_fast = EmergencyRouteCandidate("unsafe", (), 100, 1, 0, 0)
    safe_high_harm = EmergencyRouteCandidate("harm", (), 110, 0, 0, 50)
    safe_bounded = EmergencyRouteCandidate("bounded", (), 120, 0, 0, 5)
    chosen = select_emergency_route(
        (unsafe_fast, safe_high_harm, safe_bounded),
        EmergencyPolicy(deadline_seconds=150, ordinary_delay_cap_seconds=10),
    )
    assert chosen.route_id == "bounded"
