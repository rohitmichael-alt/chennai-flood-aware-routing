"""Time-binned projected-load reservations for compliant vehicles.

Reservations are a deterministic routing input, not an equilibrium solver and
not observed Chennai demand.  The caller must update the represented metric
from this ledger before asking a certificate-gated synchronizer for a route.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from chennai_routing.models.bpr import bpr_travel_time
from chennai_routing.routing.dynamic import (
    CertifiedLazySynchronizer,
    RouteResult,
    WeightUpdateBatch,
)
from chennai_routing.routing.engine import EdgeId, EnginePath, NodeId, Weight
from chennai_routing.routing.quantization import quantize_seconds


@dataclass(frozen=True)
class ReservationPolicy:
    bin_seconds: int = 300
    vehicle_pce: float = 1.0
    classification: str = "SCENARIO"

    def __post_init__(self) -> None:
        if type(self.bin_seconds) is not int or self.bin_seconds <= 0:
            raise ValueError("bin_seconds must be a positive integer.")
        if not math.isfinite(self.vehicle_pce) or self.vehicle_pce <= 0:
            raise ValueError("vehicle_pce must be finite and positive.")
        if self.classification != "SCENARIO":
            raise ValueError("Uncalibrated reservation policy must remain SCENARIO.")


@dataclass
class ReservationLedger:
    """Projected entering PCE keyed by directed arc and entry-time bin."""

    policy: ReservationPolicy = field(default_factory=ReservationPolicy)
    _pce: dict[tuple[EdgeId, int], float] = field(default_factory=dict, init=False)

    def reserve(
        self,
        path: EnginePath,
        *,
        departure_seconds: float,
        edge_travel_time_seconds: Mapping[EdgeId, float],
        compliant: bool,
        demand_pce: float | None = None,
    ) -> tuple[tuple[EdgeId, int], ...]:
        if not compliant:
            return ()
        if not math.isfinite(departure_seconds) or departure_seconds < 0:
            raise ValueError("departure_seconds must be finite and non-negative.")
        amount = self.policy.vehicle_pce if demand_pce is None else demand_pce
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("demand_pce must be finite and positive.")
        if set(path.edges) - set(edge_travel_time_seconds):
            raise ValueError("Every path edge needs a projected travel time.")

        entry_time = float(departure_seconds)
        reserved: list[tuple[EdgeId, int]] = []
        for edge in path.edges:
            duration = float(edge_travel_time_seconds[edge])
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Projected edge travel times must be finite and non-negative.")
            bin_index = int(entry_time // self.policy.bin_seconds)
            key = (edge, bin_index)
            self._pce[key] = self._pce.get(key, 0.0) + float(amount)
            reserved.append(key)
            entry_time += duration
        return tuple(reserved)

    def projected_pce(self, edge: EdgeId, bin_index: int) -> float:
        if type(bin_index) is not int or bin_index < 0:
            raise ValueError("bin_index must be a non-negative integer.")
        return self._pce.get((edge, bin_index), 0.0)

    def snapshot(self) -> Mapping[tuple[EdgeId, int], float]:
        return MappingProxyType(dict(self._pce))


def reservation_metric_replacements(
    *,
    edges: tuple[EdgeId, ...],
    bin_index: int,
    ledger: ReservationLedger,
    free_flow_seconds: Mapping[EdgeId, float],
    base_entering_pce: Mapping[EdgeId, float],
    effective_capacity_pce_per_bin: Mapping[EdgeId, float],
    alpha: float = 0.15,
    beta: float = 4.0,
) -> tuple[tuple[EdgeId, Weight], ...]:
    """Build a complete post-reservation BPR metric for one time bin."""

    if set(edges) != set(free_flow_seconds):
        raise ValueError("free_flow_seconds must exactly cover edges.")
    if set(edges) != set(base_entering_pce):
        raise ValueError("base_entering_pce must exactly cover edges.")
    if set(edges) != set(effective_capacity_pce_per_bin):
        raise ValueError("effective capacities must exactly cover edges.")
    replacements: list[tuple[EdgeId, Weight]] = []
    for edge in edges:
        projected_flow = base_entering_pce[edge] + ledger.projected_pce(edge, bin_index)
        seconds = bpr_travel_time(
            free_flow_seconds[edge],
            projected_flow,
            effective_capacity_pce_per_bin[edge],
            alpha=alpha,
            beta=beta,
        )
        replacements.append((edge, math.inf if math.isinf(seconds) else quantize_seconds(seconds)))
    return tuple(replacements)


def route_after_reservation_update(
    synchronizer: CertifiedLazySynchronizer,
    *,
    source: NodeId,
    target: NodeId,
    version: int,
    replacements: tuple[tuple[EdgeId, Weight], ...],
) -> RouteResult:
    """Enforce the Stage 7 ordering: metric update, then certificate/query."""

    state = synchronizer.state()
    synchronizer.apply_updates(
        WeightUpdateBatch(
            base_version=state.current_version,
            version=version,
            replacements=replacements,
        )
    )
    return synchronizer.route(source, target)
