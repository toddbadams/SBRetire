"""F-031.3 — Modified Dietz, chained TWR, XIRR MWR and the household in GBP (closed-form known answers)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from sbretire.ledger.account_returns import modified_dietz, returns_for, to_gbp, xirr


def test_twr_and_mwr_known_answers() -> None:
    start, end = date(2026, 4, 30), date(2026, 5, 30)  # 30 days
    r = modified_dietz(1000.0, 2100.0, [(date(2026, 5, 15), 1000.0)], start, end)
    assert r == pytest.approx((2100 - 1000 - 1000) / (1000 + 1000 * 15 / 30))

    points = [(date(2026, 1, 31), 1000.0), (date(2026, 2, 28), 1100.0), (date(2026, 3, 31), 1045.0)]
    result = returns_for(points, [])
    assert result.twr == pytest.approx(1.10 * 0.95 - 1)
    assert [m for _, m in result.monthly] == [pytest.approx(0.10), pytest.approx(-0.05)]
    assert result.mwr_period == pytest.approx(result.twr)  # no flows: the two agree
    assert result.net_flows == 0.0

    t0 = date(2024, 1, 1)
    two_years = t0 + timedelta(days=730)
    assert xirr(1000.0, [], 1000.0 * 1.05**2, t0, two_years) == pytest.approx(0.05, abs=1e-9)
    grown = returns_for([(t0, 1000.0), (two_years, 1000.0 * 1.05**2)], [])
    assert grown.mwr_annual == pytest.approx(0.05, abs=1e-9)
    half = t0 + timedelta(days=182)
    short = returns_for([(t0, 1000.0), (half, 1000.0 * 1.05 ** (182 / 365))], [])
    assert short.mwr_period == pytest.approx(1.05 ** (182 / 365) - 1, abs=1e-9)
    assert short.mwr_annual is None  # under a year: not annualised

    # a deposit at the start of the second year, everything growing at 5% a year: MWR 5%, TWR 1.05^2 - 1
    one_year = t0 + timedelta(days=365)
    v1 = 1000.0 * 1.05
    v2 = (v1 + 500.0) * 1.05 ** (365 / 365)
    flows = [(one_year, 500.0)]
    assert xirr(1000.0, flows, v2, t0, one_year + timedelta(days=365)) == pytest.approx(0.05, abs=1e-6)

    # household: GBP account plus a USD account converted at each month's rate
    d0, d1 = date(2026, 1, 31), date(2026, 2, 28)
    rates = {date(2026, 1, 1): 0.8, date(2026, 2, 1): 0.75}
    gbp_points, gbp_flows = to_gbp([(d0, 100.0), (d1, 100.0)], [(date(2026, 2, 10), 20.0)], "USD", rates)
    assert gbp_points == [(d0, pytest.approx(80.0)), (d1, pytest.approx(75.0))]
    assert gbp_flows == [(date(2026, 2, 10), pytest.approx(15.0))]
    same, _ = to_gbp([(d0, 100.0)], [], "GBP", {})
    assert same == [(d0, 100.0)]
