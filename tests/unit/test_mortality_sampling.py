"""F-008 — monthly death probabilities, survival curve and Death Month sampling.

F-008 brief §2; simulation-conventions §2, §6; SPEC §7.2, §17.1.
"""

from __future__ import annotations

import functools
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from sbretire.config import Person
from sbretire.mortality import (
    MortalityTable,
    load_mortality_table,
    monthly_death_probabilities,
    survival_curve,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_CSV = ROOT / "data" / "ons_mortality.csv"
AS_OF = date(2026, 10, 1)


def _person(dob: date, sex: str = "male") -> Person:
    return Person.model_validate({"id": "p", "name": "P", "date_of_birth": dob, "sex": sex})


@functools.cache
def _real() -> MortalityTable:
    return load_mortality_table(REAL_CSV)


@given(q=st.floats(0.0, 1.0))
def test_monthly_conversion_reproduces_annual_probability(q: float) -> None:
    """Twelve months at q_m compound back to q (SPEC §17.1), for any q, through the production code."""
    table = _constant_table(q)
    monthly = monthly_death_probabilities(table, _person(date(1964, 10, 1)), AS_OF, horizon_months=12)
    assert np.all(monthly == monthly[0])  # one year of age: twelve identical intervals
    assert 1 - np.prod(1 - monthly) == pytest.approx(q, abs=1e-12)
    real = monthly_death_probabilities(_real(), _person(date(1964, 10, 1)), AS_OF, horizon_months=12)
    annual = _real().annual_q("male", 1964, np.array([62]))[0]
    assert 1 - np.prod(1 - real) == pytest.approx(annual, abs=1e-12)


@functools.cache
def _constant_table(q: float) -> MortalityTable:
    """Every age at birth year 1964 with the same q (built in memory, no file)."""
    grid = np.full((1, 101), q)
    grid.flags.writeable = False
    return MortalityTable(
        path=Path("constant.csv"), meta={}, first_birth_year=1964, grids={"male": grid, "female": grid}
    )


def test_monthly_death_probabilities_age_steps_in_birthday_month() -> None:
    table = _real()
    person = _person(date(1958, 3, 1))  # 68 at 2026-10; 69 from 2027-03 = month 5
    monthly = monthly_death_probabilities(table, person, AS_OF, horizon_months=24)
    assert monthly.shape == (24,) and monthly.dtype == np.float64
    q68, q69, q70 = table.annual_q("male", 1958, np.array([68, 69, 70]))
    np.testing.assert_allclose(monthly[0:5], 1 - (1 - q68) ** (1 / 12), rtol=1e-14)
    np.testing.assert_allclose(monthly[5:17], 1 - (1 - q69) ** (1 / 12), rtol=1e-14)
    np.testing.assert_allclose(monthly[17:24], 1 - (1 - q70) ** (1 / 12), rtol=1e-14)
    # A mid-month birthday counts from its month: born 1962-07-15 -> 64 at 2026-10, 65 from 2027-07 (month 9).
    mid = monthly_death_probabilities(table, _person(date(1962, 7, 15), "female"), AS_OF, horizon_months=12)
    q64, q65 = table.annual_q("female", 1962, np.array([64, 65]))
    np.testing.assert_allclose(mid[:9], 1 - (1 - q64) ** (1 / 12), rtol=1e-14)
    np.testing.assert_allclose(mid[9:], 1 - (1 - q65) ** (1 / 12), rtol=1e-14)


def test_monthly_death_probabilities_use_age_100_tail() -> None:
    table = _real()
    person = _person(date(1930, 1, 1), "female")  # 96 at 2026-10; 100 from 2030-01 (month 39)
    monthly = monthly_death_probabilities(table, person, AS_OF, horizon_months=120)
    q100 = table.annual_q("female", 1930, np.array([100]))[0]
    np.testing.assert_allclose(monthly[39:], 1 - (1 - q100) ** (1 / 12), rtol=1e-14)
    assert monthly[38] < monthly[39]


def test_survival_curve_shape_and_monotone() -> None:
    monthly = monthly_death_probabilities(_real(), _person(date(1964, 9, 1)), AS_OF, horizon_months=720)
    curve = survival_curve(monthly)
    assert curve.shape == (721,) and curve.dtype == np.float64
    assert curve[0] == 1.0
    assert np.all(np.diff(curve) <= 0)
    np.testing.assert_allclose(curve[1:], np.cumprod(1 - monthly), rtol=1e-13)
    assert 0 <= curve[-1] < 0.001  # 1964 cohort to age 122
    np.testing.assert_array_equal(survival_curve(np.array([0.0, 1.0, 0.5])), [1.0, 1.0, 0.0, 0.0])
