"""Monthly GBP total returns from price series (F-026)."""

from __future__ import annotations

import datetime as dt

from sbretire.ledger.prices import PriceFile, SeriesConfig


def window(folder: str, months: int) -> tuple[dt.date, dt.date]:
    raise NotImplementedError


def gbp_returns(
    series: SeriesConfig, prices: PriceFile, fx: PriceFile | None, first: dt.date, last: dt.date
) -> list[object]:
    raise NotImplementedError
