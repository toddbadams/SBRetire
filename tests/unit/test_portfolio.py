"""F-002.1 — monthly portfolio step (SPEC §5 ordering, §9; simulation-conventions §2)."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from sbretire.portfolio import FloatArray, apply_month, monthly_return_rate


def arr(*values: float) -> FloatArray:
    return np.array(values, dtype=np.float64)


@pytest.mark.parametrize("annual", [0.05, 0.0, -0.03, 0.5, -0.9])
def test_monthly_return_rate_compounds_to_annual(annual: float) -> None:
    rate = monthly_return_rate(annual)
    assert rate == pytest.approx((1 + annual) ** (1 / 12) - 1, rel=0, abs=1e-15)
    assert (1 + rate) ** 12 == pytest.approx(1 + annual, rel=1e-12)


@pytest.mark.parametrize("annual", [-1.0, -1.5])
def test_monthly_return_rate_rejects_total_loss(annual: float) -> None:
    with pytest.raises(ValueError, match="greater than -1"):
        monthly_return_rate(annual)


def test_apply_month_orders_return_income_then_spending() -> None:
    # Return on the opening balance only: 1000 * 1.01 = 1010; + income 50 = 1060; - spending 200 = 860.
    # (Adding income before the return would give 860.5; paying spending first would give 858.)
    result = apply_month(arr(1000.0), 0.01, income=arr(50.0), spending=arr(200.0))
    assert result.balance.tolist() == pytest.approx([860.0], abs=1e-9)
    assert result.depleted.tolist() == [False]
    assert result.shortfall.tolist() == [0.0]


def test_apply_month_depletion_records_shortfall() -> None:
    # available = balance*(1+r) + income: [120, 150, 151]; spending 150 each.
    result = apply_month(
        arr(100.0, 130.0, 131.0), 0.0, income=arr(20.0, 20.0, 20.0), spending=arr(150.0, 150.0, 150.0)
    )
    assert result.depleted.tolist() == [True, False, False]  # equality (150 == 150) is funded
    assert result.shortfall.tolist() == pytest.approx([30.0, 0.0, 0.0])
    assert result.balance.tolist() == pytest.approx([0.0, 0.0, 1.0])


def test_apply_month_negative_return_can_deplete() -> None:
    result = apply_month(arr(1000.0), -0.5, income=arr(0.0), spending=arr(600.0))
    assert result.depleted.tolist() == [True]
    assert result.shortfall.tolist() == pytest.approx([100.0])
    assert result.balance.tolist() == [0.0]


_amounts = hnp.arrays(
    np.float64, st.integers(1, 30).map(lambda n: (n,)), elements=st.floats(0, 1e7, allow_nan=False)
)


@given(
    data=st.data(),
    rate=st.floats(-0.5, 0.5, allow_nan=False),
)
def test_apply_month_never_negative(data: st.DataObject, rate: float) -> None:
    balance = data.draw(_amounts)
    n = balance.shape[0]
    same_shape = hnp.arrays(np.float64, (n,), elements=st.floats(0, 1e7, allow_nan=False))
    income, spending = data.draw(same_shape), data.draw(same_shape)

    result = apply_month(balance, rate, income=income, spending=spending)

    available = balance * (1 + rate) + income
    assert (result.balance >= 0).all()
    assert (result.shortfall >= 0).all()
    np.testing.assert_array_equal(result.depleted, available < spending)
    np.testing.assert_allclose(result.balance[~result.depleted], (available - spending)[~result.depleted])
    assert (result.balance[result.depleted] == 0).all()
