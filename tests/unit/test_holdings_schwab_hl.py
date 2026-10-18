"""F-025.1 — Schwab positions and HL account summary holdings exports (synthetic fixtures)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import HoldingsError, HoldingsExport
from sbretire.ledger.parsers import hl, schwab

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
BROKERAGE = AccountConfig(
    id="brokerage", name="Example brokerage", provider="schwab", owner="person_1", wrapper="taxable",
    currency="USD", transactions=("schwab.csv",), holdings=("schwab-positions.csv",),
)  # fmt: skip
SIPP = AccountConfig(
    id="sipp_1", name="Example SIPP", provider="hl", owner="person_1", wrapper="sipp",
    currency="GBP", transactions=("hl.csv",), holdings=("hl-account-summary.csv",),
)  # fmt: skip


def _rows(export: HoldingsExport) -> list[tuple[object, ...]]:
    return [
        (h.kind, h.security_key, h.security_name, h.quantity, h.price, h.value, h.valuation_date,
         h.date_stated)
        for h in export.holdings
    ]  # fmt: skip


def test_schwab_holdings_parse_and_check_total(tmp_path: Path) -> None:
    export = schwab.parse_holdings(FIXTURES / "schwab-positions.csv", BROKERAGE)
    day = date(2026, 10, 18)
    assert _rows(export) == [
        ("security", "EXA", "EXAMPLE CORP A", 100.0, 50.25, 5025.0, day, True),
        ("security", "EXC", "EXAMPLE CORP C CLASS A", 1200.0, 5.5, 6600.0, day, True),
        ("cash", "", "Cash & Cash Investments", 0.0, None, 1234.56, day, True),
    ]
    assert {(h.account, h.owner, h.wrapper, h.currency) for h in export.holdings} == {
        ("brokerage", "person_1", "taxable", "USD")
    }
    assert [h.source_row for h in export.holdings] == [4, 5, 6]
    assert export.stated_fx is None

    broken = tmp_path / "schwab-positions.csv"
    broken.write_bytes((FIXTURES / "schwab-positions.csv").read_bytes().replace(b"$12,859.56", b"$12,859.50"))
    with pytest.raises(HoldingsError) as caught:
        schwab.parse_holdings(broken, BROKERAGE)
    message = str(caught.value)
    assert "schwab-positions.csv" in message and "12859.56" in message and "12859.50" in message


def test_hl_holdings_parse_and_check_totals(tmp_path: Path) -> None:
    export = hl.parse_holdings(FIXTURES / "hl-account-summary.csv", SIPP)
    day = date(2026, 10, 17)
    assert _rows(export) == [
        ("security", "EXA", "Example Corp, Inc. Com Stk USD0.01", 100.0, 150.0, 15000.0, day, True),
        ("security", "EXG", "Example Global Equity UCITS ETF USD Acc", 1250.0, 6.765432, 8456.79, day, True),
        ("cash", "", "Total cash", 0.0, None, 543.21, day, True),
    ]
    assert [h.source_row for h in export.holdings] == [12, 13, 7]
    assert export.stated_fx is not None
    rate, stated_on = export.stated_fx
    assert rate == pytest.approx(1 / 1.34) and stated_on == date(2026, 10, 16)

    broken = tmp_path / "hl-account-summary.csv"
    text = (FIXTURES / "hl-account-summary.csv").read_bytes()
    broken.write_bytes(text.replace(b'"23,456.79"', b'"23,456.00"'))
    with pytest.raises(HoldingsError) as caught:
        hl.parse_holdings(broken, SIPP)
    message = str(caught.value)
    assert "hl-account-summary.csv" in message and "23456.00" in message and "23456.79" in message
