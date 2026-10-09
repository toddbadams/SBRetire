"""Inflation: the price-index seam (SPEC §6).

Income and spending read the cumulative **Inflation Index** I_t through :class:`PriceIndex`, one month at a
time, so the stochastic process (F-006) can be swapped in without changing them. I = 1 in the As-Of month,
which is what makes "today's GBP" amounts nominal: nominal = today's amount × I_t.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from sbretire.config import InflationAssumptions, Scenario, ScenarioIssue
from sbretire.metadata import DataFileRecord, file_sha256
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
    """Annual inflation rates π, shape (n_years, n_paths), for simulated years starting at the As-Of month.

    Draws ε = ``rng.standard_normal((n_years, n_paths))`` in one call, year-major, so a shorter horizon reuses
    the same early-year draws; then x_y = μ + φ (x_{y-1} − μ) + σ ε_y from x_{-1} = log(1 + initial_rate).
    The recursion over years runs once per run, before the month loop, vectorised over paths.
    """
    if n_paths < 1 or n_years < 1:
        raise ValueError(f"n_paths and n_years must be positive (got {n_paths}, {n_years})")
    shocks = rng.standard_normal((n_years, n_paths))
    mu, phi, sigma = params.log_mean, params.ar1_coefficient, params.innovation_sd
    log_growth = np.empty((n_years, n_paths), dtype=np.float64)
    previous = np.full(n_paths, math.log1p(params.initial_rate))
    for year in range(n_years):
        previous = mu + phi * (previous - mu) + sigma * shocks[year]
        log_growth[year] = previous
    return np.expm1(log_growth)


class StochasticPriceIndex:
    """Cumulative Inflation Index from annual rates compounding monthly (simulation-conventions §5).

    I_0 = 1 in the As-Of month; for 12k ≤ t ≤ 12(k + 1), I_t = I_{12k} · (1 + π_k)^((t − 12k)/12), so at
    anniversaries I_{12k} = ∏_{j<k}(1 + π_j). Stores log growth (n_years, n_paths) and cumulative log levels
    (n_years + 1, n_paths); ``level`` is computed on demand.
    """

    def __init__(self, annual_rates: NDArray[np.float64]) -> None:
        rates = np.asarray(annual_rates, dtype=np.float64)
        if rates.ndim != 2:
            raise ValueError(f"annual_rates must be 2-D (n_years, n_paths), got shape {rates.shape}")
        if not np.all(np.isfinite(rates)):
            raise ValueError("annual_rates must be finite")
        if not np.all(rates > -1):
            raise ValueError("every annual rate must be greater than -1")
        self._log_growth: FloatArray = np.log1p(rates)
        self._log_level: FloatArray = np.vstack(
            [np.zeros((1, rates.shape[1])), np.cumsum(self._log_growth, axis=0)]
        )
        self._n_years: int = int(rates.shape[0])

    @classmethod
    def constant(cls, n_paths: int, n_years: int, annual_rate: float) -> StochasticPriceIndex:
        """Every path and year at ``annual_rate`` (deterministic preview)."""
        return cls(np.full((n_years, n_paths), annual_rate, dtype=np.float64))

    @property
    def n_years(self) -> int:
        return self._n_years

    def level(self, month: int) -> FloatArray:
        """I_t for ``month`` (0 = As-Of month … 12·n_years), shape (n_paths,)."""
        if not 0 <= month <= 12 * self._n_years:
            raise ValueError(f"month must be between 0 and {12 * self._n_years} (got {month})")
        year, within = divmod(month, 12)
        log_level = self._log_level[year]
        if year < self._n_years:
            log_level = log_level + (within / 12) * self._log_growth[year]
        result: FloatArray = np.exp(log_level)
        return result


def build_price_index(scenario: Scenario, rng: np.random.Generator, n_paths: int) -> StochasticPriceIndex:
    """Draw the run's inflation paths from ``rng`` (the inflation Random Stream) for the whole horizon.

    Call once per run and reuse the result for every candidate (Common Random Numbers,
    simulation-conventions §4).
    """
    params = Ar1LognormalParams.from_config(scenario.inflation)
    rates = draw_annual_rates(rng, params, n_paths=n_paths, n_years=scenario.model.horizon_years)
    return StochasticPriceIndex(rates)


def cpi_sidecar_path(path: Path) -> Path:
    """``uk_cpi.csv`` -> ``uk_cpi.meta.json`` beside it."""
    return path.with_name(path.stem + ".meta.json")


def inflation_data_file_record(inflation: InflationAssumptions) -> DataFileRecord:
    """The CPI calibration file as a Run Metadata entry (SHA-256 of the CSV; edition and retrieval date)."""
    meta = json.loads(cpi_sidecar_path(inflation.data_file).read_text(encoding="utf-8"))
    return DataFileRecord(
        role="inflation",
        path=str(inflation.data_file),
        sha256=file_sha256(inflation.data_file),
        version=str(meta["edition"]),
        retrieved=str(meta["retrieved"]),
    )


def inflation_coverage_issues(inflation: InflationAssumptions) -> list[ScenarioIssue]:
    """Problems reading ``inflation.data_file`` or years of ``source_period`` it lacks (SPEC §4.3)."""
    try:
        rates = load_cpi_series(inflation.data_file)
    except ValueError as exc:
        return [ScenarioIssue("inflation.data_file", str(exc))]
    missing = [year for year in range(inflation.first_year, inflation.last_year + 1) if year not in rates]
    if not missing:
        return []
    message = (
        f"{inflation.data_file.name} covers {min(rates)}-{max(rates)} but source_period "
        f"{inflation.source_period} needs {missing[0]}-{missing[-1]}"
    )
    return [ScenarioIssue("inflation.source_period", message)]
