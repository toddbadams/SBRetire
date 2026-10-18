"""F-029.3 — household and within-account trades, costs, minimum trade and half-window sensitivity."""

from __future__ import annotations

import numpy as np
import pytest

from sbretire.ledger.frontier import (
    Estimates,
    household_trades,
    plan_trades,
    sensitivity,
    trade_cost,
    within_account_targets,
)


def test_trades_costs_and_sensitivity() -> None:
    house = household_trades({"a": 60.0, "b": 40.0}, {"a": 0.3, "b": 0.7})
    assert house == {"a": (60.0, pytest.approx(30.0), pytest.approx(-30.0)), "b": (40.0, pytest.approx(70.0),
                                                                                  pytest.approx(30.0))}  # fmt: skip
    assert sum(trade for _, _, trade in house.values()) == pytest.approx(0.0)

    target = {"a": 0.3, "b": 0.5, "c": 0.2, "d": 0.0}
    holdings = {
        "x": {"a": 40.0, "b": 10.0},  # re-split 50 as 0.3 : 0.5 over a and b
        "v": {"a": 10.0, "b": 6.0},  # 16 → 6 and 10: both moves of 4 are under the minimum trade
        "w": {"d": 25.0},  # its only series has target 0: kept as today
    }
    split = within_account_targets(holdings, target)
    assert split["x"] == pytest.approx({"a": 50 * 0.3 / 0.8, "b": 50 * 0.5 / 0.8})
    assert split["v"] == pytest.approx({"a": 6.0, "b": 10.0})
    assert split["w"] == {"d": 25.0}

    assert trade_cost(-21.25, fee_gbp=10.0, rate=0.01) == pytest.approx(10.0 + 0.2125)
    assert trade_cost(0.0, fee_gbp=10.0, rate=0.01) == 0.0

    trades = plan_trades(holdings, split, costs={"x": (10.0, 0.01), "v": (10.0, 0.01)}, min_trade=5.0)
    assert [(t.account, t.series) for t in trades] == [("x", "a"), ("x", "b")]  # v's 4s are skipped
    assert trades[0].trade_gbp == pytest.approx(50 * 0.3 / 0.8 - 40.0)
    assert trades[0].cost_gbp == pytest.approx(10.0 + 0.01 * abs(50 * 0.3 / 0.8 - 40.0))
    assert all(t.cost_gbp > 0 for t in trades)

    # minimum-variance weights flip between halves: (0.8, 0.2) then (0.2, 0.8), so turnover is 0.6
    a = [0.01, -0.01, 0.01, -0.01, 0.02, -0.02, 0.02, -0.02]
    b = [0.02, 0.02, -0.02, -0.02, 0.01, 0.01, -0.01, -0.01]  # uncorrelated with a in each half
    returns = np.array([a, b]).T
    est = Estimates(
        series=["a", "b"], mean=12 * returns.mean(axis=0), cov=12 * np.cov(returns, rowvar=False),
        shrinkage=None, today=np.array([0.5, 0.5]), returns=returns, covariance="sample",
    )  # fmt: skip
    first, second, turnover = sensitivity(est, cap=1.0, risk_free=0.0, target="min-variance")
    np.testing.assert_allclose(first.weights, [0.8, 0.2], atol=1e-6)
    np.testing.assert_allclose(second.weights, [0.2, 0.8], atol=1e-6)
    assert turnover == pytest.approx(0.6, abs=1e-6)
