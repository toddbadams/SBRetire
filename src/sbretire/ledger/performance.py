"""Performance and drawdown of today's portfolio mix over past prices (F-027; portfolio-data §15–§17).

Returns are monthly and in GBP. Annual figures: return compounds the months (``Π(1 + r)^(12/n) − 1``),
volatility is the sample standard deviation × √12, Sharpe is ``12 × mean(r − r_f) / (√12 × sd)`` with ``r_f``
the monthly risk-free rate.
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

from sbretire.ledger.returns import MonthlyReturn, add_months

_FLAT: Final = 1e-12
"""A standard deviation at or below this is treated as zero (Sharpe undefined)."""


def monthly_rate(annual: float) -> float:
    """The monthly rate that compounds to ``annual`` over 12 months."""
    return float((1.0 + annual) ** (1.0 / 12.0) - 1.0)


@dataclass(frozen=True)
class Metrics:
    """Summary of a monthly return series; ``None`` where it is undefined."""

    months: int
    annual_return: float | None
    annual_volatility: float | None
    sharpe: float | None
    max_drawdown: float
    """Largest fall of the wealth index from a previous peak, a fraction ≥ 0."""
    peak: dt.date | None
    trough: dt.date | None
    recovery: dt.date | None
    """First month the wealth index regains the peak; ``None`` if it never does."""


def drawdowns(returns: Sequence[float]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """(wealth index, drawdown) per month; wealth starts at 1 before the first month."""
    wealth = np.cumprod(1.0 + np.asarray(returns, dtype=np.float64))
    peaks = np.maximum.accumulate(np.concatenate(([1.0], wealth)))[1:]
    return wealth, 1.0 - wealth / peaks


def metrics(months: Sequence[dt.date], returns: Sequence[float], risk_free: float) -> Metrics:
    """Annual return, volatility, Sharpe and worst drawdown of ``returns`` (one per month in ``months``).

    ``peak`` is ``None`` when the worst drawdown starts from the opening value (a fall in the first month).
    """
    n = len(returns)
    if n == 0:
        return Metrics(0, None, None, None, 0.0, None, None, None)
    values = np.asarray(returns, dtype=np.float64)
    annual_return = float(np.prod(1.0 + values) ** (12.0 / n) - 1.0)
    sd = float(np.std(values, ddof=1)) if n > 1 else None
    volatility = None if sd is None else sd * math.sqrt(12.0)
    sharpe = None
    if sd is not None and sd > _FLAT:
        sharpe = float(12.0 * np.mean(values - monthly_rate(risk_free)) / (math.sqrt(12.0) * sd))
    wealth, drawdown = drawdowns(returns)
    worst = int(np.argmax(drawdown))
    if drawdown[worst] <= 0.0:
        return Metrics(n, annual_return, volatility, sharpe, 0.0, None, None, None)
    level = np.concatenate(([1.0], wealth))[: worst + 1]
    peak_index = int(np.argmax(level))  # 0 = before the first month
    peak_value = level[peak_index]
    peak = months[peak_index - 1] if peak_index > 0 else None
    later = np.nonzero(wealth[worst + 1 :] >= peak_value)[0]
    recovery = months[worst + 1 + int(later[0])] if later.size else None
    return Metrics(
        n, annual_return, volatility, sharpe, float(drawdown[worst]), peak, months[worst], recovery
    )


def rolling(returns: Sequence[float], window: int = 12) -> tuple[list[float | None], list[float | None]]:
    """(compounded return, annualised volatility) of each ``window``-month run ending at each month."""
    values = np.asarray(returns, dtype=np.float64)
    compounded: list[float | None] = []
    volatility: list[float | None] = []
    for end in range(len(values)):
        if end + 1 < window:
            compounded.append(None)
            volatility.append(None)
            continue
        run = values[end + 1 - window : end + 1]
        compounded.append(float(np.prod(1.0 + run) - 1.0))
        volatility.append(float(np.std(run, ddof=1) * math.sqrt(12.0)))
    return compounded, volatility


@dataclass(frozen=True)
class BacktestMonth:
    """One month of the back-test: the portfolio's return and the share of today's value it covered."""

    month: dt.date
    portfolio_return: float
    covered_share: float


def backtest(
    weights: Mapping[str, float],
    cash: float,
    total: float,
    returns: Sequence[MonthlyReturn],
    first: dt.date,
    last: dt.date,
    risk_free: float,
) -> list[BacktestMonth]:
    """Today's mix month by month (portfolio-data §16): series weights by today's GBP value, plus cash.

    Each month only the series with a return that month count; they and the cash are rescaled to 100%, and
    cash earns the monthly risk-free rate. ``covered_share`` is the counted value over ``total`` (today's
    household value, unpriced holdings included). A month with nothing counted earns the risk-free rate.
    """
    by_month: dict[dt.date, dict[str, float]] = defaultdict(dict)
    for row in returns:
        if row.return_gbp is not None and row.series in weights:
            by_month[row.month][row.series] = row.return_gbp
    rf = monthly_rate(risk_free)
    months = []
    month = first
    while month <= last:
        available = by_month.get(month, {})
        counted = sum(weights[series] for series in available) + cash
        if counted > 0:
            gain = sum(weights[series] * r for series, r in available.items()) + cash * rf
            portfolio = gain / counted
        else:
            portfolio = rf
        months.append(BacktestMonth(month, portfolio, counted / total if total > 0 else 0.0))
        month = add_months(month, 1)
    return months
