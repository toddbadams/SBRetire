"""F-025.2 — Vanguard shared holdings file; ii holdings with cash from the ledger (synthetic fixtures)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import HoldingsError, HoldingsExport
from sbretire.ledger.parsers import ii, vanguard

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"


def _account(id_: str, provider: str, wrapper: str, holdings_filter: str | None = None) -> AccountConfig:
    return AccountConfig.model_validate(
        {
            "id": id_, "name": id_, "provider": provider, "owner": "person_2", "wrapper": wrapper,
            "currency": "GBP", "transactions": ["t.csv"], "holdings": ["h.csv"],
            "holdings_filter": holdings_filter,
        }
    )  # fmt: skip


ISA = _account("isa", "vanguard", "isa", "Stocks & Shares ISA")
PENSION = _account("pension", "vanguard", "pension", "Personal Pension")
SIPP = _account("sipp_2", "ii", "sipp")


def _rows(export: HoldingsExport) -> list[tuple[object, ...]]:
    return [
        (h.account, h.kind, h.security_key, h.quantity, h.price, h.value, h.valuation_date, h.date_stated)
        for h in export.holdings
    ]


def test_vanguard_holdings_filter_by_wrapper() -> None:
    path = FIXTURES / "vanguard-holdings.csv.csv"
    day = date(2026, 10, 17)
    fund = "Example Strategy® 60% Fund - Accumulation"
    assert _rows(vanguard.parse_holdings(path, ISA)) == [
        ("isa", "cash", "", 0.0, None, 0.0, day, True),
        ("isa", "security", fund, 80.0, 260.0, 20800.0, day, True),
    ]
    pension = vanguard.parse_holdings(path, PENSION)
    assert _rows(pension) == [
        ("pension", "cash", "", 0.0, None, 1000.03, day, True),
        ("pension", "security", "Example Target 2035 Fund - Accumulation", 17.5454, 240.0, 4210.9, day, True),
    ]
    assert [h.source_row for h in pension.holdings] == [2, 3]
    assert pension.holdings[0].security_name == "GBP Cash"


def test_ii_holdings_values_in_gbp_and_cash_from_ledger() -> None:
    export = ii.parse_holdings(FIXTURES / "ii_holdings.csv", SIPP)
    assert _rows(export) == [
        ("sipp_2", "security", "EXA", 400.0, 150.0, 60000.0, None, False),
        ("sipp_2", "security", "EXB", 1000.0, 40.123, 40123.0, None, False),
    ]
    assert export.holdings[0].security_name == "Example World Momentum ETF $ Acc"

    cash = ii.cash_from_transactions(ii.parse(FIXTURES / "ii.csv", SIPP), SIPP)
    assert (cash.kind, cash.value, cash.valuation_date, cash.date_stated) == ("cash", 487.01, None, False)
    assert (cash.source_file, cash.source_row) == ("ii.csv", 2)  # the newest stated running balance

    with pytest.raises(HoldingsError, match="no running balance"):
        ii.cash_from_transactions([], SIPP, FIXTURES / "ii.csv")
