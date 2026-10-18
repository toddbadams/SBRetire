"""F-024.2 — ledger rows and the Schwab transaction parser (synthetic fixture with every action)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.model import LEDGER_COLUMNS, UnknownTransaction
from sbretire.ledger.parsers import schwab

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
ACCOUNT = AccountConfig(
    id="brokerage", name="Example US brokerage", provider="schwab", owner="person_1", wrapper="taxable",
    currency="USD", transactions=("schwab.csv",), holdings=("schwab-*.csv",),
)  # fmt: skip

# date, type, flow, security_key, quantity_change, price, cash_change, fees
EXPECTED = [
    (date(2026, 10, 9), "transfer_out", "external", "", 0.0, None, -1000.0, 0.0),
    (date(2026, 10, 8), "sell", "none", "EXA", -20.0, 100.5, 2009.88, 0.12),
    (date(2026, 10, 7), "dividend", "none", "EXB", 0.0, None, 85.0, 0.0),
    (date(2026, 9, 20), "transfer_in", "external", "", 0.0, None, 250.0, 0.0),
    (date(2026, 9, 2), "buy", "none", "EXC", 1200.0, 5.125, -6150.0, 0.0),
    (date(2026, 8, 15), "corporate_action", "none", "123456789", 0.0, None, 3000.0, 0.0),
    (date(2026, 8, 15), "corporate_action", "none", "123456789", -100.0, None, 0.0, 0.0),
    (date(2026, 7, 1), "fee", "none", "EXD", 0.0, None, -1.5, 0.0),
    (date(2026, 7, 1), "tax_withheld", "none", "EXD", 0.0, None, -12.34, 0.0),
    (date(2026, 6, 30), "interest", "none", "", 0.0, None, 1.23, 0.0),
]


def test_schwab_parser_maps_every_action() -> None:
    rows = schwab.parse(FIXTURES / "schwab.csv", ACCOUNT)
    got = [
        (r.date, r.type, r.flow, r.security_key, r.quantity_change, r.price, r.cash_change, r.fees)
        for r in rows
    ]
    assert got == EXPECTED
    assert {(r.account, r.owner, r.wrapper, r.currency) for r in rows} == {
        ("brokerage", "person_1", "taxable", "USD")
    }
    assert [r.source_row for r in rows] == list(range(2, 12))  # file line numbers
    assert rows[1].security_name == "EXAMPLE CORP A" and rows[0].source_file == "schwab.csv"
    # newest first in the file, so the chronological sequence runs the other way
    assert [r.sequence for r in rows] == list(range(10, 0, -1))
    assert set(LEDGER_COLUMNS) >= {"account", "type", "flow", "quantity_change", "cash_change", "source_row"}
    assert len({r.fingerprint() for r in rows}) == len(rows)


def test_schwab_parser_rejects_unknown_action(tmp_path: Path) -> None:
    text = (FIXTURES / "schwab.csv").read_text(encoding="utf-8").replace('"Credit Interest"', '"Bond Coupon"')
    path = tmp_path / "schwab.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(UnknownTransaction) as caught:
        schwab.parse(path, ACCOUNT)
    message = str(caught.value)
    assert "schwab.csv" in message and "row 11" in message and "Bond Coupon" in message
