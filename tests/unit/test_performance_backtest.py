"""F-027.2 — back-test of today's weights: re-weighting over gaps, cash at the risk-free rate, covered share."""

from __future__ import annotations

from datetime import date

import pytest

from sbretire.ledger.performance import backtest, monthly_rate
from sbretire.ledger.returns import MonthlyReturn

FEB, MAR, APR = date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)


def _series(series: str, returns: list[float | None]) -> list[MonthlyReturn]:
    return [
        MonthlyReturn(month, series, None if r is None else 1.0, 0.0, r, "adjusted")
        for month, r in zip((FEB, MAR, APR), returns, strict=True)
    ]


def test_backtest_reweights_and_covers() -> None:
    returns = _series("a", [0.01, 0.02, 0.03]) + _series("b", [0.02, None, -0.01]) + _series("c", [0.5] * 3)
    weights = {"a": 60.0, "b": 30.0}  # "c" has returns but no holding today: ignored
    cash, total, rate = 10.0, 110.0, 0.04  # 10 of the 110 is unpriced
    rf = monthly_rate(rate)
    months = backtest(weights, cash, total, returns, FEB, APR, rate)
    assert [m.month for m in months] == [FEB, MAR, APR]
    assert [m.portfolio_return for m in months] == [
        pytest.approx((60 * 0.01 + 30 * 0.02 + 10 * rf) / 100),
        pytest.approx((60 * 0.02 + 10 * rf) / 70),  # b has no March return: a and cash rescaled
        pytest.approx((60 * 0.03 - 30 * 0.01 + 10 * rf) / 100),
    ]
    assert [m.covered_share for m in months] == [
        pytest.approx(100 / 110),
        pytest.approx(70 / 110),
        pytest.approx(100 / 110),
    ]

    all_cash = backtest({}, 50.0, 50.0, [], FEB, APR, rate)
    assert [m.portfolio_return for m in all_cash] == [pytest.approx(rf)] * 3
    assert [m.covered_share for m in all_cash] == [1.0] * 3
