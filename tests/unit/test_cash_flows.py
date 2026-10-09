"""F-004.2 — ScenarioCashFlows composes income and spending for the engine (F-004 brief §2 #5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import parse_scenario
from sbretire.income import ScenarioIncome
from sbretire.inflation import FlatPriceIndex
from sbretire.simulation import HouseholdCashFlows, simulate_paths
from sbretire.spending import ScenarioSpending

FOUR_STATES = np.array([[True, False, True, False], [True, True, False, False]])


def test_scenario_cash_flows_delegates_income_and_spending(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(valid_raw, base_dir=Path(".")).scenario
    index = FlatPriceIndex(4)
    flows: HouseholdCashFlows = ScenarioCashFlows(scenario, index, n_paths=4)
    income, spending = ScenarioIncome(scenario, index), ScenarioSpending(scenario, index)

    for month in (0, 3, 100, 161, 162):
        np.testing.assert_array_equal(flows.income(month, FOUR_STATES), income.income(month, FOUR_STATES))
        np.testing.assert_array_equal(
            flows.spending(month, FOUR_STATES), spending.spending(month, FOUR_STATES)
        )

    out = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=np.array([[12, 10_000], [10_000, 6]], dtype=np.int64),
        horizon_months=24,
        cash_flows=ScenarioCashFlows(scenario, FlatPriceIndex(2), n_paths=2),
    )
    assert out.final_balance.shape == (2,)


def test_scenario_cash_flows_rejects_mismatched_price_index(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(valid_raw, base_dir=Path(".")).scenario
    with pytest.raises(ValueError, match="paths"):
        ScenarioCashFlows(scenario, FlatPriceIndex(3), n_paths=4)
