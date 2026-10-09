"""F-002.3 — the engine against closed-form results (T3 known-answer checks).

With balance B, monthly rate r, constant spending S and no income, the engine's recurrence
B_{t+1} = B_t (1 + r) - S has the closed form B_t = (P - S/r)(1 + r)^t + S/r (r != 0), and Depletion is the
first month t with B_t (1 + r) < S. Solving gives t = floor(x) + 1 with x = ln(K / A) / ln(1 + r), where
A = S/r - P and K = S / (r (1 + r)); for r = 0, t = floor(P / S).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sbretire.portfolio import BoolArray, FloatArray, monthly_return_rate
from sbretire.simulation import simulate_paths

NEVER = 1_000_000  # Death Month far beyond the horizon


class ConstantSpending:
    def __init__(self, amount: float) -> None:
        self.amount = amount

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        return np.zeros(alive.shape[1], dtype=np.float64)

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        return np.full(alive.shape[1], self.amount, dtype=np.float64)


def annuity_depletion_month(balance: float, rate: float, spending: float) -> int:
    if rate == 0:
        return math.floor(balance / spending)
    a = spending / rate - balance
    k = spending / (rate * (1 + rate))
    x = math.log(k / a) / math.log(1 + rate)
    assert abs(x - round(x)) > 1e-6, "case too close to a month boundary for a floating-point comparison"
    return math.floor(x) + 1


@pytest.mark.parametrize(
    ("balance", "annual_return", "spending"),
    [
        (1_000_000.0, 0.05, 8_000.0),
        (500_000.0, 0.03, 3_000.0),
        (200_000.0, -0.02, 1_500.0),
        (1_000.0, 0.0, 300.0),
        (750_000.0, 0.08, 6_000.0),
    ],
)
def test_engine_depletion_month_matches_annuity_formula(
    balance: float, annual_return: float, spending: float
) -> None:
    expected = annuity_depletion_month(balance, monthly_return_rate(annual_return), spending)
    horizon = 3_000
    assert expected < horizon

    out = simulate_paths(
        starting_balance=balance,
        annual_return=annual_return,
        death_month=np.full((2, 3), NEVER, dtype=np.int64),
        horizon_months=horizon,
        cash_flows=ConstantSpending(spending),
    )

    assert out.depletion_month.tolist() == [expected] * 3


@pytest.mark.parametrize(
    ("balance", "annual_return"), [(1_500_000.0, 0.05), (250_000.0, 0.02), (80_000.0, 0.10)]
)
def test_engine_interest_only_spending_is_perpetual(balance: float, annual_return: float) -> None:
    spending = balance * monthly_return_rate(annual_return)

    out = simulate_paths(
        starting_balance=balance,
        annual_return=annual_return,
        death_month=np.full((2, 2), NEVER, dtype=np.int64),
        horizon_months=1_200,
        cash_flows=ConstantSpending(spending),
    )

    assert out.depletion_month.tolist() == [-1, -1]
    assert out.censored.tolist() == [True, True]
    np.testing.assert_allclose(out.final_balance, balance, rtol=1e-9)
