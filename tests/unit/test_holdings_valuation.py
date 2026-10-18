"""F-025.3 — valuing the newest month folder and ``sbretire portfolio value`` (synthetic fixtures)."""

from __future__ import annotations

import dataclasses
import shutil
from datetime import date
from pathlib import Path

import pytest

from sbretire.__main__ import main
from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import HOLDING_COLUMNS, HoldingsError
from sbretire.ledger.valuation import ValuationError, read_holdings, value_holdings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "accounts"
ACCOUNTS_YAML = """\
accounts:
  - {id: brokerage, name: Example brokerage, provider: schwab, owner: person_1, wrapper: taxable,
     currency: USD, transactions: ["schwab.csv"], holdings: ["schwab-positions*.csv"]}
  - {id: sipp_1, name: Example SIPP 1, provider: hl, owner: person_1, wrapper: sipp,
     currency: GBP, transactions: ["hl.csv"], holdings: ["hl-account-summary.csv"]}
  - {id: isa, name: Example ISA, provider: vanguard, owner: person_2, wrapper: isa,
     currency: GBP, transactions: ["vanguard_isa.csv"], holdings: ["vanguard-holdings*.csv"],
     holdings_filter: "Stocks & Shares ISA"}
  - {id: pension, name: Example pension, provider: vanguard, owner: person_2, wrapper: pension,
     currency: GBP, transactions: ["vanguard_pension.csv"], holdings: ["vanguard-holdings*.csv"],
     holdings_filter: "Personal Pension"}
  - {id: sipp_2, name: Example SIPP 2, provider: ii, owner: person_2, wrapper: sipp,
     currency: GBP, transactions: ["ii.csv"], holdings: ["ii_holdings.csv"]}
"""
FILES = (
    "schwab-positions.csv",
    "hl-account-summary.csv",
    "vanguard-holdings.csv.csv",
    "ii_holdings.csv",
    "ii.csv",
)


def _accounts(tmp_path: Path) -> list[AccountConfig]:
    from sbretire.ledger.accounts import load_accounts

    path = tmp_path / "accounts.yaml"
    path.write_text(ACCOUNTS_YAML, encoding="utf-8")
    return load_accounts(path)


def _months(root: Path) -> Path:
    """oct-26 holds every holdings export; sep-26 holds a Schwab export that would fail its check if read."""
    oct_, sep = root / "oct-26", root / "sep-26"
    oct_.mkdir(parents=True)
    sep.mkdir()
    for name in FILES:
        shutil.copy(FIXTURES / name, oct_ / name)
    broken = (FIXTURES / "schwab-positions.csv").read_bytes().replace(b"$12,859.56", b"$1.00")
    (sep / "schwab-positions.csv").write_bytes(broken)
    return root


def test_value_holdings_totals_dates_and_fx(tmp_path: Path) -> None:
    accounts = _accounts(tmp_path)
    folder, exports = read_holdings(_months(tmp_path / "transactions"), accounts)
    assert folder == "oct-26"
    valuation = value_holdings(folder, exports, usd_gbp=0.75)

    by_account = valuation.by_account()
    expected = {
        "brokerage": (8718.75, 925.92),  # USD 11,625.00 and 1,234.56 at 0.75
        "sipp_1": (23456.79, 543.21),
        "isa": (20800.00, 0.00),
        "pension": (4210.90, 1000.03),
        "sipp_2": (100123.00, 487.01),  # cash: ii's newest stated running balance
    }
    assert by_account.keys() == expected.keys()
    for account, (securities, cash) in expected.items():
        assert by_account[account] == (pytest.approx(securities), pytest.approx(cash))
    assert valuation.by_owner() == {"person_1": pytest.approx(33644.67), "person_2": pytest.approx(126620.94)}
    assert valuation.total_gbp() == pytest.approx(160265.61)

    ii_rows = [h for h in valuation.holdings if h.account == "sipp_2"]
    assert {(h.valuation_date, h.date_stated) for h in ii_rows} == {(date(2026, 10, 18), False)}
    isa_files = {h.source_file for h in valuation.holdings if h.account == "isa"}
    assert isa_files == {"oct-26/vanguard-holdings.csv.csv"}
    assert valuation.warnings == []  # HL states 1.34 USD per pound (0.7463), within 2% of 0.75
    hl_rate = ("oct-26/hl-account-summary.csv", pytest.approx(1 / 1.34), date(2026, 10, 16))
    assert valuation.stated_fx == [hl_rate]

    assert any("2%" in warning for warning in value_holdings(folder, exports, usd_gbp=0.80).warnings)
    early = [
        dataclasses.replace(
            export,
            holdings=[
                dataclasses.replace(h, valuation_date=date(2026, 10, 1)) if h.account == "isa" else h
                for h in export.holdings
            ],
        )
        for export in exports
    ]
    spread = value_holdings(folder, early, usd_gbp=0.75).warnings
    assert any("2026-10-01" in warning and "2026-10-18" in warning for warning in spread)

    with pytest.raises(ValuationError, match="--usd-gbp"):
        value_holdings(folder, exports, usd_gbp=None)


def test_read_holdings_refuses_a_shared_file_without_filters(tmp_path: Path) -> None:
    root = _months(tmp_path / "transactions")
    accounts = [
        a.model_copy(update={"holdings_filter": None}) if a.id == "isa" else a for a in _accounts(tmp_path)
    ]
    with pytest.raises(HoldingsError, match="holdings_filter"):
        read_holdings(root, accounts)


def test_cli_portfolio_value(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _months(tmp_path / "transactions")
    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(ACCOUNTS_YAML, encoding="utf-8")
    out = tmp_path / "out"
    base = ["portfolio", "value", "--root", str(root), "--accounts", str(accounts), "--output-dir", str(out)]
    assert main([*base, "--usd-gbp", "0.75"]) == 0
    printed = capsys.readouterr().out
    assert "Valuation of oct-26 at 0.7500 GBP per USD (--usd-gbp)" in printed
    assert "oct-26/hl-account-summary.csv states 0.7463 GBP per USD on 2026-10-16" in printed
    assert "brokerage" in printed and "2026-10-18" in printed and "9,644.67" in printed
    assert "sipp_2" in printed and "2026-10-18 (assumed)" in printed and "100,610.01" in printed
    assert "person_1: £33,644.67" in printed and "person_2: £126,620.94" in printed
    assert "Household total: £160,265.61" in printed
    pasted = (
        "portfolio:\n  starting_balance: 160266  # sbretire portfolio value: oct-26, 2026-10-17 to 2026-10-18"
    )
    assert pasted in printed
    data = (out / "portfolio" / "holdings.csv").read_bytes()
    assert b"\r\n" not in data
    lines = data.decode("utf-8").splitlines()
    assert lines[0] == ",".join((*HOLDING_COLUMNS, "fx_rate", "value_gbp"))
    assert len(lines) == 1 + 3 + 3 + 2 + 2 + 3

    assert main(base) == 2
    assert "--usd-gbp" in capsys.readouterr().err
    (root / "oct-26" / "ii_holdings.csv").unlink()
    assert main([*base, "--usd-gbp", "0.75"]) == 2
    assert "no holdings export for sipp_2 in oct-26" in capsys.readouterr().err
