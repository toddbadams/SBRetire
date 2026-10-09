"""F-012.1 — streaming annual aggregation (simulation-conventions §8; SPEC §12).

Hand fixture (tests/fixtures/scenarios/valid_minimal.yaml, As-Of 2026-10, horizon 5 years = months 0-59,
balance 50,000, budget 3,000, zero return, zero inflation, one household income of 1,000/month paid while
anyone is alive; alex (person 1) alone -> household factor 0.70, sam (person 2) alone -> her own 0.65):
- Path A: alex dies d=5, sam d=20. Months 0-4 both alive: net 2,000; months 5-19 sam alone: spending 1,950,
  income 1,000, net 950. Balance 40,000 after month 4, 25,750 after month 19; Household End 20 (Successful).
- Path B: alex d=60 (alive at the horizon), sam d=30. Both alive: net 2,000/month; month 24 is funded exactly
  (2,000 + 1,000 = 3,000) and month 25 depletes (available 1,000 < 3,000, shortfall 2,000) -> Failed.
Calendar years: 2026 months 0-2, 2027 3-14, 2028 15-26, 2029 27-38, 2030 39-50, 2031 51-59. The engine stops
after month 25 (no path running at month 26), so the 2028 row is finished from the final state.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario
from sbretire.metrics import PathClass, classify_paths
from sbretire.monte_carlo import RandomInputs
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.reporting import AnnualRow, annual_results
from sbretire.timeline import month_start

from annual_fixtures import hand_inputs, hand_scenario, seeded

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def _row(**values: Any) -> dict[str, Any]:
    return values


def test_annual_results_hand_computed_fixture() -> None:
    rows = {row.year: row for row in annual_results(hand_scenario(), hand_inputs())}
    assert list(rows) == [2026, 2027, 2028, 2029, 2030, 2031]
    common = {"monthly_budget_today": 3_000.0, "monthly_budget_nominal_median": 3_000.0}
    expected = {
        2026: _row(
            months=3,
            probability_both_alive=1.0,
            probability_person_1_alive=1.0,
            probability_person_2_alive=1.0,
            annual_budget_nominal_median=9_000.0,
            annual_income_median=3_000.0,
            annual_net_withdrawal_median=6_000.0,
            portfolio=[44_000.0] * 5,
            probability_not_depleted_yet=1.0,
            estimated_lifetime_success_rate=0.5,
            completed_paths=0,
            unresolved_paths=2,
        ),
        2027: _row(
            months=12,
            probability_both_alive=0.5,
            probability_person_1_alive=0.5,
            probability_person_2_alive=1.0,
            annual_budget_nominal_median=(25_500 + 36_000) / 2,
            annual_income_median=12_000.0,
            annual_net_withdrawal_median=(13_500 + 24_000) / 2,
            portfolio=[20_525.0, 22_625.0, 25_250.0, 27_875.0, 29_975.0],
            probability_not_depleted_yet=1.0,
            estimated_lifetime_success_rate=0.5,
            completed_paths=0,
            unresolved_paths=2,
        ),
        2028: _row(
            months=12,
            probability_both_alive=0.5,
            probability_person_1_alive=0.5,
            probability_person_2_alive=0.5,
            annual_budget_nominal_median=(9_750 + 33_000) / 2,
            annual_income_median=(5_000 + 11_000) / 2,
            annual_net_withdrawal_median=(4_750 + 22_000) / 2,
            portfolio=[0.0] * 5,
            probability_not_depleted_yet=0.5,
            estimated_lifetime_success_rate=1.0,
            completed_paths=2,
            unresolved_paths=0,
        ),
    }
    for year in (2029, 2030, 2031):
        expected[year] = _row(months=12 if year < 2031 else 9, probability_both_alive=0.0,
                              probability_person_1_alive=0.5, probability_person_2_alive=0.0,
                              annual_budget_nominal_median=None, annual_income_median=None,
                              annual_net_withdrawal_median=None, portfolio=[0.0] * 5,
                              probability_not_depleted_yet=0.5, estimated_lifetime_success_rate=1.0,
                              completed_paths=2, unresolved_paths=0)  # fmt: skip
    for year, values in expected.items():
        row = rows[year]
        portfolio = values.pop("portfolio")
        assert [
            row.portfolio_p05,
            row.portfolio_p25,
            row.portfolio_median,
            row.portfolio_p75,
            row.portfolio_p95,
        ] == (pytest.approx(portfolio)), year
        for name, value in {**common, **values}.items():
            assert getattr(row, name) == (value if value is None else pytest.approx(value)), (year, name)


class _History:
    """Records every month × path value (test only) to recompute rows independently."""

    def __init__(self, flows: ScenarioCashFlows) -> None:
        self.flows = flows
        self.income: list[FloatArray] = []
        self.spending: list[FloatArray] = []
        self.balance: list[FloatArray] = []
        self.active: list[BoolArray] = []

    def income_due(self, month: int, alive: BoolArray) -> FloatArray:
        value = self.flows.income(month, alive)
        self.income.append(value.copy())
        return value

    def spending_due(self, month: int, alive: BoolArray) -> FloatArray:
        value = self.flows.spending(month, alive)
        self.spending.append(value.copy())
        return value

    def observe(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None:
        self.balance.append(balance.copy())
        self.active.append(active.copy())


def _recompute(scenario: Scenario, inputs: RandomInputs) -> list[dict[str, Any]]:
    from sbretire.simulation import simulate_paths

    history = _History(ScenarioCashFlows(scenario, inputs.price_index, inputs.n_paths))

    class _Flows:
        def income(self, month: int, alive: BoolArray) -> FloatArray:
            return history.income_due(month, alive)

        def spending(self, month: int, alive: BoolArray) -> FloatArray:
            return history.spending_due(month, alive)

    outcomes = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=inputs.death_months,
        horizon_months=scenario.model.horizon_years * 12,
        cash_flows=_Flows(),
        observer=history.observe,
    )
    n = inputs.n_paths
    observed = len(history.balance)
    deaths = inputs.death_months
    last_month = min(scenario.model.horizon_years * 12, int(deaths.max())) - 1
    classes = classify_paths(outcomes)
    years: dict[int, list[int]] = {}
    for month in range(last_month + 1):
        years.setdefault(month_start(scenario.model.as_of_date, month).year, []).append(month)
    out = []
    for year, months in years.items():
        end = months[-1]
        alive = end < deaths
        ran = [m for m in months if m < observed]
        spend = np.zeros(n)
        income = np.zeros(n)
        ran_any = np.zeros(n, dtype=bool)
        for m in ran:
            spend += np.where(history.active[m], history.spending[m], 0.0)
            income += np.where(history.active[m], history.income[m], 0.0)
            ran_any |= history.active[m]
        balance = history.balance[end] if end < observed else outcomes.final_balance
        in_scope = alive.any(axis=0)
        not_depleted = (outcomes.depletion_month < 0) | (outcomes.depletion_month > end)
        resolved = ~not_depleted | (deaths.max(axis=0) <= end)

        def median(values: NDArray[np.float64], ran_any: BoolArray = ran_any) -> float | None:
            return float(np.median(values[ran_any])) if ran_any.any() else None

        successful = classes == PathClass.SUCCESSFUL
        out.append(
            {
                "year": year,
                "months": len(months),
                "probability_both_alive": float(alive.all(axis=0).mean()),
                "probability_person_1_alive": float(alive[0].mean()),
                "probability_person_2_alive": float(alive[1].mean()),
                "monthly_budget_nominal_median": float(
                    np.median(scenario.budget.monthly_amount_today * inputs.price_index.level(end))
                ),
                "annual_budget_nominal_median": median(spend),
                "annual_income_median": median(income),
                "annual_net_withdrawal_median": median(spend - income),
                "portfolio_p05": float(np.percentile(balance[in_scope], 5)) if in_scope.any() else None,
                "portfolio_median": float(np.percentile(balance[in_scope], 50)) if in_scope.any() else None,
                "portfolio_p95": float(np.percentile(balance[in_scope], 95)) if in_scope.any() else None,
                "probability_not_depleted_yet": float(not_depleted.mean()),
                "estimated_lifetime_success_rate": (
                    float(successful[not_depleted].mean()) if not_depleted.any() else None
                ),
                "completed_paths": int(resolved.sum()),
                "unresolved_paths": int(n - resolved.sum()),
            }
        )
    return out


def test_annual_results_match_full_history_recomputation() -> None:
    scenario, inputs = seeded(300, 3_800)
    rows = annual_results(scenario, inputs)
    expected = _recompute(scenario, inputs)
    assert [row.year for row in rows] == [values["year"] for values in expected]
    for row, values in zip(rows, expected, strict=True):
        for name, value in values.items():
            actual = getattr(row, name)
            if value is None:
                assert actual is None, (row.year, name)
            else:
                assert actual == pytest.approx(value, rel=1e-9, abs=1e-9), (row.year, name, actual, value)
    assert any(row.probability_not_depleted_yet < 1 for row in rows)  # some paths deplete: a real test


def test_annual_results_row_span() -> None:
    scenario, inputs = seeded(200, 3_000)
    rows = annual_results(scenario, inputs)
    last_alive_month = min(scenario.model.horizon_years * 12, int(inputs.death_months.max())) - 1
    assert rows[0].year == 2026 and rows[0].months == 3
    assert rows[-1].year == month_start(scenario.model.as_of_date, last_alive_month).year
    assert sum(row.months for row in rows) == last_alive_month + 1
    assert all(isinstance(row, AnnualRow) for row in rows)
    # the hand fixture's engine stops at month 26; later years are still produced (and finished correctly)
    fixture_rows = annual_results(hand_scenario(), hand_inputs())
    assert [row.year for row in fixture_rows][-1] == 2031
    assert math.isclose(sum(row.months for row in fixture_rows), 60)
