"""Monthly portfolio accounting (SPEC §9; simulation-conventions §2).

All amounts are nominal GBP; arrays hold one value per Path.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


def monthly_return_rate(annual_return: float) -> float:
    """Monthly effective rate equivalent to a fixed annual effective return: (1 + r_a)^(1/12) − 1."""
    if annual_return <= -1:
        raise ValueError(f"annual_return must be greater than -1 (got {annual_return})")
    return float((1.0 + annual_return) ** (1.0 / 12.0) - 1.0)


class MonthResult(NamedTuple):
    """Outcome of one month for every path."""

    balance: FloatArray  # closing balance, never negative
    depleted: BoolArray  # spending could not be funded this month
    shortfall: FloatArray  # unmet spending this month (0 where funded)


def monthly_return_rates(annual_return: float | FloatArray, n_paths: int) -> float | FloatArray:
    """:func:`monthly_return_rate` for a scalar, or elementwise for one annual return per path (n_paths,)."""
    values = np.asarray(annual_return, dtype=np.float64)
    if values.ndim == 0:
        return monthly_return_rate(float(values))
    if values.shape != (n_paths,):
        raise ValueError(f"annual_return must be a scalar or shape ({n_paths},) (got {values.shape})")
    if not np.all(np.isfinite(values)) or np.any(values <= -1):
        raise ValueError("annual_return must be finite and greater than -1 on every path")
    rates: FloatArray = (1.0 + values) ** (1.0 / 12.0) - 1.0
    return rates


def apply_month(
    balance: FloatArray, rate: float | FloatArray, income: FloatArray, spending: FloatArray
) -> MonthResult:
    """One month of cash flows, in the documented order.

    The monthly ``rate`` (scalar or per path) is applied to the opening ``balance``, then ``income`` is
    added. If the result is less than ``spending`` the path is depleted: the available money is spent, the
    remainder is the shortfall and the closing balance is 0. Otherwise spending is paid in full (equality is
    funded).
    """
    available = balance * (1.0 + rate) + income
    depleted = available < spending
    closing = np.where(depleted, 0.0, available - spending)
    shortfall = np.where(depleted, spending - available, 0.0)
    return MonthResult(closing, depleted, shortfall)
