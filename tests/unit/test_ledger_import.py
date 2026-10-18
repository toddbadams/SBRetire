"""F-024.5 — merging monthly export folders and ``sbretire portfolio import`` (synthetic fixtures)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from sbretire.__main__ import main
from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.merge import build_ledger
from sbretire.ledger.model import LEDGER_COLUMNS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
ACCOUNTS_YAML = """\
accounts:
  - {id: brokerage, name: Example brokerage, provider: schwab, owner: person_1, wrapper: taxable,
     currency: USD, transactions: ["schwab*.csv"], holdings: ["positions.csv"]}
  - {id: sipp_2, name: Example SIPP, provider: ii, owner: person_2, wrapper: sipp,
     currency: GBP, transactions: ["ii.csv"], holdings: ["ii_holdings.csv"]}
"""
ACCOUNTS = [
    AccountConfig(
        id="brokerage", name="Example brokerage", provider="schwab", owner="person_1", wrapper="taxable",
        currency="USD", transactions=("schwab*.csv",), holdings=("positions.csv",),
    ),
    AccountConfig(
        id="sipp_2", name="Example SIPP", provider="ii", owner="person_2", wrapper="sipp",
        currency="GBP", transactions=("ii.csv",), holdings=("ii_holdings.csv",),
    ),
]  # fmt: skip
DIVIDEND = b'"10/07/2026","Qualified Dividend"'


def _months(root: Path) -> Path:
    """sep-26 holds the older half of each year-to-date export; oct-26 holds all of it.

    The October Schwab export lists one dividend twice (a true repeat, kept); the September one lists it once.
    """
    schwab = (FIXTURES / "schwab.csv").read_bytes().splitlines(keepends=True)
    ii = (FIXTURES / "ii.csv").read_bytes().splitlines(keepends=True)
    sep, oct_ = root / "sep-26", root / "oct-26"
    sep.mkdir(parents=True)
    oct_.mkdir()
    (root / "notes").mkdir()  # not a month folder: ignored
    (sep / "schwab.csv").write_bytes(b"".join([schwab[0], *schwab[3:]]))  # from the dividend back
    (sep / "ii.csv").write_bytes(b"".join([ii[0], *ii[3:]]))  # the two oldest rows
    repeated = [line for line in schwab if line.startswith(DIVIDEND)]
    (oct_ / "schwab.csv").write_bytes(b"".join([*schwab[:4], *repeated, *schwab[4:]]))
    (oct_ / "ii.csv").write_bytes(b"".join(ii))
    return root


def test_build_ledger_merges_months_without_duplicates(tmp_path: Path) -> None:
    rows = build_ledger(_months(tmp_path / "transactions"), ACCOUNTS)
    brokerage = [row for row in rows if row.account == "brokerage"]
    sipp = [row for row in rows if row.account == "sipp_2"]
    assert len(brokerage) == 11 and len(sipp) == 4
    counts = Counter(row.fingerprint() for row in rows)
    assert sorted(counts.values()) == [1] * 13 + [2]  # only the repeated dividend appears twice
    assert {row.source_file for row in rows} == {"oct-26/schwab.csv", "oct-26/ii.csv"}  # newest folder wins
    dates = [(row.account, row.date) for row in rows]
    assert dates == sorted(dates)


def test_cli_portfolio_import(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _months(tmp_path / "transactions")
    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(ACCOUNTS_YAML, encoding="utf-8")
    out = tmp_path / "out"
    args = ["portfolio", "import", "--root", str(root), "--accounts", str(accounts), "--output-dir", str(out)]
    assert main(args) == 0
    data = (out / "portfolio" / "ledger.csv").read_bytes()
    assert b"\r\n" not in data
    lines = data.decode("utf-8").splitlines()
    assert lines[0] == ",".join(LEDGER_COLUMNS) and len(lines) == 16
    printed = capsys.readouterr().out
    assert (
        "brokerage (Example brokerage, schwab, person_1, taxable, USD): 11 rows, 2026-06-30 to 2026-10-09"
        in printed
    )
    assert (
        "  types: buy 1, corporate_action 2, dividend 2, fee 1, interest 1, sell 1, tax_withheld 1, "
        "transfer_in 1, transfer_out 1" in printed
    )
    assert "  external flows: in 250.00, out 1,000.00 USD" in printed
    assert "  reconciliation: no running balance in the export" in printed
    assert "sipp_2 (Example SIPP, ii, person_2, sipp, GBP): 4 rows, 2026-10-05 to 2026-10-12" in printed
    assert "  external flows: in 100,000.00, out 0.00 GBP" in printed
    assert "  reconciliation: ok (2 files, 6 stated balances)" in printed
    assert f"ledger: {out / 'portfolio' / 'ledger.csv'} (15 rows)" in printed

    october = root / "oct-26" / "ii.csv"
    october.write_bytes(october.read_bytes().replace(b"Total Monthly Fee", b"Something else"))
    assert main(args) == 2
    assert "oct-26/ii.csv row 4: unknown transaction 'Something else'" in capsys.readouterr().err


def test_cli_portfolio_import_reports_reconciliation_break(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _months(tmp_path / "transactions")
    october = root / "oct-26" / "ii.csv"
    october.write_bytes(october.read_bytes().replace("£12.99".encode(), "£12.00".encode()))
    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(ACCOUNTS_YAML, encoding="utf-8")
    out = tmp_path / "out"
    args = ["portfolio", "import", "--root", str(root), "--accounts", str(accounts), "--output-dir", str(out)]
    assert main(args) == 1
    printed = capsys.readouterr().out
    assert (
        "  reconciliation: FAILED sipp_2 (oct-26/ii.csv row 4): ledger cash 99988.00 but the export "
        "states 99987.01" in printed
    )
    assert (out / "portfolio" / "ledger.csv").exists()  # written anyway, for inspection
