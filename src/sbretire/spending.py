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


class ScenarioSpending:
    """Monthly Required Spending for every path, built from a validated Scenario."""

    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None:
        default = scenario.budget.survivor_budget_factor
        factors = [
            p.survivor_budget_factor if p.survivor_budget_factor is not None else default
            for p in scenario.people
        ]
        self._budget_today = scenario.budget.monthly_amount_today
        self._survivor_factor = np.array(factors, dtype=np.float64)  # factor when that person is the survivor
        self._price_index = price_index

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        """Nominal GBP spending due in ``month`` per path; ``alive`` is (2, n_paths) at the month's start."""
        n_alive = alive.sum(axis=0)
        survivor_factor = np.where(alive[0], self._survivor_factor[0], self._survivor_factor[1])
        factor = np.where(n_alive == 2, 1.0, np.where(n_alive == 1, survivor_factor, 0.0))
        return self._budget_today * self._price_index.level(month) * factor
