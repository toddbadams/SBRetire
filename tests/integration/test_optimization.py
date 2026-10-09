"""F-010.2 — per-path threshold search and the Maximum Sustainable Budget (optimization §1; SPEC §14, §17.2).

Fixture tests/fixtures/scenarios/valid_minimal.yaml (As-Of 2026-10; alex male b. 1958-03, sam female
b. 1962-07; household survivor factor 0.70, sam's own 0.65) with the real data files unless a step table is
given.
"""

from __future__ import annotations

import functools
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from numpy.typing import NDArray

from sbretire.config import Scenario, parse_scenario
from sbretire.monte_carlo import RandomInputs, draw_random_inputs, run_monte_carlo
from sbretire.mortality import MortalityTable, Sex, load_mortality_table
from sbretire.optimization import (
    BUDGET_CAP,
    BUDGET_TOLERANCE,
    maximum_sustainable_budgets,
    path_budget_thresholds,
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


def _conservative_rate(scenario: Scenario, inputs: RandomInputs, budget: float) -> float:
    return run_monte_carlo(scenario, inputs, monthly_budget_today=budget).metrics.conservative_success_rate


def test_optimization_deterministic_fixture_closed_form() -> None:
    raw = _raw(1)
    raw["portfolio"]["annual_return"] = 0.0
    raw["income"] = []
    raw["inflation"].update(log_mean=0.0, innovation_sd=0.0, initial_rate=0.0)
    scenario = _scenario(raw)
    # alex q = 1 from 70 -> Death Month 18; sam q = 1 from 75 -> Death Month 130 (see F-008.3)
    inputs = draw_random_inputs(scenario, _step_table(70, 75), ResolvedSeed(1, "config"))
    np.testing.assert_array_equal(inputs.death_months, [[18], [130]])
    closed_form = 500_000 / (18 + 0.65 * 112)  # 18 months both alive, 112 months sam alone at her own 0.65

    (result,) = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.5])
    assert result.maximum_monthly_budget_today is not None
    assert closed_form - BUDGET_TOLERANCE <= result.maximum_monthly_budget_today <= closed_form
    assert result.maximum_annual_budget_today == pytest.approx(12 * result.maximum_monthly_budget_today)
    assert result.converged and result.note == ""
    assert _conservative_rate(scenario, inputs, result.maximum_monthly_budget_today) == 1.0
    assert _conservative_rate(scenario, inputs, closed_form + 0.01) == 0.0


def _scalar_bisection(scenario: Scenario, inputs: RandomInputs, target: float) -> float:
    """SPEC §14 taken literally: bisect the budget on the Conservative Success Rate (reference only)."""
    low, high = 0.0, 50_000.0
    assert _conservative_rate(scenario, inputs, low) >= target > _conservative_rate(scenario, inputs, high)
    while high - low > BUDGET_TOLERANCE:
        middle = (low + high) / 2
        if _conservative_rate(scenario, inputs, middle) >= target:
            low = middle
        else:
            high = middle
    return low


def test_optimization_matches_scalar_bisection() -> None:
    scenario = _scenario(_raw(400))
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(3, "config"))
    targets = [0.5, 0.75, 0.9]
    results = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), targets)
    for target, result in zip(targets, results, strict=True):
        assert result.maximum_monthly_budget_today is not None
        reference = _scalar_bisection(scenario, inputs, target)
        assert abs(result.maximum_monthly_budget_today - reference) <= BUDGET_TOLERANCE, (
            target,
            result,
            reference,
        )


def test_optimization_confirming_run() -> None:
    scenario = _scenario(_raw(400))
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(4, "config"))
    for result in maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.6, 0.9, 0.95]):
        budget = result.maximum_monthly_budget_today
        assert budget is not None
        at_budget = _conservative_rate(scenario, inputs, budget)
        assert at_budget >= result.target_probability
        assert at_budget == result.estimated_success_probability
        assert _conservative_rate(scenario, inputs, budget + 2 * BUDGET_TOLERANCE) < result.target_probability


def test_optimization_infeasible_target() -> None:
    raw = _raw(300)
    raw["model"]["horizon_years"] = 10  # alex 78, sam 74 at the horizon: most paths unresolved
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(5, "config"))
    unresolved = run_monte_carlo(scenario, inputs, monthly_budget_today=0.0).metrics.unresolved_share
    assert unresolved > 0.5
    feasible, infeasible = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.01, 0.5])
    assert feasible.maximum_monthly_budget_today is not None and feasible.converged
    assert infeasible.maximum_monthly_budget_today is None
    assert infeasible.maximum_annual_budget_today is None
    assert infeasible.estimated_success_probability is None and infeasible.standard_error is None
    assert not infeasible.converged
    assert "infeasible" in infeasible.note
    assert infeasible.unresolved_fraction == pytest.approx(unresolved)


def test_optimization_reports_cap() -> None:
    raw = _raw(50)
    raw["income"].append(
        {
            "id": "lottery",
            "name": "Lottery",
            "start_date": "2026-10-01",
            "annual_amount_today": 100_000_000,
            "inflation_linked": True,
            "survivor_percentage": 1.0,
            "recipient": "household",
        }
    )
    scenario = _scenario(raw)
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(6, "config"))
    search = path_budget_thresholds(scenario, inputs)
    completed = inputs.death_months.max(axis=0) < scenario.model.horizon_years * 12
    assert completed.any()
    assert search.capped[completed].all()
    assert search.upper_bound == BUDGET_CAP
    (result,) = maximum_sustainable_budgets(search, [0.5])
    assert not result.converged and "cap" in result.note
    assert result.maximum_monthly_budget_today == BUDGET_CAP


def test_optimization_monotone_and_crn() -> None:
    scenario = _scenario(_raw(500))
    inputs = draw_random_inputs(scenario, _table(), ResolvedSeed(8, "config"))
    deaths_before = inputs.death_months.copy()
    levels_before = [inputs.price_index.level(month).copy() for month in (0, 120, 719)]

    search = path_budget_thresholds(scenario, inputs)
    results = maximum_sustainable_budgets(search, [0.5, 0.9, 0.95, 0.99])

    budgets = [result.maximum_monthly_budget_today for result in results]
    assert all(budget is not None for budget in budgets)
    assert budgets == sorted(budgets, reverse=True)  # type: ignore[type-var]
    for result in results:
        assert result.budget_tolerance == BUDGET_TOLERANCE
        assert result.iterations == search.iterations > 0
        p = result.estimated_success_probability
        assert p is not None and result.standard_error == pytest.approx(math.sqrt(p * (1 - p) / 500))
    np.testing.assert_array_equal(inputs.death_months, deaths_before)
    for month, level in zip((0, 120, 719), levels_before, strict=True):
        np.testing.assert_array_equal(inputs.price_index.level(month), level)
