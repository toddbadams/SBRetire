"""Path classification and success metrics (SPEC §11; simulation-conventions §7)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.typing import NDArray

from sbretire.simulation import PathOutcomes


class PathClass(IntEnum):
    """Outcome of one Path (simulation-conventions §7)."""

    SUCCESSFUL = 0
    FAILED = 1
    UNRESOLVED = 2


def classify_paths(outcomes: PathOutcomes) -> NDArray[np.int8]:
    """Failed if ever depleted; else Unresolved if someone is alive at the Horizon; else Successful."""
    depleted = outcomes.depletion_month >= 0
    classes = np.where(
        depleted, PathClass.FAILED, np.where(outcomes.censored, PathClass.UNRESOLVED, PathClass.SUCCESSFUL)
    )
    return classes.astype(np.int8)


def _rate_and_error(successes: int, denominator: int) -> tuple[float, float] | tuple[None, None]:
    """p̂ = successes / denominator and its binomial SE √(p̂(1 − p̂)/denominator); (None, None) if empty."""
    if denominator == 0:
        return None, None
    rate = successes / denominator
    return rate, math.sqrt(rate * (1.0 - rate) / denominator)


@dataclass(frozen=True)
class SuccessMetrics:
    """SPEC §11 counts and rates for one Budget; each standard error uses its own rate's denominator."""

    n_paths: int
    n_successful: int
    n_failed: int
    n_unresolved: int
    n_completed: int
    conservative_success_rate: float
    """n_successful / n_paths — Unresolved Paths count as non-successes; the V1 target."""
    conservative_standard_error: float
    """Binomial SE of the conservative rate, denominator n_paths."""
    completed_success_rate: float | None
    """n_successful / n_completed; None when no path completed."""
    completed_standard_error: float | None
    """Binomial SE of the completed-path rate, denominator n_completed."""
    unresolved_share: float
    """n_unresolved / n_paths."""

    @classmethod
    def from_outcomes(cls, outcomes: PathOutcomes) -> SuccessMetrics:
        counts = np.bincount(classify_paths(outcomes), minlength=len(PathClass))
        n_successful, n_failed, n_unresolved = (int(count) for count in counts)
        n_paths = n_successful + n_failed + n_unresolved
        if n_paths == 0:
            raise ValueError("no paths to summarise")
        n_completed = n_successful + n_failed
        conservative, conservative_se = _rate_and_error(n_successful, n_paths)
        assert conservative is not None and conservative_se is not None
        completed, completed_se = _rate_and_error(n_successful, n_completed)
        return cls(
            n_paths=n_paths,
            n_successful=n_successful,
            n_failed=n_failed,
            n_unresolved=n_unresolved,
            n_completed=n_completed,
            conservative_success_rate=conservative,
            conservative_standard_error=conservative_se,
            completed_success_rate=completed,
            completed_standard_error=completed_se,
            unresolved_share=n_unresolved / n_paths,
        )
