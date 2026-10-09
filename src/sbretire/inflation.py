"""Inflation: the price-index seam (SPEC §6).

Income and spending read the cumulative **Inflation Index** I_t through :class:`PriceIndex`, one month at a
time, so the stochastic process (F-006) can be swapped in without changing them. I = 1 in the As-Of month,
which is what makes "today's GBP" amounts nominal: nominal = today's amount × I_t.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

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
    """AR(1) in x = log(1 + annual rate): x_y = μ + φ (x_{y-1} − μ) + σ ε_y (data-and-calibration §2)."""

    log_mean: float
    """μ, mean of log(1 + annual rate); the median annual rate is e^μ − 1."""
    ar1_coefficient: float
    """φ, −1 < φ < 1: share of last year's deviation from μ carried into this year."""
    innovation_sd: float
    """σ ≥ 0, SD of the yearly shock to log(1 + annual rate); stationary SD is σ / √(1 − φ²)."""
    initial_rate: float
    """Annual rate π for the year before the As-Of date (> −1)."""

    @classmethod
    def from_config(cls, inflation: InflationAssumptions) -> Ar1LognormalParams:
        return cls(
            inflation.log_mean, inflation.ar1_coefficient, inflation.innovation_sd, inflation.initial_rate
        )


def fit_ar1_lognormal(annual_rates: Sequence[float], initial_rate: float | None = None) -> Ar1LognormalParams:
    """Calibrate the AR(1) lognormal process to consecutive annual rates (decimals, oldest first).

    μ = mean of x = log(1 + π); φ = Σ(x_{t−1} − μ)(x_t − μ) / Σ(x_{t−1} − μ)²; σ = √(Σ e² / (m − 2)) over the
    m = n − 1 residuals e_t = (x_t − μ) − φ (x_{t−1} − μ) (two fitted parameters). ``initial_rate`` defaults
    to the last observed rate.
    """
    if len(annual_rates) < 4:
        raise ValueError(f"need at least 4 annual rates to fit an AR(1) process (got {len(annual_rates)})")
    if any(rate <= -1 for rate in annual_rates):
        raise ValueError("every annual rate must be greater than -1")
    x = np.log1p(np.asarray(annual_rates, dtype=np.float64))
    mu = float(x.mean())
    d = x - mu
    lagged, current = d[:-1], d[1:]
    denominator = float(lagged @ lagged)
    if denominator == 0.0:
        raise ValueError("the annual rates are constant; an AR(1) coefficient cannot be estimated")
    phi = float(lagged @ current) / denominator
    residuals = current - phi * lagged
    sigma = float(np.sqrt(residuals @ residuals / (len(residuals) - 2)))
    last = float(annual_rates[-1]) if initial_rate is None else initial_rate
    return Ar1LognormalParams(log_mean=mu, ar1_coefficient=phi, innovation_sd=sigma, initial_rate=last)


CPI_COLUMNS = ("year", "annual_rate")


def load_cpi_series(path: Path) -> dict[int, float]:
    """Read ``uk_cpi.csv`` (``year,annual_rate``, decimals) into {year: rate}.

    Raises ``ValueError`` naming file:line for a bad header or row, a duplicate year or a gap.
    """
    rates: dict[int, float] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None or tuple(cell.strip() for cell in header) != CPI_COLUMNS:
            raise ValueError(f"{path.name}:1: columns must be {','.join(CPI_COLUMNS)} (got {header!r})")
        for line, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                year, rate = int(row[0]), float(row[1])
            except (ValueError, IndexError):
                raise ValueError(
                    f"{path.name}:{line}: expected a whole year and a decimal rate (got {row!r})"
                ) from None
            if not (math.isfinite(rate) and rate > -1):
                raise ValueError(
                    f"{path.name}:{line}: annual_rate must be finite and greater than -1 (got {rate})"
                )
            if year in rates:
                raise ValueError(f"{path.name}:{line}: duplicate year {year}")
            rates[year] = rate
    years = sorted(rates)
    if not years or years != list(range(years[0], years[-1] + 1)):
        raise ValueError(f"{path.name}: years must be contiguous (got {years[:1]}…{years[-1:]})")
    return rates


def calibrate_inflation(inflation: InflationAssumptions) -> Ar1LognormalParams:
    """Fit to ``inflation.data_file`` over ``inflation.source_period``; initial rate = the last year."""
    rates = load_cpi_series(inflation.data_file)
    period = range(inflation.first_year, inflation.last_year + 1)
    missing = [year for year in period if year not in rates]
    if missing:
        raise ValueError(
            f"{inflation.data_file.name} lacks years {missing} from source_period {inflation.source_period}"
        )
    return fit_ar1_lognormal([rates[year] for year in period])


def draw_annual_rates(
    rng: np.random.Generator, params: Ar1LognormalParams, n_paths: int, n_years: int
) -> NDArray[np.float64]:
    raise NotImplementedError


class StochasticPriceIndex:
    def __init__(self, annual_rates: NDArray[np.float64]) -> None:
        raise NotImplementedError

    @classmethod
    def constant(cls, n_paths: int, n_years: int, annual_rate: float) -> StochasticPriceIndex:
        raise NotImplementedError

    def level(self, month: int) -> FloatArray:
        raise NotImplementedError
