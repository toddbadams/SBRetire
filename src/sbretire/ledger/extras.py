"""Extras for the Portfolio page: drawdown episodes, a returns calendar, risk and income (F-030; §25).

Pure functions over the back-test, the frontier estimates and the ledger; all money in GBP.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray

from sbretire.ledger.model import LedgerRow
from sbretire.ledger.returns import add_months

_INCOME: Final = {"dividend": "dividends_gbp", "interest": "interest_gbp", "fee": "fees_gbp",
                  "tax_withheld": "tax_withheld_gbp"}  # fmt: skip


def _ym(month: dt.date | None) -> str | None:
    return None if month is None else f"{month:%Y-%m}"


def drawdown_episodes(
    months: Sequence[dt.date], returns: Sequence[float], top: int = 5
) -> list[dict[str, object]]:
    """The ``top`` deepest non-overlapping falls of the wealth index (1 before month one), deepest first.

    Each: ``peak`` (``None`` = the opening value), ``trough``, ``recovery`` (first month back at the peak, or
    ``None``), ``depth`` (a fraction), ``months_to_trough`` and ``months_to_recover``.
    """
    wealth = np.cumprod(1.0 + np.asarray(returns, dtype=np.float64))
    episodes: list[dict[str, object]] = []
    peak_level, peak_index = 1.0, -1
    trough_level, trough_index = 1.0, -1
    in_fall = False
    for i, level in enumerate(wealth):
        if level >= peak_level:
            if in_fall:
                episodes.append(_episode(months, peak_index, trough_index, i, 1 - trough_level / peak_level))
                in_fall = False
            peak_level, peak_index = float(level), i
        else:
            if not in_fall or level < trough_level:
                trough_level, trough_index = float(level), i
            in_fall = True
    if in_fall:
        episodes.append(_episode(months, peak_index, trough_index, None, 1 - trough_level / peak_level))
    episodes.sort(key=lambda e: -float(e["depth"]))  # type: ignore[arg-type]
    return episodes[:top]


def _episode(
    months: Sequence[dt.date], peak: int, trough: int, recovery: int | None, depth: float
) -> dict[str, object]:
    return {
        "peak": _ym(months[peak]) if peak >= 0 else None,
        "trough": _ym(months[trough]),
        "recovery": _ym(months[recovery]) if recovery is not None else None,
        "depth": depth,
        "months_to_trough": trough - peak,
        "months_to_recover": None if recovery is None else recovery - trough,
    }


def calendar(months: Sequence[dt.date], returns: Sequence[float]) -> list[dict[str, object]]:
    """Years × months of monthly returns (``None`` outside the series) and each year's compounded total."""
    by_year: dict[int, list[float | None]] = {}
    for month, value in zip(months, returns, strict=True):
        by_year.setdefault(month.year, [None] * 12)[month.month - 1] = value
    return [
        {"year": year, "months": values,
         "total": float(np.prod([1.0 + v for v in values if v is not None]) - 1.0)}
        for year, values in sorted(by_year.items())
    ]  # fmt: skip


def correlation(cov: NDArray[np.float64]) -> NDArray[np.float64]:
    """The correlation matrix of a covariance matrix."""
    sd = np.sqrt(np.diag(cov))
    return np.asarray(cov / np.outer(sd, sd), dtype=np.float64)


def risk_contribution(weights: NDArray[np.float64], cov: NDArray[np.float64]) -> NDArray[np.float64]:
    """Each holding's share of the mix's variance, ``wᵢ(Σw)ᵢ / wᵀΣw``; the shares sum to 1."""
    w = np.asarray(weights, dtype=np.float64)
    marginal = cov @ w
    return np.asarray(w * marginal / float(w @ marginal), dtype=np.float64)


def income_by_month(
    rows: Sequence[LedgerRow], first: dt.date, last: dt.date, usd_gbp: float | None
) -> list[dict[str, object]]:
    """Dividends, interest, fees and tax withheld per month from ``first`` to ``last`` (first days), in GBP.

    Signed as in the ledger (fees and tax withheld negative); USD rows convert at ``usd_gbp``; other rows and
    other currencies are ignored.
    """
    months: dict[dt.date, dict[str, object]] = {}
    month = first
    while month <= last:
        months[month] = {"month": _ym(month), **{key: 0.0 for key in _INCOME.values()}}
        month = add_months(month, 1)
    for row in rows:
        key = _INCOME.get(row.type)
        start = row.date.replace(day=1)
        if key is None or start not in months:
            continue
        rate = 1.0 if row.currency == "GBP" else usd_gbp if row.currency == "USD" else None
        if rate is None:
            continue
        months[start][key] = float(months[start][key]) + row.cash_change * rate  # type: ignore[arg-type]
    return list(months.values())
