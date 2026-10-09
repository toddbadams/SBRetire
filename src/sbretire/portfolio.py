"""Monthly portfolio accounting (SPEC §9; simulation-conventions §2)."""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


def monthly_return_rate(annual_return: float) -> float:
    raise NotImplementedError


class MonthResult(NamedTuple):
    balance: FloatArray
    depleted: BoolArray
    shortfall: FloatArray


def apply_month(balance: FloatArray, rate: float, income: FloatArray, spending: FloatArray) -> MonthResult:
    raise NotImplementedError
