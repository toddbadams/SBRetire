"""F-031.4 — ``sbretire portfolio account-returns``, account_returns.csv and portfolio.json 1.1."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import jsonschema
import pytest
from test_portfolio_document import full_setup

from sbretire.__main__ import main
from sbretire.ledger.accounts import load_accounts
from sbretire.ledger.document import ReportOptions, build_portfolio_document

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "portfolio.schema.json").read_text(encoding="utf-8"))


def test_cli_account_returns_and_document(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts, factsheets = full_setup(tmp_path)
    out = tmp_path / "out"
    args = ["portfolio", "account-returns", "--root", str(root), "--accounts", str(accounts),
            "--prices", str(prices), "--output-dir", str(out)]  # fmt: skip
    assert main(args) == 0
    printed = capsys.readouterr().out
    assert "Account returns from" in printed and "time-weighted" in printed and "money-weighted" in printed
    # sipp_1 (EXA via example_corp, EXG via global_equity) and isa (strategy) are fully priced
    for available in ("sipp_1", "isa"):
        assert f"  {available} " in printed
    # brokerage holds EXC, pension its target fund and sipp_2 EXB: none has a price series
    assert "brokerage: EXC" in printed or "brokerage:" in printed
    assert "unavailable" in printed and "household" in printed

    data = (out / "portfolio" / "account_returns.csv").read_bytes()
    assert b"\r\n" not in data
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    assert list(rows[0]) == ["account", "date", "value", "external_flow", "return"]
    sipp = [r for r in rows if r["account"] == "sipp_1"]
    assert len(sipp) >= 2 and float(sipp[-1]["value"]) == pytest.approx(24000.00)  # today's HL value

    document = build_portfolio_document(
        ReportOptions(root=root, prices=prices, factsheets=factsheets, months=24, min_trade=1.0),
        load_accounts(accounts),
    )
    jsonschema.validate(document, SCHEMA)
    assert document["schema_version"] == "1.1"
    section = document["account_returns"]
    assert isinstance(section, dict) and section["available"]
    by_id = {a["account"]: a for a in section["accounts"]}
    sipp_1 = by_id["sipp_1"]
    assert sipp_1["available"] and sipp_1["end_value"] == pytest.approx(24000.00)
    # no external flows in sipp_1: the time- and money-weighted returns agree
    assert sipp_1["twr"] == pytest.approx(sipp_1["end_value"] / sipp_1["start_value"] - 1)
    assert sipp_1["mwr_period"] == pytest.approx(sipp_1["twr"], abs=1e-9)
    assert not by_id["pension"]["available"] and by_id["pension"]["reason"]
    assert not section["household"]["available"]
