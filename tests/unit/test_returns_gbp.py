"""F-026.2 — monthly GBP total returns: closed-form known answers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.prices import MonthEnd, PriceFile, SeriesConfig
from sbretire.ledger.returns import gbp_returns, window

JAN, FEB, MAR, APR = (date(2026, month, 1) for month in (1, 2, 3, 4))


def _file(
    closes: dict[date, float], dividends: dict[date, float] | None = None, basis: str = "dividends"
) -> PriceFile:
    months = [
        MonthEnd(month, close, (dividends or {}).get(month, 0.0)) for month, close in sorted(closes.items())
    ]
    return PriceFile(
        path=Path("x.csv"), basis=basis,  # type: ignore[arg-type]
        months=months, first=months[0].month, last=months[-1].month, rows=len(months), sha256="",
    )  # fmt: skip


def _series(quote: str) -> SeriesConfig:
    return SeriesConfig.model_validate(
        {"id": "s", "name": "S", "file": "x.csv", "quote": quote, "holdings": ["a:S"]}
    )


def _returns(quote: str, prices: PriceFile, fx: PriceFile | None = None) -> list[float | None]:
    return [row.return_gbp for row in gbp_returns(_series(quote), prices, fx, FEB, APR)]


def test_gbp_returns_known_answers() -> None:
    assert window("oct-26", 60) == (date(2021, 10, 1), date(2026, 9, 1))
    assert window("jan-27", 12) == (date(2026, 1, 1), date(2026, 12, 1))

    growth = _file({JAN: 100.0, FEB: 101.0, MAR: 102.01, APR: 103.0301})
    assert _returns("GBP", growth) == [pytest.approx(0.01)] * 3
    rows = gbp_returns(_series("GBP"), growth, None, FEB, APR)
    assert [row.month for row in rows] == [FEB, MAR, APR]
    assert [row.value_gbp for row in rows] == pytest.approx([101.0, 102.01, 103.0301])

    flat = _file({JAN: 100.0, FEB: 100.0, MAR: 100.0, APR: 100.0}, {MAR: 2.0})
    assert _returns("GBP", flat) == [0.0, pytest.approx(0.02), 0.0]  # D / P_{t-1}

    pence = _file(
        {month: 100 * close for month, close in {JAN: 100.0, FEB: 101.0, MAR: 102.01, APR: 103.0301}.items()}
    )
    assert _returns("GBX", pence) == pytest.approx(_returns("GBP", growth))
    assert [row.value_gbp for row in gbp_returns(_series("GBX"), pence, None, FEB, APR)] == pytest.approx(
        [101.0, 102.01, 103.0301]
    )

    rate = _file({JAN: 0.80, FEB: 0.75, MAR: 0.75, APR: 0.78}, basis="price")
    dollars = _file({JAN: 100.0, FEB: 101.0, MAR: 101.0, APR: 101.0})
    assert _returns("USD", dollars, rate) == [
        pytest.approx(1.01 * 0.75 / 0.80 - 1),
        0.0,
        pytest.approx(0.78 / 0.75 - 1),
    ]

    gap = _file({JAN: 100.0, FEB: 101.0, APR: 103.0301})
    assert _returns("GBP", gap) == [pytest.approx(0.01), None, None]  # into and out of the missing month
    assert gbp_returns(_series("GBP"), gap, None, FEB, APR)[1].value_gbp is None

    short_rate = _file({JAN: 0.80, FEB: 0.75, APR: 0.78}, basis="price")
    assert _returns("USD", dollars, short_rate)[1:] == [None, None]

    with pytest.raises(ValueError, match="FX"):
        gbp_returns(_series("USD"), dollars, None, FEB, APR)
