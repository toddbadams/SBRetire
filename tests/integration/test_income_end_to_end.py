"""F-003.4 — engine + ScenarioIncome agree with a hand-computed income total (T2).

Zero return and zero spending, so the final balance is exactly the starting balance plus every payment
received. Fixture: tests/fixtures/scenarios/valid_minimal.yaml (As-Of 2026-10-01, start 500 000;
people alex=row 0, sam=row 1)
- pension_a: 1000/month from month 3, survivor 0.5 after alex dies (flat index, so linking is x1)
- annuity_b: 500/month months 0..161, recipient sam, survivor 0
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from sbretire.config import parse_scenario
from sbretire.income import ScenarioIncome
from sbretire.inflation import FlatPriceIndex
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.simulation import simulate_paths

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "valid_minimal.yaml"


class IncomeOnly:
    def __init__(self, income: ScenarioIncome) -> None:
        self._income = income

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        return self._income.income(month, alive)

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        return np.zeros(alive.shape[1], dtype=np.float64)


def test_income_end_to_end_matches_hand_total() -> None:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["portfolio"]["annual_return"] = 0.0
    scenario = parse_scenario(raw, base_dir=FIXTURE.parent).scenario
    horizon = 720
    death_month = np.array([[24, 400, 10_000], [300, 100, 10_000]], dtype=np.int64)

    out = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=death_month,
        horizon_months=horizon,
        cash_flows=IncomeOnly(ScenarioIncome(scenario, FlatPriceIndex(3))),
    )

    # path 0: alex dies 24, sam 300 -> pension 21 full months + 276 at 50%; annuity 162 months
    path_0 = 21 * 1000 + 276 * 500 + 162 * 500
    # path 1: sam dies 100, alex 400 -> pension full months 3..399;
    #         annuity only while sam lives (months 0..99)
    path_1 = 397 * 1000 + 100 * 500
    # path 2: both alive to the horizon -> pension months 3..719; annuity months 0..161
    path_2 = 717 * 1000 + 162 * 500
    expected = 500_000.0 + np.array([path_0, path_1, path_2], dtype=np.float64)

    np.testing.assert_allclose(out.final_balance, expected, rtol=0, atol=1e-6)
    assert out.household_end_month.tolist() == [300, 400, -1]
    assert out.depletion_month.tolist() == [-1, -1, -1]
