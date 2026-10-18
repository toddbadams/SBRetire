"""Monthly GBP total returns from price series (F-026; portfolio-data §12–§13).

A month's return is ``(P_t + D_t) × X_t / (P_{t-1} × X_{t-1}) − 1``: ``P`` the month-end price in pounds
or dollars (GBX ÷ 100), ``D`` the dividends paid in the month, ``X`` GBP per unit of the quote currency at
month-end.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Final

from sbretire.ledger.prices import PriceFile, SeriesConfig

_MONTHS: Final = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


@dataclass(frozen=True)
class MonthlyReturn:
    """One series' month in GBP: value per unit, dividends and total return (``None`` when unknown)."""

    month: dt.date
    series: str
    value_gbp: float | None
    dividend_gbp: float
    return_gbp: float | None
    basis: str


def add_months(month: dt.date, count: int) -> dt.date:
    """The first day of the month ``count`` months after ``month`` (negative goes back)."""
    index = month.year * 12 + month.month - 1 + count
    return dt.date(index // 12, index % 12 + 1, 1)


def window(folder: str, months: int) -> tuple[dt.date, dt.date]:
    """(first, last) return month: ``months`` months ending the month before the folder's ``<mon>-<yy>``."""
    name, _, year = folder.partition("-")
    if name not in _MONTHS or not year.isdigit() or months < 1:
        raise ValueError(
            f"expected a <mon>-<yy> folder and a positive month count (got {folder!r}, {months})"
        )
    last = add_months(dt.date(2000 + int(year), _MONTHS.index(name) + 1, 1), -1)
    return add_months(last, -(months - 1)), last


def gbp_returns(
    series: SeriesConfig, prices: PriceFile, fx: PriceFile | None, first: dt.date, last: dt.date
) -> list[MonthlyReturn]:
    """One row per month from ``first`` to ``last``; months without a price (or rate) have no value or return.

    Raises ``ValueError`` when a USD series has no FX file.
    """
    if series.quote == "USD" and fx is None:
        raise ValueError(f"series {series.id!r} is quoted in USD but no FX file gives GBP per USD")
    unit = 0.01 if series.quote == "GBX" else 1.0
    closes = {m.month: m for m in prices.months}
    rates = {m.month: m.close for m in fx.months} if series.quote == "USD" and fx is not None else None

    def rate(month: dt.date) -> float | None:
        return 1.0 if rates is None else rates.get(month)

    def value(month: dt.date) -> float | None:
        found, x = closes.get(month), rate(month)
        return None if found is None or x is None else found.close * unit * x

    rows = []
    month = first
    while month <= last:
        found, x = closes.get(month), rate(month)
        dividend = 0.0 if found is None or x is None else found.dividend * unit * x
        now, before = value(month), value(add_months(month, -1))
        total = None if now is None or before is None else (now + dividend) / before - 1
        rows.append(MonthlyReturn(month, series.id, now, dividend, total, prices.basis))
        month = add_months(month, 1)
    return rows


def build_returns(*args: object, **kwargs: object) -> object:
    raise NotImplementedError
