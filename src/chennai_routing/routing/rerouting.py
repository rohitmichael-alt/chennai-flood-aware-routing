"""Post-certificate route-adoption filter.

This is not a shortest-path algorithm and is not claimed to reach equilibrium.
It decides whether a vehicle should switch from an already adopted path to a
newly computed candidate, using labelled SCENARIO thresholds.

Cooldown suppresses only opportunistic minimum-gain switches. Incumbent
infeasibility and declared degradation adopt immediately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chennai_routing.routing.engine import EnginePath


@dataclass(frozen=True)
class AdoptionThresholds:
    """Scenario thresholds for whether to replace an adopted route."""

    degradation: float = 0.15
    minimum_gain: float = 0.05
    cooldown_epochs: int = 1
    classification: str = "SCENARIO"


@dataclass(frozen=True)
class AdoptionDecision:
    adopt: bool
    reason: str


def decide_route_adoption(
    *,
    adopted: EnginePath | None,
    candidate: EnginePath | None,
    epoch: int,
    last_change_epoch: int | None,
    thresholds: AdoptionThresholds | None = None,
) -> AdoptionDecision:
    """Filter a certificate/engine candidate before treating it as adopted."""

    chosen = thresholds or AdoptionThresholds()
    if candidate is None:
        return AdoptionDecision(False, "no_candidate")
    if adopted is None:
        return AdoptionDecision(True, "no_incumbent")
    adopted_cost = float(adopted.cost)
    candidate_cost = float(candidate.cost)
    if _infeasible(adopted) or not math.isfinite(adopted_cost):
        return AdoptionDecision(True, "incumbent_infeasible")
    if not math.isfinite(candidate_cost):
        return AdoptionDecision(False, "candidate_infeasible")
    if adopted_cost > 0 and (candidate_cost - adopted_cost) / adopted_cost >= chosen.degradation:
        return AdoptionDecision(True, "degradation")
    if epoch_in_cooldown(epoch, last_change_epoch, chosen.cooldown_epochs):
        return AdoptionDecision(False, "cooldown")
    if adopted_cost > 0 and (adopted_cost - candidate_cost) / adopted_cost >= chosen.minimum_gain:
        return AdoptionDecision(True, "minimum_gain")
    return AdoptionDecision(False, "hold")


def epoch_in_cooldown(
    epoch: int,
    last_change_epoch: int | None,
    cooldown_epochs: int,
) -> bool:
    if last_change_epoch is None:
        return False
    return epoch - last_change_epoch < cooldown_epochs


def _infeasible(path: EnginePath) -> bool:
    return path.cost is not None and math.isinf(float(path.cost))
