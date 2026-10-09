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
from sbretire.spending import ScenarioSpending

from annual_fixtures import FIXTURE, hand_scenario
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
