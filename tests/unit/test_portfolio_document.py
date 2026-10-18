"""F-030.2 — portfolio.json (schema 1.0) and ``sbretire portfolio report`` on synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from test_exposure_cli import GLOBAL, STRATEGY
from test_frontier_cli import _prices
from test_returns_coverage import _setup

from sbretire.__main__ import main
from sbretire.ledger.accounts import load_accounts
from sbretire.ledger.document import ReportOptions, build_portfolio_document

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "portfolio.schema.json").read_text(encoding="utf-8"))
ANALYSES = ("exposure", "performance", "frontier", "risk", "rebalance", "income")


def full_setup(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """F-029 synthetic holdings, 24 months of prices, a risk-free rate, a cap, stock fields and factsheets."""
    root, prices, accounts = _setup(tmp_path)
    _prices(prices)
    securities = prices / "securities.yaml"
    text = securities.read_text("utf-8")
    text = text.replace(
        'holdings: ["brokerage:EXA", "sipp_1:EXA"]',
        'holdings: ["brokerage:EXA", "sipp_1:EXA"], sector: technology, region: United States',
    )
    text = text.replace('holdings: ["sipp_1:EXG"]', 'holdings: ["sipp_1:EXG"], factsheet: global.yaml')
    text = text.replace('holdings: ["isa:', 'factsheet: strategy.yaml, holdings: ["isa:')
    securities.write_text("risk_free_rate: 0.04\nmax_weight: 0.6\n" + text, "utf-8")  # fmt: skip
    factsheets = tmp_path / "factsheets"
    factsheets.mkdir()
    (factsheets / "global.yaml").write_text(GLOBAL, encoding="utf-8")
    (factsheets / "strategy.yaml").write_text(STRATEGY, encoding="utf-8")
    return root, prices, accounts, factsheets


def test_portfolio_document_full_and_empty(tmp_path: Path) -> None:
    root, prices, accounts_path, factsheets = full_setup(tmp_path / "full")
    accounts = load_accounts(accounts_path)
    options = ReportOptions(root=root, prices=prices, factsheets=factsheets, months=24, min_trade=1.0)
    document = build_portfolio_document(options, accounts)
    jsonschema.validate(document, SCHEMA)
    assert document["schema_version"] == "1.0" and document["folder"] == "oct-26"
    for section in ANALYSES:
        assert document[section]["available"], (section, document[section].get("reason"))  # type: ignore[index]
    assert document["total"]["value_gbp"] == pytest.approx(160265.61)  # type: ignore[index]
    assert document["total"]["starting_balance_yaml"].startswith("starting_balance: 160266")  # type: ignore[index]
    frontier = document["frontier"]
    assert len(frontier["series"]) == 4 and len(frontier["points"]) == 21  # type: ignore[index]
    risk = document["risk"]
    assert [row[i] for i, row in enumerate(risk["correlation"])] == pytest.approx([1.0] * 4)  # type: ignore[index]
    assert sum(c["risk_share"] for c in risk["contribution"]) == pytest.approx(1.0)  # type: ignore[index]
    assert document["rebalance"]["within"]  # type: ignore[index]
    assert len(document["holdings"]) == 8  # type: ignore[arg-type]
    assert json.dumps(document, allow_nan=False)  # finite numbers only

    root, prices, accounts_path = _setup(tmp_path / "empty")
    (prices / "securities.yaml").unlink()
    empty = build_portfolio_document(
        ReportOptions(root=root, prices=prices, factsheets=tmp_path / "none", months=3, usd_gbp=0.75),
        load_accounts(accounts_path),
    )
    jsonschema.validate(empty, SCHEMA)
    assert empty["total"]["value_gbp"] == pytest.approx(160265.61)  # type: ignore[index]
    for section in ("exposure", "performance", "frontier", "risk", "rebalance"):
        assert not empty[section]["available"] and empty[section]["reason"], section  # type: ignore[index]
    assert "securities.yaml" in empty["exposure"]["reason"]  # type: ignore[index]


def test_cli_portfolio_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, prices, accounts, factsheets = full_setup(tmp_path)
    out = tmp_path / "out"
    args = ["portfolio", "report", "--root", str(root), "--accounts", str(accounts), "--prices", str(prices),
            "--factsheets", str(factsheets), "--output-dir", str(out), "--months", "24"]  # fmt: skip
    assert main(args) == 0
    printed = capsys.readouterr().out
    for section in ANALYSES:
        assert f"{section}: available" in printed, section
    data = json.loads((out / "portfolio" / "portfolio.json").read_text("utf-8"))
    script = (out / "portfolio" / "portfolio.js").read_text("utf-8")
    assert script.startswith("window.SBRETIRE_PORTFOLIO = ") and script.endswith(";\n")
    assert json.loads(script[len("window.SBRETIRE_PORTFOLIO = ") : -2]) == data
    for page in ("portfolio.html", "portfolio-view.css", "portfolio-view.js", "viewer.css", "theme.css"):
        assert (out / page).is_file(), page

    (factsheets / "global.yaml").write_text(GLOBAL.replace("Japan: 5", "Atlantis: 5"), encoding="utf-8")
    assert main(args) == 2
    assert "regions.Atlantis" in capsys.readouterr().err
