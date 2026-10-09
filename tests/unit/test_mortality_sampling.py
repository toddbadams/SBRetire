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

from sbretire.config import Person, Scenario, load_scenario
from sbretire.mortality import (
    MortalityTable,
    load_mortality_table,
    monthly_death_probabilities,
    sample_death_months,
    survival_curve,
)
from sbretire.randomness import RandomStreams, ResolvedSeed

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


EXAMPLE = ROOT / "config" / "model.example.yaml"


def _example(horizon_years: int | None = None) -> Scenario:
    scenario = load_scenario(EXAMPLE).scenario
    if horizon_years is None:
        return scenario
    model = scenario.model.model_copy(update={"horizon_years": horizon_years})
    return scenario.model_copy(update={"model": model})


def _mortality_stream(seed: int) -> np.random.Generator:
    return RandomStreams.from_seed(ResolvedSeed(seed, "config")).mortality


def test_sample_death_months_shape_and_range() -> None:
    scenario = _example(horizon_years=60)
    deaths = sample_death_months(scenario, _real(), _mortality_stream(1), n_paths=5_000)
    assert deaths.shape == (2, 5_000) and deaths.dtype == np.int64
    assert deaths.min() >= 1 and deaths.max() <= 720
    assert (deaths == 720).any()  # some survive a 60-year horizon (female b. 1969 reaches 117)


def test_sample_death_months_seed_42_known_answer() -> None:
    # Example scenario (As-Of 2026-10, horizon 100 y): male b. 1960-09, female b. 1969-05. Pinned values were
    # computed independently: own CSV parse, own survival loop, d = min{k >= 1 : u < 1 - S_k} on
    # SeedSequence(42, spawn_key=(0,)).random((2, 4)).
    deaths = sample_death_months(_example(), _real(), _mortality_stream(42), n_paths=4)
    np.testing.assert_array_equal(deaths, [[371, 368, 354, 179], [527, 245, 614, 452]])


def test_sample_death_months_matches_survival_curve() -> None:
    scenario = _example(horizon_years=60)
    n_paths = 100_000
    deaths = sample_death_months(scenario, _real(), _mortality_stream(11), n_paths=n_paths)
    horizon = 720
    for row, person in enumerate(scenario.people):
        curve = survival_curve(
            monthly_death_probabilities(_real(), person, scenario.model.as_of_date, horizon)
        )
        for k in (12, 120, 240, 360, horizon - 1):
            expected = 1 - curve[k]
            observed = float(np.mean(deaths[row] <= k))
            se = max(np.sqrt(expected * (1 - expected) / n_paths), 1 / n_paths)
            assert abs(observed - expected) <= 4 * se, (person.id, k, observed, expected)
        # d == H means died in the last month or survived it: probability S_{H-1}
        assert abs(float(np.mean(deaths[row] == horizon)) - curve[horizon - 1]) <= 4 * max(
            np.sqrt(curve[horizon - 1] * (1 - curve[horizon - 1]) / n_paths), 1 / n_paths
        )


def test_sample_death_months_people_independent() -> None:
    deaths = sample_death_months(_example(horizon_years=60), _real(), _mortality_stream(5), n_paths=100_000)
    assert abs(float(np.corrcoef(deaths[0], deaths[1])[0, 1])) < 0.01


def test_sample_death_months_horizon_stable() -> None:
    long = sample_death_months(_example(horizon_years=60), _real(), _mortality_stream(9), n_paths=20_000)
    short = sample_death_months(_example(horizon_years=30), _real(), _mortality_stream(9), n_paths=20_000)
    np.testing.assert_array_equal(short, np.minimum(long, 360))


def test_sample_death_months_degenerate_tables() -> None:
    scenario = _example(horizon_years=10)
    certain = _constant_cohort_table({1960: 1.0, 1969: 1.0})
    np.testing.assert_array_equal(sample_death_months(scenario, certain, _mortality_stream(3), n_paths=50), 1)
    never = _constant_cohort_table({1960: 0.0, 1969: 0.0})
    np.testing.assert_array_equal(sample_death_months(scenario, never, _mortality_stream(3), n_paths=50), 120)


def _constant_cohort_table(q_by_birth_year: dict[int, float]) -> MortalityTable:
    first = min(q_by_birth_year)
    grid = np.full((max(q_by_birth_year) - first + 1, 101), np.nan)
    for birth, q in q_by_birth_year.items():
        grid[birth - first] = q
    grid.flags.writeable = False
    return MortalityTable(
        path=Path("constant.csv"), meta={}, first_birth_year=first, grids={"male": grid, "female": grid}
    )
