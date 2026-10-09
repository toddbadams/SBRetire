"""Required Spending from the Scenario's Budget (SPEC §6; configuration §6).

:class:`ScenarioSpending` supplies the engine's ``spending(month, alive)``:
S_t = B_m × I_t × F_t in nominal GBP, where B_m is ``budget.monthly_amount_today`` (today's GBP), I_t the
Inflation Index and F_t the Survivor Budget Factor — 1 while both are alive, the survivor's own
``survivor_budget_factor`` (else the household ``budget.survivor_budget_factor``) while exactly one is,
and 0 once both have died.
"""

from __future__ import annotations

import numpy as np

from sbretire.config import Scenario
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray


def _checked_budget(budget: float | FloatArray, paths_shape: tuple[int, ...]) -> float | FloatArray:
    values = np.asarray(budget, dtype=np.float64)
    if values.ndim not in (0, 1) or (values.ndim == 1 and values.shape != paths_shape):
        raise ValueError(f"monthly_budget_today must be a scalar or shape {paths_shape} (got {values.shape})")
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("monthly_budget_today must be finite and non-negative")
    return float(values) if values.ndim == 0 else values


class ScenarioSpending:
    """Monthly Required Spending for every path, built from a validated Scenario."""

    def __init__(
        self,
        scenario: Scenario,
        price_index: PriceIndex,
        monthly_budget_today: float | FloatArray | None = None,
    ) -> None:
        """``monthly_budget_today`` (today's GBP per month) overrides the Scenario's Budget: a scalar, or one
        value per path, shape (n_paths,) — used by the budget search (F-010)."""
        default = scenario.budget.survivor_budget_factor
        factors = [
            p.survivor_budget_factor if p.survivor_budget_factor is not None else default
            for p in scenario.people
        ]
        self._budget_today = _checked_budget(
            scenario.budget.monthly_amount_today if monthly_budget_today is None else monthly_budget_today,
            price_index.level(0).shape,
        )
        self._survivor_factor = np.array(factors, dtype=np.float64)  # factor when that person is the survivor
        self._price_index = price_index

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        """Nominal GBP spending due in ``month`` per path; ``alive`` is (2, n_paths) at the month's start."""
        n_alive = alive.sum(axis=0)
        survivor_factor = np.where(alive[0], self._survivor_factor[0], self._survivor_factor[1])
        factor = np.where(n_alive == 2, 1.0, np.where(n_alive == 1, survivor_factor, 0.0))
        return self._budget_today * self._price_index.level(month) * factor
