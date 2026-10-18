"""F-029.4 — ``sbretire portfolio frontier`` on synthetic holdings and 24 months of synthetic prices."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from test_returns_coverage import HEADER, _setup

from sbretire.__main__ import main
from sbretire.ledger.returns import add_months

SERIES_FILES = ("EXA.csv", "EXG.L.csv", "strategy.csv", "EXA.L.csv")  # all four series of the F-026 setup


def _prices(prices: Path) -> None:
    """25 month-ends (September 2024 to September 2026) for every series and the USD rate; seeded."""
    rng = np.random.default_rng(2029)
    months = [add_months(date(2024, 9, 1), i) for i in range(25)]
    for name, drift, vol in zip(
        SERIES_FILES, (0.008, 0.012, 0.005, 0.010), (0.04, 0.07, 0.02, 0.05), strict=True
    ):
        level = 100.0
        lines = []
        for month in months:
            lines.append(f"{month:%Y-%m}-28,1,1,1,{level:.4f},{level:.4f},0\n")
            level *= 1 + drift + vol * rng.standard_normal()
        (prices / name).write_text(HEADER + "".join(lines), encoding="utf-8")
    rate = "".join(f"{m:%Y-%m}-28,1,1,1,0.75,0.75,0\n" for m in months)
    (prices / "GBP=X.csv").write_text(HEADER + rate, encoding="utf-8")


def test_cli_portfolio_frontier(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts = _setup(tmp_path)
    _prices(prices)
    securities = prices / "securities.yaml"
    securities.write_text("risk_free_rate: 0.04\nmax_weight: 0.6\n" + securities.read_text("utf-8"), "utf-8")
    text = accounts.read_text("utf-8").replace(
        'currency: GBP, transactions: ["hl.csv"]',
        'currency: GBP, trading: {fee_per_trade: 11.95, cost_rate: 0.002}, transactions: ["hl.csv"]',
    )
    accounts.write_text(text, "utf-8")
    out = tmp_path / "out"
    args = ["portfolio", "frontier", "--root", str(root), "--accounts", str(accounts),
            "--prices", str(prices), "--output-dir", str(out),
            "--months", "24", "--min-trade", "1"]  # fmt: skip

    assert main(args) == 0
    printed = capsys.readouterr().out
    assert "Efficient frontier of the priced sleeve: 4 series, 2024-10 to 2026-09 (24 months)" in printed
    assert "Ledoit-Wolf" in printed and "max weight 60%" in printed
    assert "Analysis, not advice" in printed and "cannot be made as" in printed
    for label in ("today", "min variance", "max Sharpe", "target (same risk as today)", "within accounts"):
        assert label in printed
    assert "Trades within accounts" in printed and "Household trades (analysis only" in printed
    assert "turnover" in printed

    folder = out / "portfolio"
    for name in ("frontier.csv", "frontier_weights.csv", "trades.csv"):
        assert b"\r\n" not in (folder / name).read_bytes()
    frontier = list(csv.DictReader((folder / "frontier.csv").read_text("utf-8").splitlines()))
    assert list(frontier[0]) == ["point", "return", "volatility", "sharpe"]
    assert [r["point"] for r in frontier][-5:] == [
        "today",
        "min_variance",
        "max_sharpe",
        "target",
        "within_accounts",
    ]
    assert len(frontier) == 21 + 5
    weights = list(csv.DictReader((folder / "frontier_weights.csv").read_text("utf-8").splitlines()))
    assert list(weights[0]) == [
        "series",
        "name",
        "today",
        "min_variance",
        "max_sharpe",
        "target",
        "within_accounts",
    ]
    assert sorted(r["series"] for r in weights) == ["example_corp", "global_equity", "momentum", "strategy"]
    for column in ("today", "min_variance", "max_sharpe", "target", "within_accounts"):
        assert sum(float(r[column]) for r in weights) == pytest.approx(1.0, abs=1e-6)
        assert all(float(r[column]) <= 0.6 + 1e-6 for r in weights) or column in ("today", "within_accounts")
    trades = list(csv.DictReader((folder / "trades.csv").read_text("utf-8").splitlines()))
    assert list(trades[0]) == [
        "scope",
        "account",
        "series",
        "current_gbp",
        "target_gbp",
        "trade_gbp",
        "cost_gbp",
    ]
    household = [r for r in trades if r["scope"] == "household"]
    assert sum(float(r["trade_gbp"]) for r in household) == pytest.approx(0.0, abs=0.01)
    in_sipp = [r for r in trades if r["scope"] == "account" and r["account"] == "sipp_1"]
    assert {r["series"] for r in in_sipp} == {"example_corp", "global_equity"}  # the only account holding two
    for row in in_sipp:
        assert float(row["cost_gbp"]) == pytest.approx(
            11.95 + 0.002 * abs(float(row["trade_gbp"])), abs=0.005
        )

    assert main([*args, "--max-weight", "0.2"]) == 2  # 4 × 0.2 < 1
    assert "max_weight" in capsys.readouterr().err
