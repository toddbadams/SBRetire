"""F-008.3 — sampled Death Months drive the engine's household states (SPEC §17.1, §17.2).

Fixture tests/fixtures/scenarios/valid_minimal.yaml: As-Of 2026-10, horizon 60 years (720 months);
alex male b. 1958-03-01 (68), sam female b. 1962-07-15 (64). Deterministic tables use q = 0 below an age and
q = 1 from it, so a death is certain in the first month of that age (simulation-conventions §2, §6):
- alex q = 1 from 70: 70th birthday month 2028-03 = month 17 -> dies during month 17 -> Death Month 18;
- sam q = 1 from 75: 75th birthday month 2037-07 = month 129 -> Death Month 130.
"""

from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from numpy.typing import NDArray

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario, parse_scenario
from sbretire.inflation import FlatPriceIndex
from sbretire.mortality import MortalityTable, Sex, load_mortality_table, sample_death_months
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.randomness import RandomStreams, ResolvedSeed
from sbretire.simulation import PathOutcomes, simulate_paths

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def _scenario() -> Scenario:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["portfolio"]["starting_balance"] = 10_000_000  # never depletes: only mortality drives the states
    return parse_scenario(raw, base_dir=FIXTURE.parent).scenario


def _step_table(death_age: dict[str, int | None]) -> MortalityTable:
    """Birth years 1958 (male) and 1962 (female): q = 0 below ``death_age[sex]``, 1 from it (None: never)."""
    grids: dict[Sex, NDArray[np.float64]] = {}
    cohorts: tuple[tuple[Sex, int], ...] = (("male", 1958), ("female", 1962))
    for sex, birth in cohorts:
        grid = np.full((1962 - 1958 + 1, 101), np.nan)
        age = death_age[sex]
        grid[birth - 1958] = [1.0 if age is not None and x >= age else 0.0 for x in range(101)]
        grid.flags.writeable = False
        grids[sex] = grid
    return MortalityTable(path=Path("step.csv"), meta={}, first_birth_year=1958, grids=grids)


class _Recorder:
    def __init__(self) -> None:
        self.alive: list[BoolArray] = []

    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None:
        self.alive.append(alive.copy())


def _run(scenario: Scenario, deaths: NDArray[np.int64], recorder: _Recorder) -> PathOutcomes:
    n_paths = deaths.shape[1]
    return simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=deaths,
        horizon_months=scenario.model.horizon_years * 12,
        cash_flows=ScenarioCashFlows(scenario, FlatPriceIndex(n_paths), n_paths),
        observer=recorder,
    )


def _stream(seed: int) -> np.random.Generator:
    return RandomStreams.from_seed(ResolvedSeed(seed, "config")).mortality


def test_deterministic_mortality_fixture_state_transitions() -> None:
    scenario = _scenario()
    deaths = sample_death_months(scenario, _step_table({"male": 70, "female": 75}), _stream(1), n_paths=3)
    np.testing.assert_array_equal(deaths, [[18, 18, 18], [130, 130, 130]])

    recorder = _Recorder()
    outcome = _run(scenario, deaths, recorder)
    states = np.array([alive[:, 0] for alive in recorder.alive])  # (months observed, 2) for path 0
    assert states[:18].all()  # months 0-17: both alive
    np.testing.assert_array_equal(states[18:130], [[False, True]] * 112)  # months 18-129: sam alone
    assert len(recorder.alive) == 130  # path ends at Household End (month 130), before its cash flows
    np.testing.assert_array_equal(outcome.household_end_month, [130, 130, 130])
    assert not outcome.censored.any()

    survivors = sample_death_months(
        scenario, _step_table({"male": None, "female": None}), _stream(1), n_paths=3
    )
    np.testing.assert_array_equal(survivors, 720)
    censored = _run(scenario, survivors, _Recorder())
    assert censored.censored.all()
    np.testing.assert_array_equal(censored.household_end_month, -1)


@functools.cache
def _real_table() -> MortalityTable:
    return load_mortality_table(ROOT / "data" / "ons_mortality.csv")


@settings(max_examples=25, deadline=None)
@given(seed=st.integers(0, 2**32))
def test_dead_person_never_alive_again(seed: int) -> None:
    scenario = _scenario()
    deaths = sample_death_months(scenario, _real_table(), _stream(seed), n_paths=64)
    recorder = _Recorder()
    _run(scenario, deaths, recorder)
    alive = np.array(recorder.alive)  # (months, 2, paths)
    # once False in some month, False in every later month: alive is non-increasing over time
    assert not (alive[1:] & ~alive[:-1]).any()
    for month, state in enumerate(alive):
        np.testing.assert_array_equal(state, month < deaths)
