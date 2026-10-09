"""Maximum Sustainable Budget by per-path threshold bisection (SPEC §14; optimization §1)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from sbretire.config import Scenario
from sbretire.monte_carlo import RandomInputs

BUDGET_TOLERANCE: Final = 1.0
BUDGET_CAP: Final = 1_000_000.0


@dataclass(frozen=True)
class ThresholdSearch:
    thresholds: NDArray[np.float64]
    capped: NDArray[np.bool_]
    iterations: int
    upper_bound: float


def path_budget_thresholds(scenario: Scenario, inputs: RandomInputs) -> ThresholdSearch:
    raise NotImplementedError


@dataclass(frozen=True)
class BudgetResult:
    target_probability: float
    maximum_monthly_budget_today: float | None
    maximum_annual_budget_today: float | None
    estimated_success_probability: float | None
    standard_error: float | None
    unresolved_fraction: float
    budget_tolerance: float
    converged: bool
    iterations: int
    note: str


def maximum_sustainable_budgets(search: ThresholdSearch, targets: Sequence[float]) -> list[BudgetResult]:
    raise NotImplementedError
