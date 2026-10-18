"""F-031.2 — month-end units, cash and values rebuilt backwards from today's holdings (known answers)."""

from __future__ import annotations

from datetime import date

import pytest

from sbretire.ledger.account_returns import cash_at, price_in, rebuild, units_at
from sbretire.ledger.model import Flow, LedgerRow, TransactionType

JAN, FEB, MAR = date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)


def _row(
    day: date, kind: TransactionType, key: str, qty: float, cash: float, flow: Flow = "none"
) -> LedgerRow:
    return LedgerRow(
        account="a", owner="p", wrapper="isa", date=day, settle_date=None, type=kind, flow=flow,
        security_key=key, security_name=key, quantity_change=qty, price=None, cash_change=cash, fees=0.0,
        currency="GBP", reference="", source_file="f.csv", source_row=2, sequence=1,
    )  # fmt: skip


ROWS = [
    _row(date(2026, 1, 15), "buy", "S", 10.0, -100.0),  # before the January month-end: already in
    _row(date(2026, 2, 3), "contribution", "", 0.0, 1000.0, "external"),
    _row(date(2026, 2, 10), "buy", "S", 40.0, -400.0),
    _row(date(2026, 2, 20), "fee", "", 0.0, -5.0),
]
MATCHED = {("a", "S"): "s"}


def test_rebuild_month_end_values() -> None:
    # today: 100 units of s and £50 cash; the three February rows are undone for the January month-end
    assert units_at(ROWS, MATCHED, {"s": 100.0}, JAN) == {"s": 60.0}
    assert units_at(ROWS, MATCHED, {"s": 100.0}, FEB) == {"s": 100.0}
    assert cash_at(ROWS, 50.0, JAN) == pytest.approx(50.0 + 400.0 + 5.0 - 1000.0)
    assert cash_at(ROWS, 50.0, FEB) == pytest.approx(50.0)

    assert price_in("GBP", "GBX", 250.0, 0.8) == pytest.approx(2.5)
    assert price_in("GBP", "USD", 10.0, 0.8) == pytest.approx(8.0)
    assert price_in("USD", "USD", 10.0, 0.8) == pytest.approx(10.0)
    assert price_in("USD", "GBP", 8.0, 0.8) == pytest.approx(10.0)

    closes = {"s": {JAN: 9.0, FEB: 11.0}}
    values, missing = rebuild(ROWS, MATCHED, {"s": 100.0}, 50.0, [JAN, FEB], closes, {"s": "GBP"}, "GBP", {})
    assert missing == []
    assert [month for month, _ in values] == [JAN, FEB]
    assert [value for _, value in values] == pytest.approx(
        [60 * 9.0 + (50.0 + 405.0 - 1000.0), 100 * 11.0 + 50.0]
    )

    _, missing = rebuild(ROWS, MATCHED, {"s": 100.0}, 50.0, [JAN, FEB, MAR], closes, {"s": "GBP"}, "GBP", {})
    assert missing == ["s (2026-03)"]  # held in March but no March price

    unknown = [*ROWS, _row(date(2026, 1, 5), "buy", "X", 5.0, -50.0)]
    _, missing = rebuild(unknown, MATCHED, {"s": 100.0}, 50.0, [JAN, FEB], closes, {"s": "GBP"}, "GBP", {})
    assert missing == ["X (no price series matched)"]

    usd = rebuild(
        ROWS, MATCHED, {"s": 100.0}, 50.0, [JAN, FEB], closes, {"s": "USD"}, "GBP", {JAN: 0.8, FEB: 0.75}
    )
    assert usd[0][1][1] == pytest.approx(100 * 11.0 * 0.75 + 50.0)
    assert rebuild(ROWS, MATCHED, {"s": 100.0}, 50.0, [JAN], closes, {"s": "USD"}, "GBP", {})[1] == [
        "s (2026-01: no USD rate)"
    ]
