"""Inflation: the price-index seam (SPEC §6).

Income and spending read the cumulative **Inflation Index** I_t through :class:`PriceIndex`, one month at a
time, so the stochastic process (F-006) can be swapped in without changing them. I = 1 in the As-Of month,
which is what makes "today's GBP" amounts nominal: nominal = today's amount × I_t.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from sbretire.config import InflationAssumptions
from sbretire.portfolio import FloatArray


class PriceIndex(Protocol):
    """Cumulative price level per path."""

    def level(self, month: int) -> FloatArray:
        """I_t for ``month`` (0 = As-Of month), shape (n_paths,)."""
        ...


class FlatPriceIndex:
    """Zero inflation: I_t = 1 for every path and month."""

    def __init__(self, n_paths: int) -> None:
        self._ones = np.ones(n_paths, dtype=np.float64)
        self._ones.flags.writeable = False

    def level(self, month: int) -> FloatArray:
        return self._ones


class AnnualStepPriceIndex:
    """Constant inflation stepping once a year on As-Of anniversaries: I_t = (1 + rate)^floor(t / 12).

    Deterministic illustration of SPEC §6's "one annual rate held for twelve months"
    (simulation-conventions §3, provisional until F-006).
    """

    def __init__(self, n_paths: int, annual_rate: float) -> None:
        if annual_rate <= -1:
            raise ValueError(f"annual_rate must be greater than -1 (got {annual_rate})")
        self._n_paths = n_paths
        self._growth = 1.0 + annual_rate

    def level(self, month: int) -> FloatArray:
        return np.full(self._n_paths, self._growth ** (month // 12), dtype=np.float64)


@dataclass(frozen=True)
class Ar1LognormalParams:
    log_mean: float
    ar1_coefficient: float
    innovation_sd: float
    initial_rate: float


def fit_ar1_lognormal(annual_rates: Sequence[float], initial_rate: float | None = None) -> Ar1LognormalParams:
    raise NotImplementedError


def load_cpi_series(path: Path) -> dict[int, float]:
    raise NotImplementedError


def calibrate_inflation(inflation: InflationAssumptions) -> Ar1LognormalParams:
    raise NotImplementedError
