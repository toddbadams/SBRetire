"""F-029.2 — long-only capped optimiser: closed-form and dominance checks."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from sbretire.ledger.frontier import Estimates, frontier, max_return_at, max_sharpe, min_variance

TOL = 1e-6


def _estimates(mean: list[float], cov: list[list[float]]) -> Estimates:
    n = len(mean)
    return Estimates(
        series=[f"s{i}" for i in range(n)], mean=np.array(mean), cov=np.array(cov), shrinkage=None,
        today=np.full(n, 1 / n), returns=np.zeros((0, n)),
    )  # fmt: skip


def test_optimiser_known_answers() -> None:
    two = _estimates([0.05, 0.08], [[0.01, 0.0], [0.0, 0.04]])  # σ 10% and 20%, uncorrelated
    mv = min_variance(two, cap=1.0)
    np.testing.assert_allclose(mv.weights, [0.8, 0.2], atol=1e-6)  # w1 = σ2² / (σ1² + σ2²)
    assert mv.volatility == pytest.approx(np.sqrt(0.8**2 * 0.01 + 0.2**2 * 0.04), abs=1e-6)
    assert mv.annual_return == pytest.approx(0.8 * 0.05 + 0.2 * 0.08, abs=1e-6)
    capped = min_variance(two, cap=0.6)
    np.testing.assert_allclose(capped.weights, [0.6, 0.4], atol=1e-6)
    with pytest.raises(ValueError, match="max_weight"):
        min_variance(two, cap=0.4)  # 2 × 0.4 < 1

    three = _estimates(
        [0.04, 0.07, 0.10],
        [[0.010, 0.002, 0.001], [0.002, 0.030, 0.006], [0.001, 0.006, 0.060]],
    )
    cap, rf = 0.6, 0.02
    points = frontier(three, cap, rf, points=11)
    assert len(points) == 11
    for mix in points:
        assert mix.weights.sum() == pytest.approx(1.0, abs=TOL)
        assert (mix.weights >= -TOL).all() and (mix.weights <= cap + TOL).all()
    vols = [m.volatility for m in points]
    rets = [m.annual_return for m in points]
    assert all(b >= a - TOL for a, b in pairwise(vols))
    assert all(b >= a - TOL for a, b in pairwise(rets))
    assert rets[-1] == pytest.approx(0.6 * 0.10 + 0.4 * 0.07, abs=1e-6)  # highest return the cap allows

    best = max_sharpe(three, cap, rf)
    assert best.sharpe is not None
    assert all(best.sharpe >= (m.sharpe or -np.inf) - TOL for m in points)

    level = 0.15
    same = max_return_at(three, cap, rf, level)
    assert same.volatility <= level + TOL
    assert same.annual_return >= max(m.annual_return for m in points if m.volatility <= level) - TOL
    assert max_return_at(three, cap, rf, 0.01).weights == pytest.approx(
        min_variance(three, cap).weights, abs=1e-6
    )
