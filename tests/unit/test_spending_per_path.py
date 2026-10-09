"""F-010.1 — a per-path Budget through spending, cash flows and the Monte Carlo run (F-010 brief §2 #7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario, parse_scenario
from sbretire.inflation import StochasticPriceIndex
from sbretire.monte_carlo import draw_random_inputs, run_monte_carlo
from sbretire.mortality import load_mortality_table
from sbretire.randomness import ResolvedSeed
from sbretire.spending import ScenarioSpending

from scenario_helpers import set_at

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"


def _scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=FIXTURES).scenario


def test_spending_per_path_budget(valid_raw: dict[str, Any]) -> None:
    scenario = _scenario(valid_raw)  # alex alone -> household factor 0.70; sam alone -> own 0.65
    index = StochasticPriceIndex(np.array([[0.0, 0.10, 0.02]]))  # 1 year, 3 paths
    budgets = np.array([1000.0, 2000.0, 0.0])
    spending = ScenarioSpending(scenario, index, monthly_budget_today=budgets)
    both = np.ones((2, 3), dtype=bool)
    alex_alone = np.array([[True, True, True], [False, False, False]])
    sam_alone = np.array([[False, False, False], [True, True, True]])
    for month in (0, 6, 12):
        level = index.level(month)
        np.testing.assert_allclose(spending.spending(month, both), budgets * level, rtol=1e-14)
        np.testing.assert_allclose(spending.spending(month, alex_alone), budgets * level * 0.70, rtol=1e-14)
        np.testing.assert_allclose(spending.spending(month, sam_alone), budgets * level * 0.65, rtol=1e-14)
    flows = ScenarioCashFlows(scenario, index, n_paths=3, monthly_budget_today=budgets)
    np.testing.assert_allclose(flows.spending(6, both), budgets * index.level(6), rtol=1e-14)


def test_spending_default_budget_unchanged(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "model.simulation_count", 300)
    scenario = _scenario(raw)
    table = load_mortality_table(scenario.mortality.data_file)
    inputs = draw_random_inputs(scenario, table, ResolvedSeed(5, "config"))
    default = run_monte_carlo(scenario, inputs)
    scalar = run_monte_carlo(scenario, inputs, monthly_budget_today=scenario.budget.monthly_amount_today)
    array = run_monte_carlo(
        scenario, inputs, monthly_budget_today=np.full(300, scenario.budget.monthly_amount_today)
    )
    for other in (scalar, array):
        np.testing.assert_array_equal(other.outcomes.final_balance, default.outcomes.final_balance)
        np.testing.assert_array_equal(other.outcomes.depletion_month, default.outcomes.depletion_month)
        assert other.metrics == default.metrics


@pytest.mark.parametrize(
    "budget", [np.array([1000.0, 2000.0]), np.array([1000.0, -1.0, 5.0]), np.array([1.0, np.nan, 2.0]), -5.0]
)
def test_spending_rejects_bad_budget(valid_raw: dict[str, Any], budget: Any) -> None:
    index = StochasticPriceIndex(np.zeros((1, 3)))
    with pytest.raises(ValueError, match="monthly_budget_today"):
        ScenarioSpending(_scenario(valid_raw), index, monthly_budget_today=budget)
