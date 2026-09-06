"""Deterministic lag and classification-error experiments for road evidence."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class EvidenceRobustnessSummary:
    """Confusion and availability counts for one perturbed evidence trace."""

    step_count: int
    available_count: int
    unavailable_count: int
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int

    @property
    def availability_rate(self) -> float:
        return self.available_count / self.step_count

    @property
    def accuracy_when_available(self) -> float | None:
        if self.available_count == 0:
            return None
        return (self.true_positive + self.true_negative) / self.available_count


def perturb_binary_evidence(
    truth: Sequence[bool],
    *,
    lag_steps: int,
    false_positive_rate: float,
    false_negative_rate: float,
    seed: int,
) -> tuple[bool | None, ...]:
    """Apply observation lag and seeded classification errors.

    ``None`` denotes evidence not yet available because the requested lag
    reaches before the start of the trace.
    """

    if not truth:
        raise ValueError("The truth trace must not be empty.")
    if type(lag_steps) is not int or lag_steps < 0:
        raise ValueError("lag_steps must be a non-negative integer.")
    for name, rate in (
        ("false_positive_rate", false_positive_rate),
        ("false_negative_rate", false_negative_rate),
    ):
        if not 0 <= rate <= 1:
            raise ValueError(f"{name} must lie in [0, 1].")
    if any(type(value) is not bool for value in truth):
        raise TypeError("Binary evidence truth values must be bool.")

    rng = random.Random(seed)
    observed: list[bool | None] = []
    for step in range(len(truth)):
        source_step = step - lag_steps
        if source_step < 0:
            observed.append(None)
            continue
        source_value = truth[source_step]
        if source_value:
            observed.append(False if rng.random() < false_negative_rate else True)
        else:
            observed.append(True if rng.random() < false_positive_rate else False)
    return tuple(observed)


def summarize_binary_evidence(
    truth: Sequence[bool],
    observed: Sequence[bool | None],
) -> EvidenceRobustnessSummary:
    """Compare a perturbed trace with contemporaneous ground truth."""

    if len(truth) != len(observed) or not truth:
        raise ValueError("Truth and observed traces need the same non-zero length.")
    if any(type(value) is not bool for value in truth):
        raise TypeError("Binary evidence truth values must be bool.")
    if any(value is not None and type(value) is not bool for value in observed):
        raise TypeError("Observed values must be bool or None.")

    true_positive = true_negative = false_positive = false_negative = 0
    unavailable = 0
    for expected, actual in zip(truth, observed):
        if actual is None:
            unavailable += 1
        elif expected and actual:
            true_positive += 1
        elif not expected and not actual:
            true_negative += 1
        elif actual:
            false_positive += 1
        else:
            false_negative += 1

    return EvidenceRobustnessSummary(
        step_count=len(truth),
        available_count=len(truth) - unavailable,
        unavailable_count=unavailable,
        true_positive=true_positive,
        true_negative=true_negative,
        false_positive=false_positive,
        false_negative=false_negative,
    )
