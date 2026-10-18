"""F-027.3 — ``sbretire portfolio performance`` on the F-026 synthetic holdings and price files."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from test_returns_coverage import _setup

from sbretire.__main__ import main


def test_cli_portfolio_performance(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts = _setup(tmp_path)
    out = tmp_path / "out"
    base = ["portfolio", "performance", "--root", str(root), "--accounts", str(accounts),
            "--prices", str(prices), "--output-dir", str(out), "--months", "3"]  # fmt: skip

    assert main(base) == 2  # the synthetic map sets no risk_free_rate
    assert "risk_free_rate" in capsys.readouterr().err

    assert main([*base, "--risk-free", "0.04"]) == 0
    printed = capsys.readouterr().out
    assert (
        "Back-test of today's mix, 2026-07 to 2026-09 (3 months), risk-free 4.00% a year (--risk-free)"
        in printed
    )
    assert "not a forecast" in printed
    for label in ("Annual return", "Annual volatility", "Sharpe ratio", "Max drawdown", "Covered"):
        assert label in printed
    assert "example_corp" in printed and "global_equity" in printed and "strategy" in printed

    data = (out / "portfolio" / "performance.csv").read_bytes()
    assert b"\r\n" not in data
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    assert list(rows[0]) == [
        "month", "portfolio_return", "wealth_index", "drawdown", "covered_share",
        "rolling_12m_return", "rolling_12m_volatility",
    ]  # fmt: skip
    assert [row["month"] for row in rows] == ["2026-07", "2026-08", "2026-09"]
    assert all(row["rolling_12m_return"] == "" for row in rows)  # fewer than 12 months
    assert 0 < float(rows[0]["covered_share"]) < 1

    series = list(
        csv.DictReader((out / "portfolio" / "performance_series.csv").read_text("utf-8").splitlines())
    )
    assert list(series[0]) == [
        "series", "name", "weight", "months", "annual_return", "annual_volatility", "sharpe", "max_drawdown",
    ]  # fmt: skip
    assert [row["series"] for row in series] == ["example_corp", "global_equity", "strategy"]
    corp = series[0]
    assert corp["months"] == "3" and float(corp["annual_return"]) == pytest.approx(1.01**12 - 1)
    assert corp["annual_volatility"] == "" and corp["sharpe"] == ""  # under 12 months: n/a
