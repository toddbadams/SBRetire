"""F-020 — budget.spend_at_least_income: Required Spending floored at the month's household income.

Hand fixture (``annual_fixtures.hand_scenario``): household income 1,000/month (survivor share 1.0), survivor
factors 0.7 (alex, household default) and 0.65 (sam).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import yaml

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario, ScenarioError, parse_scenario
from sbretire.income import ScenarioIncome
from sbretire.inflation import StochasticPriceIndex
from sbretire.metadata import config_sha256
from sbretire.metrics import PathClass, classify_paths
from sbretire.monte_carlo import RandomInputs, run_monte_carlo
from sbretire.optimization import BUDGET_TOLERANCE, maximum_sustainable_budgets, path_budget_thresholds
from sbretire.randomness import ResolvedSeed
from sbretire.spending import ScenarioSpending

from annual_fixtures import FIXTURE, hand_scenario, seeded
from scenario_helpers import set_at

FIXTURE_HASH = "69bab36469edb5d58d2c6d2086b5dbf8e9ac07c348f65ecb3a67fe421a55d589"  # pinned before F-019


def _raw() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def _with_budget(scenario: Scenario, **changes: object) -> Scenario:
    return scenario.model_copy(update={"budget": scenario.budget.model_copy(update=changes)})


def test_budget_spend_at_least_income_validated() -> None:
    assert parse_scenario(_raw(), base_dir=FIXTURE.parent).scenario.budget.spend_at_least_income is False
    on = parse_scenario(set_at(_raw(), "budget.spend_at_least_income", True), base_dir=FIXTURE.parent)
    assert on.scenario.budget.spend_at_least_income is True
    for bad in ("yes", 1, None):
        with pytest.raises(ScenarioError) as caught:
            parse_scenario(set_at(_raw(), "budget.spend_at_least_income", bad), base_dir=FIXTURE.parent)
        assert [issue.location for issue in caught.value.issues] == ["budget.spend_at_least_income"], bad


def test_spend_at_least_income_floors_spending_at_income() -> None:
    index = StochasticPriceIndex.constant(4, 5, 0.02)
    # paths: both alive · only alex (person 0) · only sam (person 1) · neither
    alive = np.array([[True, True, False, False], [True, False, True, False]])
    month = 30
    level = float(index.level(month)[0])
    for budget in (800.0, 1_000.0, 1_500.0, 2_000.0):
        base = _with_budget(hand_scenario(), monthly_amount_today=budget)
        on = _with_budget(base, spend_at_least_income=True)
        plain = ScenarioSpending(base, index).spending(month, alive)
        income = ScenarioIncome(base, index).income(month, alive)
        np.testing.assert_array_equal(ScenarioCashFlows(base, index, 4).spending(month, alive), plain)
        floored = ScenarioCashFlows(on, index, 4).spending(month, alive)
        np.testing.assert_allclose(floored, np.maximum(plain, income), rtol=1e-15)
        expected = [
            max(budget, 1_000.0) * level,
            max(0.7 * budget, 1_000.0) * level,
            max(0.65 * budget, 1_000.0) * level,
            0.0,
        ]
        np.testing.assert_allclose(floored, expected, rtol=1e-12)
    assert floored[0] == pytest.approx(2_000.0 * level)  # budget above income: budget-based spending
    assert floored[1] == pytest.approx(1_400.0 * level)


def test_config_sha256_spend_option_default_excluded() -> None:
    raw = _raw()
    assert config_sha256(parse_scenario(raw, base_dir=FIXTURE.parent).scenario) == FIXTURE_HASH
    off = set_at(raw, "budget.spend_at_least_income", False)
    assert config_sha256(parse_scenario(off, base_dir=FIXTURE.parent).scenario) == FIXTURE_HASH
    on = set_at(raw, "budget.spend_at_least_income", True)
    assert config_sha256(parse_scenario(on, base_dir=FIXTURE.parent).scenario) != FIXTURE_HASH


def _early_income_inputs(spend_at_least_income: bool) -> tuple[Scenario, RandomInputs]:
    """50,000 balance, zero return and inflation; 3,000/month income in months 0-23; both die in month 60."""
    raw = set_at(set_at(_raw(), "portfolio.starting_balance", 50_000), "portfolio.annual_return", 0.0)
    raw = set_at(raw, "model.horizon_years", 10)
    raw["income"] = [
        {
            "id": "pension",
            "name": "Pension",
            "start_date": "2026-10-01",
            "end_date": "2028-10-01",
            "annual_amount_today": 36_000,
            "inflation_linked": True,
            "survivor_percentage": 1.0,
            "recipient": "household",
        }
    ]
    raw = set_at(raw, "budget.spend_at_least_income", spend_at_least_income)
    scenario = parse_scenario(raw, base_dir=FIXTURE.parent).scenario
    deaths = np.full((2, 3), 60, dtype=np.int64)
    return scenario, RandomInputs(
        ResolvedSeed(0, "config"), deaths, StochasticPriceIndex.constant(3, 10, 0.0)
    )


def test_spend_at_least_income_closed_form() -> None:
    # off: the surplus 24 x (3,000 - B) is saved, so 50,000 + 72,000 - 60 B >= 0; on: months 0-23 spend
    # exactly the income, leaving 50,000 for the 36 months without income.
    for on, exact in ((False, (50_000 + 24 * 3_000) / 60), (True, 50_000 / 36)):
        scenario, inputs = _early_income_inputs(on)
        search = path_budget_thresholds(scenario, inputs)
        assert np.all((search.thresholds <= exact + 1e-6) & (search.thresholds > exact - BUDGET_TOLERANCE)), (
            on
        )
        [result] = maximum_sustainable_budgets(search, [0.5])
        assert result.estimated_success_probability == 1.0


def test_spend_at_least_income_budget_monotone() -> None:
    scenario, inputs = seeded(400, 3_000)
    scenario = _with_budget(scenario, spend_at_least_income=True)
    search = path_budget_thresholds(scenario, inputs)
    previous = np.ones(inputs.n_paths, dtype=np.bool_)
    for budget in np.linspace(250.0, 6_000.0, 24):
        outcomes = run_monte_carlo(scenario, inputs, monthly_budget_today=float(budget)).outcomes
        ok = classify_paths(outcomes) == PathClass.SUCCESSFUL
        assert not np.any(ok & ~previous), budget
        assert np.all(ok[search.thresholds >= budget]), budget
        assert not np.any(ok[search.thresholds + BUDGET_TOLERANCE < budget]), budget
        previous = ok
    assert previous.sum() < (search.thresholds > -np.inf).sum()
    plain = maximum_sustainable_budgets(
        path_budget_thresholds(_with_budget(scenario, spend_at_least_income=False), inputs), [0.9]
    )
    floored = maximum_sustainable_budgets(search, [0.9])
    assert (
        floored[0].maximum_monthly_budget_today is not None
        and plain[0].maximum_monthly_budget_today is not None
    )
    assert floored[0].maximum_monthly_budget_today <= plain[0].maximum_monthly_budget_today
