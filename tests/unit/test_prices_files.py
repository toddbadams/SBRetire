"""F-026.1 — the securities map and price files (synthetic fixtures)."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from sbretire.config import ScenarioError
from sbretire.ledger.prices import load_securities, read_price_file

ROOT = Path(__file__).resolve().parents[2]
PRICES = ROOT / "tests" / "fixtures" / "prices"
EXAMPLE = ROOT / "config" / "securities.example.yaml"


def _locations(tmp_path: Path, text: str) -> list[str]:
    path = tmp_path / "securities.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ScenarioError) as caught:
        load_securities(path)
    return [issue.location for issue in caught.value.issues]


def test_load_securities_validates(tmp_path: Path) -> None:
    config = load_securities(EXAMPLE)
    assert [series.id for series in config.securities] == ["global_equity", "example_corp", "target_2035"]
    assert config.securities[0].quote == "GBX"
    assert config.securities[0].holdings == ("sipp_1:EXG", "sipp_2:EXG")
    assert config.fx == {"USD": "GBP=X.csv"}

    base = "fx: {USD: fx.csv}\nsecurities:\n"
    one = "  - {id: a, name: A, file: a.csv, quote: GBP, holdings: ['x:A']}\n"
    assert _locations(tmp_path, base + one.replace("GBP", "EUR")) == ["securities[0].quote"]
    assert _locations(tmp_path, base + one + one.replace("'x:A'", "'x:B'")) == ["securities[1].id"]
    assert _locations(tmp_path, base + one + one.replace("id: a", "id: b")) == ["securities[1].holdings[0]"]
    assert _locations(tmp_path, base + one.replace("quote: GBP", "quote: GBP, colour: red")) == [
        "securities[0].colour"
    ]
    assert _locations(tmp_path, base + one.replace("'x:A'", "'no-account'")) == ["securities[0].holdings[0]"]


def test_read_price_file_layouts_to_month_ends() -> None:
    expected = [
        (date(2026, 1, 1), 100.0, 0.0),
        (date(2026, 2, 1), 101.0, 0.0),
        (date(2026, 3, 1), 102.01, 0.0),
    ]
    for name in ("yahoo_daily.csv", "yahoo_monthly.csv"):
        prices = read_price_file(PRICES / name)
        assert [(m.month, m.close, m.dividend) for m in prices.months] == expected, name
        assert prices.basis == "adjusted"
    daily = read_price_file(PRICES / "yahoo_daily.csv")
    assert (daily.first, daily.last, daily.rows) == (
        date(2026, 1, 2),
        date(2026, 3, 31),
        4,
    )  # the null row is skipped
    assert daily.sha256 == hashlib.sha256((PRICES / "yahoo_daily.csv").read_bytes()).hexdigest()

    minimal = read_price_file(PRICES / "minimal.csv")
    assert minimal.basis == "dividends"
    assert [(m.month, m.close, m.dividend) for m in minimal.months] == [
        (date(2026, 1, 1), 100.0, 0.0),
        (date(2026, 2, 1), 101.0, 0.5),
        (date(2026, 3, 1), 102.01, 0.0),
    ]
