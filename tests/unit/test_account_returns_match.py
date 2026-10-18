"""F-031.1 — matching ledger securities to price series: by key, by normalised name, by ledger_names."""

from __future__ import annotations

from datetime import date

from sbretire.ledger.account_returns import match_securities, normalise_name
from sbretire.ledger.holdings import Holding
from sbretire.ledger.model import LedgerRow
from sbretire.ledger.prices import SecuritiesConfig


def _row(account: str, key: str) -> LedgerRow:
    return LedgerRow(
        account=account, owner="p", wrapper="isa", date=date(2026, 3, 1), settle_date=None, type="buy",
        flow="none", security_key=key, security_name=key, quantity_change=1.0, price=1.0, cash_change=-1.0,
        fees=0.0, currency="GBP", reference="", source_file="f.csv", source_row=2, sequence=1,
    )  # fmt: skip


def _holding(account: str, key: str, name: str) -> Holding:
    return Holding(
        account=account, owner="p", wrapper="isa", valuation_date=date(2026, 10, 17), date_stated=True,
        kind="security", security_key=key, security_name=name, quantity=1.0, price=1.0, value=1.0,
        currency="GBP", source_file="h.csv", source_row=2,
    )  # fmt: skip


SECURITIES = SecuritiesConfig.model_validate(
    {
        "securities": [
            {"id": "corp", "name": "Corp", "file": "c.csv", "quote": "USD", "holdings": ["brokerage:EXA"]},
            {"id": "global", "name": "Global", "file": "g.csv", "quote": "GBX", "holdings": ["sipp_1:EXG"]},
            {"id": "japan", "name": "Japan", "file": "j.csv", "quote": "GBP",
             "holdings": ["isa:Vanguard Japan Stock Ind"],
             "ledger_names": ["Vanguard Japan Stock Index Fund - Accumulation"]},
            {"id": "old", "name": "Old", "file": "o.csv", "quote": "GBP", "holdings": ["sipp_1:OLD"],
             "ledger_names": ["Old Example plc Ord 1p"]},
        ]
    }
)  # fmt: skip


def test_match_securities() -> None:
    assert normalise_name("Example Global Equity UCITS ETF USD Acc") == "example global equity ucits etf"
    assert normalise_name("Example Global Equity UCITS ETF - USD") == "example global equity ucits etf"
    assert normalise_name("Example Corp, Inc. Com Stk") == "example corp inc com stk"

    rows = [
        _row("brokerage", "EXA"),  # by key
        _row("sipp_1", "Example Global Equity UCITS ETF USD Acc"),  # by normalised name
        _row("isa", "Vanguard Japan Stock Index Fund - Accumulation"),  # by ledger_names (holding truncated)
        _row("sipp_1", "Old Example plc Ord 1p"),  # sold out: by ledger_names, no holding today
        _row("sipp_1", "MYSTERY"),  # unknown
    ]
    holdings = [
        _holding("brokerage", "EXA", "EXAMPLE CORP A"),
        _holding("sipp_1", "EXG", "Example Global Equity UCITS ETF USD"),
        _holding("isa", "Vanguard Japan Stock Ind", "Vanguard Japan Stock Ind"),
    ]
    matched, unmatched = match_securities(rows, holdings, SECURITIES)
    assert matched == {
        ("brokerage", "EXA"): "corp",
        ("sipp_1", "Example Global Equity UCITS ETF USD Acc"): "global",
        ("isa", "Vanguard Japan Stock Index Fund - Accumulation"): "japan",
        ("sipp_1", "Old Example plc Ord 1p"): "old",
    }
    assert unmatched == [("sipp_1", "MYSTERY")]
