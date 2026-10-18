"""Performance and drawdown of today's portfolio mix over past prices (F-027; portfolio-data §15–§17).

Returns are monthly and in GBP. Annual figures: return compounds the months (``Π(1 + r)^(12/n) − 1``),
volatility is the sample standard deviation × √12, Sharpe is ``12 × mean(r − r_f) / (√12 × sd)`` with ``r_f``
the monthly risk-free rate.
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray

from sbretire.ledger.returns import MonthlyReturn, ReturnsReport, add_months

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


MIN_MONTHS_FOR_RISK: Final = 12
"""A series needs this many monthly returns for its volatility and Sharpe to be shown."""


@dataclass(frozen=True)
class SeriesPerformance:
    series: str
    name: str
    weight: float
    """Share of today's household value."""
    metrics: Metrics


@dataclass(frozen=True)
class Performance:
    """Everything ``sbretire portfolio performance`` prints and writes."""

    report: ReturnsReport
    risk_free: float
    risk_free_source: str
    months: list[BacktestMonth]
    metrics: Metrics
    wealth: list[float]
    drawdown: list[float]
    rolling_return: list[float | None]
    rolling_volatility: list[float | None]
    series: list[SeriesPerformance]


def build_performance(report: ReturnsReport, risk_free: float, source: str) -> Performance:
    """Back-test today's mix (portfolio-data §16) and measure it and each series (§15, §17)."""
    months = backtest(
        report.series_values,
        report.cash_gbp,
        report.total_gbp,
        report.returns,
        report.first,
        report.last,
        risk_free,
    )
    dates = [m.month for m in months]
    values = [m.portfolio_return for m in months]
    wealth, drawdown = drawdowns(values)
    rolling_return, rolling_volatility = rolling(values)
    series = []
    for series_id, value in report.series_values.items():
        rows = [r for r in report.returns if r.series == series_id and r.return_gbp is not None]
        found = metrics(
            [r.month for r in rows], [r.return_gbp for r in rows if r.return_gbp is not None], risk_free
        )
        if found.months < MIN_MONTHS_FOR_RISK:
            found = dataclasses.replace(found, annual_volatility=None, sharpe=None)
        weight = value / report.total_gbp if report.total_gbp else 0.0
        series.append(
            SeriesPerformance(series_id, report.series_names.get(series_id, series_id), weight, found)
        )
    return Performance(
        report, risk_free, source, months, metrics(dates, values, risk_free),
        wealth.tolist(), drawdown.tolist(), rolling_return, rolling_volatility, series,
    )  # fmt: skip


PERFORMANCE_COLUMNS: Final = (
    "month", "portfolio_return", "wealth_index", "drawdown", "covered_share",
    "rolling_12m_return", "rolling_12m_volatility",
)  # fmt: skip
SERIES_COLUMNS: Final = (
    "series", "name", "weight", "months", "annual_return", "annual_volatility", "sharpe", "max_drawdown",
)  # fmt: skip


def _cell(value: float | None) -> str | float:
    return "" if value is None else value


def write_performance_csvs(performance: Performance, folder: Path) -> None:
    """``performance.csv`` (one row per month) and ``performance_series.csv`` (one per series); UTF-8, LF."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "performance.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(PERFORMANCE_COLUMNS)
        for i, month in enumerate(performance.months):
            writer.writerow((
                f"{month.month:%Y-%m}", month.portfolio_return, performance.wealth[i],
                performance.drawdown[i], month.covered_share, _cell(performance.rolling_return[i]),
                _cell(performance.rolling_volatility[i]),
            ))  # fmt: skip
    with (folder / "performance_series.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SERIES_COLUMNS)
        for item in performance.series:
            m = item.metrics
            writer.writerow((
                item.series, item.name, item.weight, m.months, _cell(m.annual_return),
                _cell(m.annual_volatility), _cell(m.sharpe), m.max_drawdown,
            ))  # fmt: skip


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2%}"


def _month(value: dt.date | None) -> str:
    return "-" if value is None else f"{value:%Y-%m}"


def format_performance(performance: Performance) -> str:
    """The summary: headline metrics, the worst drawdown, coverage and the per-series table."""
    report, m = performance.report, performance.metrics
    lines = [
        f"Back-test of today's mix, {report.first:%Y-%m} to {report.last:%Y-%m} "
        f"({len(performance.months)} months), risk-free {performance.risk_free:.2%} a year "
        f"({performance.risk_free_source})",
        "  Historical, not a forecast or advice: today's weights applied to past monthly returns.",
        f"  Annual return       {_pct(m.annual_return)}",
        f"  Annual volatility   {_pct(m.annual_volatility)}",
        f"  Sharpe ratio        {'n/a' if m.sharpe is None else f'{m.sharpe:.2f}'}",
    ]
    if m.max_drawdown > 0:
        recovered = f"recovered {_month(m.recovery)}" if m.recovery else "not recovered"
        lines.append(
            f"  Max drawdown        {m.max_drawdown:.2%}  peak {_month(m.peak)}, "
            f"trough {_month(m.trough)}, {recovered}"
        )
    else:
        lines.append("  Max drawdown        none")
    covered = [month.covered_share for month in performance.months]
    if covered:
        low = min(performance.months, key=lambda month: month.covered_share)
        cash = report.cash_gbp / report.total_gbp if report.total_gbp else 0.0
        lines.append(
            f"  Covered             average {sum(covered) / len(covered):.1%} of today's value "
            f"(lowest {low.covered_share:.1%} in {low.month:%Y-%m}); cash {cash:.1%} at the risk-free rate"
        )
    if not performance.series:
        lines.append("  No priced holdings yet: the back-test is all cash at the risk-free rate.")
    else:
        lines.append(
            "  {:<24} {:>7} {:>6} {:>8} {:>10} {:>6} {:>8}".format(
                "series", "weight", "months", "return", "volatility", "sharpe", "max dd"
            )
        )
        for item in performance.series:
            s = item.metrics
            sharpe = "n/a" if s.sharpe is None else f"{s.sharpe:.2f}"
            lines.append(
                f"  {item.series[:24]:<24} {item.weight:>7.1%} {s.months:>6} {_pct(s.annual_return):>8} "
                f"{_pct(s.annual_volatility):>10} {sharpe:>6} {s.max_drawdown:>8.1%}"
            )
    lines += [f"warning: {warning}" for warning in report.warnings]
    return "\n".join(lines)
