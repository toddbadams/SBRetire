"""Path loop (SPEC §10.2; simulation-conventions §2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from sbretire.portfolio import BoolArray, FloatArray

IntArray = NDArray[np.int64]


class HouseholdCashFlows(Protocol):
    def income(self, month: int, alive: BoolArray) -> FloatArray: ...

    def spending(self, month: int, alive: BoolArray) -> FloatArray: ...


class MonthObserver(Protocol):
    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None: ...


@dataclass(frozen=True)
class PathOutcomes:
    depletion_month: IntArray
    shortfall: FloatArray
    household_end_month: IntArray
    censored: BoolArray
    final_balance: FloatArray


def simulate_paths(
    *,
    starting_balance: float,
    annual_return: float,
    death_month: IntArray,
    horizon_months: int,
    cash_flows: HouseholdCashFlows,
    observer: MonthObserver | None = None,
) -> PathOutcomes:
    raise NotImplementedError
