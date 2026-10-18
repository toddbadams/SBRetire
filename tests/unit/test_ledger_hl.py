"""F-024.3 — Hargreaves Lansdown transaction export (synthetic fixture: Windows-1252, preamble, pence)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.model import UnknownTransaction
from sbretire.ledger.parsers import hl

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
ACCOUNT = AccountConfig(
    id="sipp_1", name="Example SIPP", provider="hl", owner="person_1", wrapper="sipp",
    currency="GBP", transactions=("hl.csv",), holdings=("hl-account-summary.csv",),
)  # fmt: skip

# date, settle, type, flow, security_key, quantity_change, price (pounds), cash_change, reference
EXPECTED = [
    (
        date(2026, 10, 16),
        date(2026, 10, 20),
        "buy",
        "none",
        "Example Global Equity UCITS ETF USD Acc",
        1250.0,
        12.345678,
        -15432.10,
        "B111111111",
    ),
    (
        date(2026, 10, 15),
        date(2026, 10, 17),
        "sell",
        "none",
        "Example Corp, Inc. Com Stk USD0.01",
        -40.0,
        250.1,
        10004.00,
        "S222222222",
    ),
    (
        date(2026, 10, 14),
        date(2026, 10, 14),
        "internal_transfer",
        "internal",
        "",
        0.0,
        None,
        120.50,
        "Transfer",
    ),
    (date(2026, 10, 1), date(2026, 10, 1), "interest", "none", "", 0.0, None, 3.21, "INTEREST"),
    (date(2026, 9, 30), date(2026, 9, 30), "fee", "none", "", 0.0, None, -45.00, "MANAGE FEE"),
    (date(2026, 9, 20), date(2026, 9, 20), "transfer_out", "external", "", 0.0, None, -5000.00, "ID TFC"),
    (
        date(2026, 9, 10),
        date(2026, 9, 10),
        "internal_transfer",
        "internal",
        "",
        0.0,
        None,
        -2000.00,
        "TRANSFER",
    ),
    (date(2026, 9, 2), date(2026, 9, 2), "transfer_in", "external", "", 0.0, None, 25000.00, "BACS"),
]


def test_hl_parser_reads_trades_interest_and_transfers() -> None:
    rows = hl.parse(FIXTURES / "hl.csv", ACCOUNT)
    got = [
        (
            r.date,
            r.settle_date,
            r.type,
            r.flow,
            r.security_key,
            r.quantity_change,
            r.price,
            r.cash_change,
            r.reference,
        )
        for r in rows
    ]
    assert got == EXPECTED
    assert {r.currency for r in rows} == {"GBP"} and rows[0].source_row == 7
    assert [r.sequence for r in rows] == list(range(8, 0, -1))  # newest first in the file


def test_hl_parser_rejects_unknown_description(tmp_path: Path) -> None:
    text = (FIXTURES / "hl.csv").read_bytes().decode("cp1252")
    text = text.replace('"INTEREST","Interest From', '"DIVIDEND","Dividend From')
    path = tmp_path / "hl.csv"
    path.write_bytes(text.encode("cp1252"))
    with pytest.raises(UnknownTransaction) as caught:
        hl.parse(path, ACCOUNT)
    assert "hl.csv" in str(caught.value) and "row 10" in str(caught.value) and "DIVIDEND" in str(caught.value)
