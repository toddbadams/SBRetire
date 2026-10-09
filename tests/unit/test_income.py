"""F-003.3 — ScenarioIncome: dates, inflation linking, survivor rules (SPEC §8; configuration §3–§5).

Fixture (tests/fixtures/scenarios/valid_minimal.yaml), As-Of 2026-10-01; people alex (row 0), sam (row 1):
- pension_a: from 2027-01-01 (month 3), 12000/yr, inflation-linked, survivor 0.5, recipient alex
- annuity_b: 2024-04-01 .. 2040-04-01 exclusive (months <0 .. 162), 6000/yr, not linked, survivor 0,
  recipient sam
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sbretire.config import Scenario, parse_scenario
from sbretire.income import ScenarioIncome
from sbretire.inflation import FlatPriceIndex
from sbretire.portfolio import BoolArray, FloatArray

from scenario_helpers import set_at


class ScriptedPriceIndex:
    def __init__(self, fn: Callable[[int], FloatArray]) -> None:
        self.fn = fn

    def level(self, month: int) -> FloatArray:
        return self.fn(month)


# Alive patterns as columns: both alive | alex dead, sam alive | alex alive, sam dead | both dead
FOUR_STATES: BoolArray = np.array([[True, False, True, False], [True, True, False, False]])
ALL_ALIVE: BoolArray = np.ones((2, 2), dtype=np.bool_)


def scenario(raw: dict[str, Any], *, keep: tuple[int, ...] = (0, 1)) -> Scenario:
    raw = set_at(raw, "income", [raw["income"][i] for i in keep])
    return parse_scenario(raw, base_dir=Path(".")).scenario


def test_linked_income_tracks_price_index(valid_raw: dict[str, Any]) -> None:
    index = ScriptedPriceIndex(lambda m: np.array([1.0 + 0.01 * m, 2.0]))
    income = ScenarioIncome(scenario(valid_raw, keep=(0,)), index)

    assert income.income(2, ALL_ALIVE).tolist() == [0.0, 0.0]  # not started yet
    np.testing.assert_allclose(income.income(3, ALL_ALIVE), [1000.0 * 1.03, 2000.0])
    np.testing.assert_allclose(income.income(40, ALL_ALIVE), [1000.0 * 1.40, 2000.0])


def test_unlinked_income_is_nominally_constant(valid_raw: dict[str, Any]) -> None:
    index = ScriptedPriceIndex(lambda m: np.array([1.0 + m, 3.0]))
    income = ScenarioIncome(scenario(valid_raw, keep=(1,)), index)
    for month in (0, 1, 50, 161):
        np.testing.assert_allclose(income.income(month, ALL_ALIVE), [500.0, 500.0])


def test_income_starts_and_ends_on_configured_dates(valid_raw: dict[str, Any]) -> None:
    flat = FlatPriceIndex(2)
    pension = ScenarioIncome(scenario(valid_raw, keep=(0,)), flat)
    annuity = ScenarioIncome(scenario(valid_raw, keep=(1,)), flat)

    assert [pension.income(m, ALL_ALIVE)[0] for m in (0, 2, 3, 4)] == [0.0, 0.0, 1000.0, 1000.0]
    # annuity_b started before the As-Of date (pays from month 0) and ends exclusively at month 162
    assert [annuity.income(m, ALL_ALIVE)[0] for m in (0, 161, 162, 200)] == [500.0, 500.0, 0.0, 0.0]


def test_survivor_percentage_applies_only_after_recipient_death(valid_raw: dict[str, Any]) -> None:
    income = ScenarioIncome(scenario(valid_raw, keep=(0,)), FlatPriceIndex(4))
    # recipient alex: full while alex lives (even if sam has died), x0.5 once alex has died and sam lives
    assert income.income(12, FOUR_STATES).tolist() == [1000.0, 500.0, 1000.0, 0.0]


def test_recipient_dying_before_start_pays_survivor_from_start(valid_raw: dict[str, Any]) -> None:
    income = ScenarioIncome(scenario(valid_raw, keep=(0,)), FlatPriceIndex(1))
    alex_dead_from_month_0 = np.array([[False], [True]])
    assert [income.income(m, alex_dead_from_month_0)[0] for m in (0, 2, 3, 30)] == [0.0, 0.0, 500.0, 500.0]


def test_household_stream_survivor_rule(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "income[0].recipient", "household")
    raw = set_at(raw, "income[0].survivor_percentage", 0.25)
    income = ScenarioIncome(scenario(raw, keep=(0,)), FlatPriceIndex(4))
    assert income.income(12, FOUR_STATES).tolist() == [1000.0, 250.0, 250.0, 0.0]


def test_income_sums_streams_per_path(valid_raw: dict[str, Any]) -> None:
    income = ScenarioIncome(scenario(valid_raw), FlatPriceIndex(4))
    # both: 1000 + 500 | alex dead: 500 + 500 | sam dead: 1000 + 0 | none: 0
    assert income.income(5, FOUR_STATES).tolist() == [1500.0, 1000.0, 1000.0, 0.0]
    result = income.income(5, FOUR_STATES)
    assert result.dtype == np.float64 and result.shape == (4,)


def test_no_income_streams_pays_nothing(valid_raw: dict[str, Any]) -> None:
    income = ScenarioIncome(scenario(valid_raw, keep=()), FlatPriceIndex(3))
    assert income.income(0, np.ones((2, 3), dtype=np.bool_)).tolist() == [0.0, 0.0, 0.0]


def test_index_shape_must_match_alive(valid_raw: dict[str, Any]) -> None:
    income = ScenarioIncome(scenario(valid_raw, keep=(0,)), FlatPriceIndex(2))
    with pytest.raises(ValueError, match="paths"):
        income.income(5, FOUR_STATES)
