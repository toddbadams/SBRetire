"""F-024.4 — Vanguard and ii exports, and cash reconciliation (synthetic fixtures)."""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.model import UnknownTransaction
from sbretire.ledger.parsers import ii, vanguard
from sbretire.ledger.reconcile import reconcile_cash

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
FUND = "Example Strategy® 60% Fund - Accumulation"


def _account(id_: str, provider: str, wrapper: str, file: str, filter_: str | None = None) -> AccountConfig:
    return AccountConfig.model_validate(
        {
            "id": id_, "name": id_, "provider": provider, "owner": "person_2", "wrapper": wrapper,
            "currency": "GBP", "transactions": [file], "holdings": ["h.csv"], "filter": filter_,
        }
    )  # fmt: skip


ISA = _account("isa", "vanguard", "isa", "vanguard.csv", "ISA")
PENSION = _account("pension", "vanguard", "pension", "vanguard.csv", "Example Pension")
SIPP = _account("sipp_2", "ii", "sipp", "ii.csv")


def test_vanguard_parser_filters_and_splits_legs() -> None:
    isa = vanguard.parse(FIXTURES / "vanguard.csv", ISA)
    pension = vanguard.parse(FIXTURES / "vanguard.csv", PENSION)
    assert len(isa) == 7 and len(pension) == 5
    assert {row.account for row in isa} == {"isa"} and {row.account for row in pension} == {"pension"}
    assert [row.sequence for row in isa] == list(range(1, 8))  # file is oldest first
    assert [row.type for row in isa] == ["interest", "sell", "sell", "fee", "contribution", "buy", "buy"]
    fee_units, fee_cash = isa[1], isa[2]
    assert (fee_units.security_key, fee_units.quantity_change, fee_units.price) == (FUND, -0.1562, 224.64)
    assert (fee_units.cash_change, fee_units.stated_balance) == (0.0, None)
    assert (fee_cash.security_key, fee_cash.quantity_change, fee_cash.cash_change) == ("", 0.0, 35.10)
    assert fee_cash.stated_balance == 83.17
    bought_units, bought_cash = isa[5], isa[6]
    assert (bought_units.quantity_change, bought_units.cash_change) == (80.0, 0.0)
    assert (bought_cash.quantity_change, bought_cash.cash_change) == (0.0, -20000.0)
    assert isa[4].flow == "external" and isa[4].cash_change == 20000.0
    assert [(row.type, row.flow) for row in pension if row.type != "buy"] == [
        ("contribution", "external"),
        ("tax_relief", "external"),
        ("interest", "none"),
    ]
    assert isa[0].date == date(2026, 1, 1) and isa[0].source_row == 2


def test_vanguard_parser_unknown_type_raises(tmp_path: Path) -> None:
    text = (FIXTURES / "vanguard.csv").read_bytes().replace(b"Account Fee,Account", b"Mystery,Account")
    (tmp_path / "vanguard.csv").write_bytes(text)
    with pytest.raises(UnknownTransaction, match=r"vanguard\.csv row 5: unknown transaction 'Mystery'"):
        vanguard.parse(tmp_path / "vanguard.csv", ISA)


def test_ii_parser_reads_debits_credits_and_transfer_in() -> None:
    rows = ii.parse(FIXTURES / "ii.csv", SIPP)
    got = [
        (r.date, r.settle_date, r.type, r.flow, r.security_key, r.quantity_change, r.price, r.cash_change,
         r.reference, r.stated_balance, r.sequence, r.source_row)
        for r in rows
    ]  # fmt: skip
    assert got == [
        (date(2026, 10, 12), date(2026, 10, 14), "buy", "none", "EXB", 1000.0, 39.5, -39500.0,
         "REF0002", 487.01, 4, 2),
        (date(2026, 10, 12), date(2026, 10, 14), "buy", "none", "EXA", 400.0, 150.0, -60000.0,
         "REF0001", 39987.01, 3, 3),
        (date(2026, 10, 6), date(2026, 10, 6), "fee", "none", "", 0.0, None, -12.99, "", 99987.01, 2, 4),
        (date(2026, 10, 5), date(2026, 10, 5), "transfer_in", "external", "", 0.0, None, 100000.0, "",
         100000.0, 1, 5),
    ]  # fmt: skip
    assert rows[0].security_name == "1000 ISHS V  Del   39.50 S Date 14/10/26"


def test_ii_parser_unknown_description_raises(tmp_path: Path) -> None:
    text = (FIXTURES / "ii.csv").read_bytes().replace(b"Total Monthly Fee", b"Something else")
    (tmp_path / "ii.csv").write_bytes(text)
    with pytest.raises(UnknownTransaction, match=r"ii\.csv row 4: unknown transaction 'Something else'"):
        ii.parse(tmp_path / "ii.csv", SIPP)


def test_reconcile_cash_matches_running_balance() -> None:
    isa = vanguard.parse(FIXTURES / "vanguard.csv", ISA)
    pension = vanguard.parse(FIXTURES / "vanguard.csv", PENSION)
    sipp = ii.parse(FIXTURES / "ii.csv", SIPP)
    assert reconcile_cash(isa + pension + sipp) == []
    broken = [dataclasses.replace(row, cash_change=-12.00) if row.type == "fee" else row for row in sipp]
    assert reconcile_cash(broken) == [
        "sipp_2 (ii.csv row 4): ledger cash 99988.00 but the export states 99987.01"
    ]
