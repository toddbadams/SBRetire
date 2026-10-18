"""Efficient frontier of the priced sleeve and the re-weighting analysis (F-029; portfolio-data §21–§24).

Analysis, not advice: every figure is estimated from past monthly returns.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from sbretire.ledger.returns import MonthlyReturn, add_months

Covariance = Literal["shrunk", "sample"]


def ledoit_wolf(samples: NDArray[np.float64]) -> tuple[NDArray[np.float64], float]:
    """(covariance, intensity): the sample covariance (÷ T) shrunk towards ``m·I``, ``m`` its mean variance.

    Ledoit & Wolf (2004), "Honey, I shrunk the sample covariance matrix": intensity ``min(b̄², d²) / d²`` with
    ``d²`` the distance of the sample covariance from the target and ``b̄²`` the estimation noise.
    """
    t, n = samples.shape
    centred = samples - samples.mean(axis=0)
    sample = centred.T @ centred / t
    m = float(np.trace(sample)) / n
    target = m * np.eye(n)
    d2 = float(np.sum((sample - target) ** 2)) / n
    outer = np.einsum("ti,tj->tij", centred, centred)
    b_bar2 = float(np.sum((outer - sample) ** 2)) / n / t**2
    shrink = 0.0 if d2 == 0.0 else min(b_bar2, d2) / d2
    return shrink * target + (1.0 - shrink) * sample, shrink


@dataclass(frozen=True)
class Estimates:
    """Annual expected returns and covariance of the priced sleeve, and today's sleeve weights."""

    series: list[str]
    mean: NDArray[np.float64]
    """Annual: 12 × the mean monthly return."""
    cov: NDArray[np.float64]
    """Annual: 12 × the monthly covariance (Ledoit-Wolf shrunk or sample)."""
    shrinkage: float | None
    today: NDArray[np.float64]
    """Today's weights within the sleeve (sum 1)."""
    returns: NDArray[np.float64]
    """Monthly returns, months × series, for re-estimating on sub-windows."""


def estimate(
    returns: Sequence[MonthlyReturn],
    values: Mapping[str, float],
    first: dt.date,
    last: dt.date,
    covariance: Covariance = "shrunk",
) -> Estimates:
    """Estimates over the priced sleeve: series with today's value > 0 and a return in every month (§21).

    The sample option uses the n − 1 sample covariance; the shrunk option Ledoit-Wolf's (÷ T) estimate.
    """
    months: list[dt.date] = []
    month = first
    while month <= last:
        months.append(month)
        month = add_months(month, 1)
    by_series: dict[str, dict[dt.date, float]] = defaultdict(dict)
    for row in returns:
        if row.return_gbp is not None:
            by_series[row.series][row.month] = row.return_gbp
    sleeve = [
        series for series, value in values.items()
        if value > 0 and all(month in by_series.get(series, {}) for month in months)
    ]  # fmt: skip
    matrix = np.array([[by_series[s][m] for s in sleeve] for m in months], dtype=np.float64).reshape(
        len(months), len(sleeve)
    )
    shrinkage: float | None
    if covariance == "shrunk" and sleeve:
        monthly_cov, shrinkage = ledoit_wolf(matrix)
    else:
        monthly_cov = np.cov(matrix, rowvar=False, ddof=1).reshape(len(sleeve), len(sleeve))
        shrinkage = None
    weights = np.array([values[s] for s in sleeve], dtype=np.float64)
    today = weights / weights.sum() if weights.size else weights
    return Estimates(sleeve, 12.0 * matrix.mean(axis=0), 12.0 * monthly_cov, shrinkage, today, matrix)


def min_variance(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def frontier(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def max_sharpe(*args: object, **kwargs: object) -> object:
    raise NotImplementedError


def max_return_at(*args: object, **kwargs: object) -> object:
    raise NotImplementedError
