"""Household income from the Scenario's Income Streams (SPEC §8; configuration §3–§5)."""

from __future__ import annotations

from sbretire.config import Scenario
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray


class ScenarioIncome:
    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None:
        self.scenario = scenario
        self.price_index = price_index

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        raise NotImplementedError
