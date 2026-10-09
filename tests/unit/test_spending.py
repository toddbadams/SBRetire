"""F-004.1 — ScenarioSpending: S_t = B_m × I_t × F_t (SPEC §6; configuration §6).

Fixture budget: 3000/month today, household survivor factor 0.7; alex (row 0) has no override,
sam (row 1) has survivor_budget_factor 0.65.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from sbretire.config import Scenario, parse_scenario
from sbretire.inflation import FlatPriceIndex
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.spending import ScenarioSpending

from scenario_helpers import delete_at, set_at

# Columns: both alive | alex dead (sam survives) | sam dead (alex survives) | both dead
FOUR_STATES: BoolArray = np.array([[True, False, True, False], [True, True, False, False]])


class ScriptedPriceIndex:
    def __init__(self, fn: Callable[[int], FloatArray]) -> None:
        self.fn = fn

    def level(self, month: int) -> FloatArray:
        return self.fn(month)


def scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=Path(".")).scenario


def test_spending_tracks_price_index_while_both_alive(valid_raw: dict[str, Any]) -> None:
    index = ScriptedPriceIndex(lambda m: np.array([1.0, 1.5]) * (1 + 0.01 * m))
    spending = ScenarioSpending(scenario(valid_raw), index)
    both = np.ones((2, 2), dtype=np.bool_)
    np.testing.assert_allclose(spending.spending(0, both), [3000.0, 4500.0])
    np.testing.assert_allclose(spending.spending(10, both), [3000.0 * 1.1, 4500.0 * 1.1])


def test_spending_changes_after_first_death_by_survivor_factor(valid_raw: dict[str, Any]) -> None:
    spending = ScenarioSpending(scenario(valid_raw), FlatPriceIndex(4))
    # sam survives -> sam's own 0.65; alex survives -> no override -> household 0.7
    np.testing.assert_allclose(spending.spending(5, FOUR_STATES), [3000.0, 1950.0, 2100.0, 0.0])


def test_survivor_factor_precedence_uses_survivor_then_default(valid_raw: dict[str, Any]) -> None:
    alex_override = set_at(valid_raw, "people[0].survivor_budget_factor", 0.8)
    spending = ScenarioSpending(scenario(alex_override), FlatPriceIndex(4))
    np.testing.assert_allclose(spending.spending(5, FOUR_STATES), [3000.0, 1950.0, 2400.0, 0.0])

    no_overrides = delete_at(valid_raw, "people[1].survivor_budget_factor")
    spending = ScenarioSpending(scenario(no_overrides), FlatPriceIndex(4))
    np.testing.assert_allclose(spending.spending(5, FOUR_STATES), [3000.0, 2100.0, 2100.0, 0.0])


def test_spending_zero_when_both_dead(valid_raw: dict[str, Any]) -> None:
    index = ScriptedPriceIndex(lambda m: np.full(4, 2.0))
    spending = ScenarioSpending(scenario(valid_raw), index)
    result = spending.spending(30, FOUR_STATES)
    np.testing.assert_allclose(result, [6000.0, 3900.0, 4200.0, 0.0])
    assert result.dtype == np.float64 and result.shape == (4,)
