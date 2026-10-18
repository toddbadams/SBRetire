"""F-027.1 — risk-free rate config and performance metrics: closed-form known answers."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pytest

from sbretire.config import ScenarioError
from sbretire.ledger.performance import metrics, monthly_rate, rolling
from sbretire.ledger.prices import load_securities

SERIES = "securities:\n  - {id: a, name: A, file: a.csv, quote: GBP, holdings: ['x:A']}\n"


def _months(count: int, start: date = date(2024, 1, 1)) -> list[date]:
    return [
        date(start.year + (start.month - 1 + i) // 12, (start.month - 1 + i) % 12 + 1, 1)
        for i in range(count)
    ]


def test_risk_free_rate_config(tmp_path: Path) -> None:
    path = tmp_path / "securities.yaml"
    path.write_text("risk_free_rate: 0.04\n" + SERIES, encoding="utf-8")
    assert load_securities(path).risk_free_rate == 0.04
    path.write_text(SERIES, encoding="utf-8")
    assert load_securities(path).risk_free_rate is None
    for bad in ("-0.01", "0.2"):
        path.write_text(f"risk_free_rate: {bad}\n" + SERIES, encoding="utf-8")
        with pytest.raises(ScenarioError) as caught:
            load_securities(path)
        assert [issue.location for issue in caught.value.issues] == ["risk_free_rate"]
    assert monthly_rate(0.04) == pytest.approx(1.04 ** (1 / 12) - 1)
    assert monthly_rate(0.0) == 0.0


def test_metrics_known_answers() -> None:
    constant = metrics(_months(24), [0.01] * 24, 0.0)
    assert constant.months == 24
    assert constant.annual_return == pytest.approx(1.01**12 - 1)
    assert constant.annual_volatility == pytest.approx(0.0)
    assert constant.sharpe is None
    assert (constant.max_drawdown, constant.peak, constant.trough, constant.recovery) == (
        0.0,
        None,
        None,
        None,
    )

    alternating = metrics(_months(24), [0.02, -0.01] * 12, 0.0)
    sd = 0.015 * math.sqrt(24 / 23)  # sample sd of ±0.015 about the mean 0.005
    assert alternating.annual_return == pytest.approx((1.02 * 0.99) ** 6 - 1)
    assert alternating.annual_volatility == pytest.approx(sd * math.sqrt(12))
    assert alternating.sharpe == pytest.approx(12 * 0.005 / (math.sqrt(12) * sd))
    with_rate = metrics(_months(24), [0.02, -0.01] * 12, 0.04)
    assert with_rate.sharpe == pytest.approx(12 * (0.005 - monthly_rate(0.04)) / (math.sqrt(12) * sd))

    months = _months(5)
    fall = metrics(months, [0.05, -0.10, 0.0, 0.12, 0.01], 0.0)
    assert fall.max_drawdown == pytest.approx(0.10)  # 1.05 → 0.945
    assert (fall.peak, fall.trough, fall.recovery) == (months[0], months[1], months[3])  # 1.0584 ≥ 1.05
    unrecovered = metrics(months[:3], [0.05, -0.10, 0.0], 0.0)
    assert (unrecovered.peak, unrecovered.trough, unrecovered.recovery) == (months[0], months[1], None)

    empty = metrics([], [], 0.04)
    assert (empty.months, empty.annual_return, empty.annual_volatility, empty.sharpe) == (0, None, None, None)

    run = [0.01] * 11 + [0.02, 0.0, -0.01]
    returns, volatility = rolling(run)
    assert returns[:11] == [None] * 11 and volatility[:11] == [None] * 11
    assert returns[11] == pytest.approx(1.01**11 * 1.02 - 1)
    assert returns[13] == pytest.approx(1.01**9 * 1.02 * 1.0 * 0.99 - 1)
    first_window = run[:12]
    mean = sum(first_window) / 12
    assert volatility[11] == pytest.approx(
        math.sqrt(sum((r - mean) ** 2 for r in first_window) / 11) * math.sqrt(12)
    )
