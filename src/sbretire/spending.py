"""Required Spending from the Scenario's Budget (SPEC §6; configuration §6)."""

from __future__ import annotations

from sbretire.config import Scenario
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray


class ScenarioSpending:
    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None:
        self.scenario = scenario
        self.price_index = price_index

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        raise NotImplementedError
