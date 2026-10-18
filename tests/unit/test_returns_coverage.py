"""F-026.3 — coverage of holdings by price series and ``sbretire portfolio returns`` (synthetic fixtures)."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from test_holdings_valuation import ACCOUNTS_YAML, FIXTURES

from sbretire.__main__ import main
from sbretire.ledger.accounts import load_accounts
from sbretire.ledger.returns import build_returns

ISA_FUND = "Example Strategy® 60% Fund - Accumulation"
SECURITIES_YAML = f"""\
fx: {{USD: GBP=X.csv}}
securities:
  - {{id: example_corp, name: Example Corp, file: EXA.csv, quote: USD,
     holdings: ["brokerage:EXA", "sipp_1:EXA"]}}
  - {{id: global_equity, name: Example Global Equity, file: EXG.L.csv, quote: GBX, holdings: ["sipp_1:EXG"]}}
  - {{id: strategy, name: Example Strategy, file: strategy.csv, quote: GBP, holdings: ["isa:{ISA_FUND}"]}}
  - {{id: momentum, name: Example Momentum, file: EXA.L.csv, quote: GBP, holdings: ["sipp_2:EXA"]}}
"""
HEADER = "Date,Open,High,Low,Close,Adj Close,Volume\n"


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    """oct-26 holdings (window Jul-Sep 2026 with --months 3) and a prices folder.

    example_corp: full; global_equity: starts in August (short); strategy: no August (gaps);
    momentum: no file; brokerage:EXC, pension's fund and sipp_2:EXB: in no series.
    """
    root = tmp_path / "transactions" / "oct-26"
    root.mkdir(parents=True)
    for name in (
        "schwab-positions.csv",
        "hl-account-summary.csv",
        "vanguard-holdings.csv.csv",
        "ii_holdings.csv",
        "ii.csv",
    ):
        shutil.copy(FIXTURES / name, root / name)
    prices = tmp_path / "prices"
    prices.mkdir()
    (prices / "securities.yaml").write_text(SECURITIES_YAML, encoding="utf-8")

    def write(name: str, rows: dict[str, float]) -> None:
        lines = [f"{day},1,1,1,{close},{close},0\n" for day, close in rows.items()]
        (prices / name).write_text(HEADER + "".join(lines), encoding="utf-8")

    write("GBP=X.csv", {"2026-06-30": 0.75, "2026-07-31": 0.75, "2026-08-31": 0.75, "2026-09-30": 0.75})
    write("EXA.csv", {"2026-06-30": 100.0, "2026-07-31": 101.0, "2026-08-31": 102.01, "2026-09-30": 103.0301})
    write("EXG.L.csv", {"2026-08-31": 600.0, "2026-09-30": 606.0})
    write("strategy.csv", {"2026-06-30": 250.0, "2026-07-31": 255.0, "2026-09-30": 260.0})
    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(ACCOUNTS_YAML, encoding="utf-8")
    return tmp_path / "transactions", prices, accounts


def test_coverage_classifies_holdings(tmp_path: Path) -> None:
    root, prices, accounts_path = _setup(tmp_path)
    report = build_returns(root, load_accounts(accounts_path), prices, months=3, usd_gbp=None)
    assert (report.first, report.last, report.usd_gbp) == (date(2026, 7, 1), date(2026, 9, 1), 0.75)

    rows = {row.series or row.holdings[0]: row for row in report.coverage}
    assert rows["example_corp"].status == "full" and rows["example_corp"].months == 3
    assert rows["example_corp"].holdings == ("brokerage:EXA", "sipp_1:EXA")
    assert rows["global_equity"].status == "short" and rows["global_equity"].first == date(2026, 9, 1)
    assert rows["strategy"].status == "gaps" and rows["strategy"].months == 1
    assert rows["momentum"].status == "missing" and "no price file" in rows["momentum"].detail
    for unmapped in ("brokerage:EXC", f"pension:{'Example Target 2035 Fund - Accumulation'}", "sipp_2:EXB"):
        assert rows[unmapped].status == "missing" and "securities.yaml" in rows[unmapped].detail

    invested = 3768.75 + 4950.00 + 15000.00 + 8456.79 + 20800.00 + 4210.90 + 60000.00 + 40123.00
    assert rows["example_corp"].share == pytest.approx((3768.75 + 15000.00) / invested)
    assert rows["sipp_2:EXB"].share == pytest.approx(40123.00 / invested)
    assert sum(row.share for row in report.coverage) == pytest.approx(1.0)

    corp = [row for row in report.returns if row.series == "example_corp"]
    assert [row.return_gbp for row in corp] == [pytest.approx(0.01)] * 3


def test_cli_portfolio_returns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts = _setup(tmp_path)
    out = tmp_path / "out"
    args = ["portfolio", "returns", "--root", str(root), "--accounts", str(accounts), "--prices", str(prices),
            "--output-dir", str(out), "--months", "3"]  # fmt: skip
    assert main(args) == 0
    printed = capsys.readouterr().out
    assert "Monthly returns 2026-07 to 2026-09 (3 months)" in printed
    assert "example_corp" in printed and "full" in printed and "short" in printed and "gaps" in printed
    assert "sipp_2:EXB" in printed and "missing" in printed

    data = (out / "portfolio" / "returns.csv").read_bytes()
    assert b"\r\n" not in data
    lines = data.decode("utf-8").splitlines()
    assert lines[0] == "month,series,value_gbp,dividend_gbp,return_gbp,basis"
    assert len(lines) == 1 + 3 * 3  # three series with files, three months each
    assert lines[1].startswith("2026-07,example_corp,")

    meta = json.loads((out / "portfolio" / "returns_metadata.json").read_text(encoding="utf-8"))
    assert meta["window"] == {"first": "2026-07", "last": "2026-09", "months": 3}
    files = {entry["file"]: entry for entry in meta["files"]}
    assert set(files) == {"GBP=X.csv", "EXA.csv", "EXG.L.csv", "strategy.csv"}
    assert len(files["EXA.csv"]["sha256"]) == 64 and files["EXA.csv"]["first"] == "2026-06-30"

    (prices / "securities.yaml").write_text(
        SECURITIES_YAML.replace("quote: GBX", "quote: EUR"), encoding="utf-8"
    )
    assert main(args) == 2
    assert "securities[1].quote" in capsys.readouterr().err
