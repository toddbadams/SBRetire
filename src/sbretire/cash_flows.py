"""Household cash flows from a Scenario: income and Required Spending for the engine."""

from __future__ import annotations

from sbretire.config import Scenario
from sbretire.inflation import PriceIndex
from sbretire.portfolio import BoolArray, FloatArray


class ScenarioCashFlows:
    def __init__(self, scenario: Scenario, price_index: PriceIndex, n_paths: int) -> None:
        raise NotImplementedError

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        raise NotImplementedError

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        raise NotImplementedError
