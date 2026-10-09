"""Household cash flows from a Scenario: income and Required Spending for the engine.

:class:`ScenarioCashFlows` is the ``HouseholdCashFlows`` that ``simulate_paths`` consumes for a real
Scenario: :class:`~sbretire.income.ScenarioIncome` plus :class:`~sbretire.spending.ScenarioSpending`, both
reading the same Inflation Index (SPEC §6).
"""

from __future__ import annotations

from sbretire.config import Scenario
from sbretire.income import ScenarioIncome
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.spending import ScenarioSpending


class ScenarioCashFlows:
    """Monthly income and Required Spending (nominal GBP) for ``n_paths`` paths of one Scenario."""

    def __init__(
        self,
        scenario: Scenario,
        price_index: PriceIndex,
        n_paths: int,
        monthly_budget_today: float | FloatArray | None = None,
    ) -> None:
        shape = price_index.level(0).shape
        if shape != (n_paths,):
            raise ValueError(f"price index covers {shape} paths but n_paths is {n_paths}")
        self._income = ScenarioIncome(scenario, price_index)
        self._spending = ScenarioSpending(scenario, price_index, monthly_budget_today)

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        return self._income.income(month, alive)

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        return self._spending.spending(month, alive)
