"""Test doubles implementing ``sbretire.simulation.HouseholdCashFlows``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from sbretire.portfolio import BoolArray, FloatArray


@dataclass
class PerPersonCashFlows:
    """Per-path amounts: income paid per living person; spending scaled by a survivor factor.

    spending = spending_both * (1 if both alive, survivor_factor if one alive, 0 if none)
    income   = income_per_person * number alive
    ``extra_income(month)`` adds a household amount from a given month (e.g. to test that a depleted path
    is not revived).
    Every call is recorded so tests can see what the engine asked for.
    """

    spending_both: FloatArray
    income_per_person: FloatArray
    survivor_factor: float = 1.0
    extra_income: Callable[[int], float] = lambda month: 0.0
    calls: list[tuple[str, int, BoolArray]] = field(default_factory=list)

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        self.calls.append(("income", month, alive.copy()))
        return self.income_per_person * alive.sum(axis=0) + self.extra_income(month)

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        self.calls.append(("spending", month, alive.copy()))
        n_alive = alive.sum(axis=0)
        factor = np.where(n_alive == 2, 1.0, np.where(n_alive == 1, self.survivor_factor, 0.0))
        return self.spending_both * factor


def constant(n_paths: int, *, spending: float, income: float = 0.0) -> PerPersonCashFlows:
    """Household spending ``spending`` while anyone is alive; ``income`` per living person."""
    return PerPersonCashFlows(
        spending_both=np.full(n_paths, spending, dtype=np.float64),
        income_per_person=np.full(n_paths, income, dtype=np.float64),
    )
