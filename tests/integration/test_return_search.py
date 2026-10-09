"""F-011.2 — return monotonicity, per-path minimum returns and required returns (optimization §2; SPEC §13).

Fixture tests/fixtures/scenarios/valid_minimal.yaml (As-Of 2026-10; alex male b. 1958-03, sam female
b. 1962-07; household survivor factor 0.70, sam's own 0.65; budget 3,000) with the real data files unless a
step table is given.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from numpy.typing import NDArray
from scipy.optimize import brentq

from sbretire.config import Scenario, parse_scenario
from sbretire.metrics import PathClass, classify_paths
from sbretire.monte_carlo import RandomInputs, draw_random_inputs, run_monte_carlo
from sbretire.mortality import MortalityTable, Sex, load_mortality_table
from sbretire.optimization import (
    RETURN_LOWER,
    RETURN_TOLERANCE,
    RETURN_UPPER,
    path_return_thresholds,
    required_returns,
)
from sbretire.randomness import ResolvedSeed

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def _raw(paths: int) -> dict[str, Any]:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    raw["model"]["simulation_count"] = paths
    return raw


def _scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=FIXTURE.parent).scenario


@functools.cache
def _table() -> MortalityTable:
    return load_mortality_table(ROOT / "data" / "ons_mortality.csv")


def _step_table(male_death_age: int, female_death_age: int) -> MortalityTable:
    grids: dict[Sex, NDArray[np.float64]] = {}
    cohorts: tuple[tuple[Sex, int, int], ...] = (
        ("male", 1958, male_death_age),
        ("female", 1962, female_death_age),
    )
    for sex, birth, age in cohorts:
        grid = np.full((5, 101), np.nan)
        grid[birth - 1958] = [1.0 if x >= age else 0.0 for x in range(101)]
        grid.flags.writeable = False
        grids[sex] = grid
    return MortalityTable(path=Path("step.csv"), meta={}, first_birth_year=1958, grids=grids)


def _rate(scenario: Scenario, inputs: RandomInputs, annual_return: float) -> float:
    return run_monte_carlo(scenario, inputs, annual_return=annual_return).metrics.conservative_success_rate


def test_success_is_monotone_in_return() -> None:
    scenario = _scenario(_raw(300))
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(12, "config"))
    grid = np.round(np.arange(-0.10, 0.1501, 0.01), 4)
    successful = np.array(
        [
            classify_paths(run_monte_carlo(scenario, inputs, annual_return=float(r)).outcomes)
            == PathClass.SUCCESSFUL
            for r in grid
        ]
    )  # (returns, paths)
    assert not np.any(successful[:-1] & ~successful[1:])  # once Successful, Successful at every higher return
    rates = successful.mean(axis=1)
    assert np.all(np.diff(rates) >= 0)
    assert rates[0] < rates[-1]  # the return really matters on this fixture


def test_return_search_deterministic_closed_form() -> None:
    raw = _raw(1)
    raw["income"] = []
    raw["budget"]["monthly_amount_today"] = 6_000
    raw["inflation"].update(log_mean=0.0, innovation_sd=0.0, initial_rate=0.0)
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _step_table(70, 75), ResolvedSeed(1, "config"))
    np.testing.assert_array_equal(inputs.death_months, [[18], [130]])
    spending = np.array([6_000.0] * 18 + [6_000.0 * 0.65] * 112)  # months 0-129, then household end

    def shortfall(monthly: float) -> float:
        """Balance needed at month 0 to fund every month exactly (return before spending) minus 500,000."""
        return float(np.sum(spending / (1 + monthly) ** np.arange(1, 131))) - 500_000.0

    monthly_root = brentq(shortfall, -0.05, 0.05, xtol=1e-14)
    closed_form = (1 + monthly_root) ** 12 - 1
    assert closed_form > 0

    (result,) = required_returns(path_return_thresholds(scenario, inputs), [0.5])
    assert result.required_annual_return is not None
    assert closed_form <= result.required_annual_return <= closed_form + RETURN_TOLERANCE
    assert result.converged and result.note == ""
    assert result.monthly_budget_today == 6_000
    assert _rate(scenario, inputs, result.required_annual_return) == 1.0
    assert _rate(scenario, inputs, closed_form - 0.0001) == 0.0


def _scalar_bisection(scenario: Scenario, inputs: RandomInputs, target: float) -> float:
    """SPEC §13 taken literally: bisect the return on the Conservative Success Rate (reference only)."""
    low, high = RETURN_LOWER, RETURN_UPPER
    assert _rate(scenario, inputs, low) < target <= _rate(scenario, inputs, high)
    while high - low > RETURN_TOLERANCE:
        middle = (low + high) / 2
        if _rate(scenario, inputs, middle) >= target:
            high = middle
        else:
            low = middle
    return high


def test_return_search_matches_scalar_bisection() -> None:
    raw = _raw(400)
    raw["budget"]["monthly_amount_today"] = 4_000
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(13, "config"))
    targets = [0.5, 0.8, 0.95]
    for target, result in zip(
        targets, required_returns(path_return_thresholds(scenario, inputs), targets), strict=True
    ):
        assert result.required_annual_return is not None
        reference = _scalar_bisection(scenario, inputs, target)
        assert abs(result.required_annual_return - reference) <= RETURN_TOLERANCE, (target, result, reference)


def test_return_search_confirming_run() -> None:
    raw = _raw(400)
    raw["budget"]["monthly_amount_today"] = 4_000
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(14, "config"))
    for result in required_returns(path_return_thresholds(scenario, inputs), [0.6, 0.9, 0.95]):
        r = result.required_annual_return
        assert r is not None
        at_r = _rate(scenario, inputs, r)
        assert at_r >= result.target_probability
        assert at_r == result.estimated_success_probability
        assert _rate(scenario, inputs, r - 2 * RETURN_TOLERANCE) < result.target_probability


def test_return_search_reports_bounds() -> None:
    hopeless = _raw(200)
    hopeless["budget"]["monthly_amount_today"] = 100_000
    scenario = _scenario(hopeless)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(15, "config"))
    (none,) = required_returns(path_return_thresholds(scenario, inputs), [0.5])
    assert none.required_annual_return is None and none.estimated_success_probability is None
    assert not none.converged and "no solution" in none.note

    easy = _raw(200)
    easy["budget"]["monthly_amount_today"] = 100
    scenario = _scenario(easy)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(16, "config"))
    search = path_return_thresholds(scenario, inputs)
    completed = inputs.death_months.max(axis=0) < scenario.model.horizon_years * 12
    assert search.at_lower_bound[completed].all()
    (low,) = required_returns(search, [0.5])
    assert low.required_annual_return == RETURN_LOWER
    assert not low.converged and "-50%" in low.note


def test_return_search_monotone_targets_and_crn() -> None:
    raw = _raw(500)
    raw["budget"]["monthly_amount_today"] = 4_000
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(17, "config"))
    deaths_before = inputs.death_months.copy()
    levels_before = [inputs.price_index.level(month).copy() for month in (0, 120, 719)]

    search = path_return_thresholds(scenario, inputs)
    results = required_returns(search, [0.5, 0.9, 0.95, 0.99])
    returns = [result.required_annual_return for result in results]
    assert all(r is not None for r in returns)
    assert returns == sorted(returns)  # type: ignore[type-var]
    for result in results:
        assert result.return_tolerance == RETURN_TOLERANCE
        assert result.iterations == search.iterations > 0
        assert result.monthly_budget_today == 4_000
        p = result.estimated_success_probability
        assert p is not None and result.standard_error == pytest.approx(np.sqrt(p * (1 - p) / 500))
    np.testing.assert_array_equal(inputs.death_months, deaths_before)
    for month, level in zip((0, 120, 719), levels_before, strict=True):
        np.testing.assert_array_equal(inputs.price_index.level(month), level)
