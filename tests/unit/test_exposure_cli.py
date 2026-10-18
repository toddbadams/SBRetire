"""F-028.3 — ``sbretire portfolio exposure`` on the F-026 synthetic holdings with synthetic factsheets."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pytest
from test_returns_coverage import _setup

from sbretire.__main__ import main

GLOBAL = """\
as_of: 2026-09-30
source: Example Global Equity factsheet
asset_classes: {Equity: 100}
sectors: {Technology: 25, Financials: 15, Health Care: 10, Industrials: 10, Other: 40}
regions: {United States: 60, United Kingdom: 5, Europe ex-UK: 15, Japan: 5, Emerging Markets: 15}
top_holdings: {Example Corp: 4.0, Big Bank: 1.5}
"""
STRATEGY = """\
as_of: 2025-06-30
source: Example Strategy factsheet
asset_classes: {Equity: 60, Bonds: 40}
regions: {North America: 30, UK: 40, Other: 30}
currencies: {GBP: 70, USD: 30}
"""
HOUSEHOLD = 160265.61  # F-025's synthetic valuation at 0.75 GBP per USD


def test_cli_portfolio_exposure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts = _setup(tmp_path)
    securities = prices / "securities.yaml"
    text = securities.read_text(encoding="utf-8")
    text = text.replace(
        'holdings: ["brokerage:EXA", "sipp_1:EXA"]',
        'holdings: ["brokerage:EXA", "sipp_1:EXA"], sector: technology, region: United States',
    )
    text = text.replace('holdings: ["sipp_1:EXG"]', 'holdings: ["sipp_1:EXG"], factsheet: global.yaml')
    text = text.replace('holdings: ["isa:', 'factsheet: strategy.yaml, holdings: ["isa:')
    securities.write_text(text, encoding="utf-8")
    factsheets = tmp_path / "factsheets"
    factsheets.mkdir()
    (factsheets / "global.yaml").write_text(GLOBAL, encoding="utf-8")
    (factsheets / "strategy.yaml").write_text(STRATEGY, encoding="utf-8")
    out = tmp_path / "out"
    args = ["portfolio", "exposure", "--root", str(root), "--accounts", str(accounts),
            "--prices", str(prices), "--factsheets", str(factsheets), "--output-dir", str(out)]  # fmt: skip

    assert main(args) == 0
    printed = capsys.readouterr().out
    assert "Look-through of the oct-26 holdings" in printed
    for heading in ("Asset class", "Sector", "Region", "Currency", "Top look-through holdings"):
        assert heading in printed
    assert "Information Technology" in printed and "Unclassified" in printed and "Example Corp" in printed
    assert "strategy.yaml is dated 2025-06-30, more than 12 months before" in printed

    data = (out / "portfolio" / "exposure.csv").read_bytes()
    assert b"\r\n" not in data
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    assert list(rows[0]) == ["dimension", "label", "value_gbp", "share"]
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row["dimension"]] += float(row["value_gbp"])
    for dimension in ("asset_class", "sector", "region", "currency"):
        assert totals[dimension] == pytest.approx(HOUSEHOLD), dimension
    corp = {row["label"]: float(row["value_gbp"]) for row in rows if row["dimension"] == "top_holding"}
    assert corp["Example Corp"] == pytest.approx(3768.75 + 15000.00 + 8456.79 * 0.04)

    (factsheets / "global.yaml").write_text(GLOBAL.replace("Japan: 5", "Atlantis: 5"), encoding="utf-8")
    assert main(args) == 2
    assert "regions.Atlantis" in capsys.readouterr().err
