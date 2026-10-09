"""Annual results: calendar-year rows aggregated as the engine runs (SPEC §12; simulation-conventions §8).

The collector only ever holds per-path state for the current year (shape (n_paths,)) and one finished row
per year, so memory does not grow with months × paths (SPEC §10.4). Money is nominal GBP; probabilities are
shares of paths.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario
from sbretire.metrics import PathClass, classify_paths
from sbretire.monte_carlo import RandomInputs
from sbretire.portfolio import BoolArray, FloatArray
from sbretire.simulation import PathOutcomes, simulate_paths
from sbretire.timeline import month_start

PERCENTILES: Final = (5, 25, 50, 75, 95)
ANNUAL_COLUMNS: Final = (
    "year",
    "months",
    "probability_both_alive",
    "probability_person_1_alive",
    "probability_person_2_alive",
    "monthly_budget_today",
    "monthly_budget_nominal_median",
    "annual_budget_nominal_median",
    "annual_income_median",
    "annual_net_withdrawal_median",
    "portfolio_p05",
    "portfolio_p25",
    "portfolio_median",
    "portfolio_p75",
    "portfolio_p95",
    "probability_not_depleted_yet",
    "estimated_lifetime_success_rate",
    "completed_paths",
    "unresolved_paths",
)


@dataclass(frozen=True)
class AnnualRow:
    """One calendar year of ``annual_results.csv`` (definitions: simulation-conventions §8)."""

    year: int
    months: int
    probability_both_alive: float
    probability_person_1_alive: float
    probability_person_2_alive: float
    monthly_budget_today: float
    monthly_budget_nominal_median: float
    annual_budget_nominal_median: float | None
    annual_income_median: float | None
    annual_net_withdrawal_median: float | None
    portfolio_p05: float | None
    portfolio_p25: float | None
    portfolio_median: float | None
    portfolio_p75: float | None
    portfolio_p95: float | None
    probability_not_depleted_yet: float
    estimated_lifetime_success_rate: float | None
    completed_paths: int
    unresolved_paths: int


@dataclass(frozen=True)
class _YearFlows:
    """Per-year statistics computed when the year closes (no per-path arrays kept)."""

    spending_median: float | None
    income_median: float | None
    net_withdrawal_median: float | None
    portfolio: tuple[float, ...] | None


class _RecordingCashFlows:
    """Passes cash flows through to the engine and remembers the current month's values."""

    def __init__(self, inner: ScenarioCashFlows) -> None:
        self._inner = inner
        self.last_income: FloatArray | None = None
        self.last_spending: FloatArray | None = None

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        self.last_income = self._inner.income(month, alive)
        return self.last_income

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        self.last_spending = self._inner.spending(month, alive)
        return self.last_spending


class _AnnualCollector:
    """Engine observer: accumulates this year's per-path flows and closes each year at its last month."""

    def __init__(self, scenario: Scenario, inputs: RandomInputs, flows: _RecordingCashFlows) -> None:
        self._flows = flows
        self._deaths = inputs.death_months
        n_paths = inputs.n_paths
        last_month = min(scenario.model.horizon_years * 12, int(self._deaths.max())) - 1
        self.months_by_year: dict[int, list[int]] = {}
        for month in range(last_month + 1):
            self.months_by_year.setdefault(month_start(scenario.model.as_of_date, month).year, []).append(
                month
            )
        self._year_of_end = {months[-1]: year for year, months in self.months_by_year.items()}
        self._spending = np.zeros(n_paths)
        self._income = np.zeros(n_paths)
        self._ran = np.zeros(n_paths, dtype=np.bool_)
        self.closed: dict[int, _YearFlows] = {}

    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None:
        assert self._flows.last_spending is not None and self._flows.last_income is not None
        self._spending += np.where(active, self._flows.last_spending, 0.0)
        self._income += np.where(active, self._flows.last_income, 0.0)
        self._ran |= active
        year = self._year_of_end.get(month)
        if year is not None:
            self._close(year, balance)

    def _close(self, year: int, balance: FloatArray) -> None:
        end = self.months_by_year[year][-1]
        in_scope = (end < self._deaths).any(axis=0)
        ran = self._ran
        self.closed[year] = _YearFlows(
            spending_median=float(np.median(self._spending[ran])) if ran.any() else None,
            income_median=float(np.median(self._income[ran])) if ran.any() else None,
            net_withdrawal_median=float(np.median((self._spending - self._income)[ran]))
            if ran.any()
            else None,
            portfolio=(
                tuple(float(v) for v in np.percentile(balance[in_scope], PERCENTILES))
                if in_scope.any()
                else None
            ),
        )
        self._spending[:] = 0.0
        self._income[:] = 0.0
        self._ran[:] = False

    def finish(self, outcomes: PathOutcomes) -> None:
        """Close the years the engine never reached (it stops once no path is running)."""
        for year in self.months_by_year:
            if year not in self.closed:
                self._close(year, outcomes.final_balance)


def annual_results(scenario: Scenario, inputs: RandomInputs) -> list[AnnualRow]:
    """Calendar-year rows for the configured Budget on ``inputs`` (simulation-conventions §8).

    Runs the engine once with a streaming observer; survival, depletion and lifetime outcomes come from the
    random inputs and the run's per-path outcomes.
    """
    flows = _RecordingCashFlows(ScenarioCashFlows(scenario, inputs.price_index, inputs.n_paths))
    collector = _AnnualCollector(scenario, inputs, flows)
    outcomes = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=inputs.death_months,
        horizon_months=scenario.model.horizon_years * 12,
        cash_flows=flows,
        observer=collector,
    )
    collector.finish(outcomes)

    deaths = inputs.death_months
    n_paths = inputs.n_paths
    successful = classify_paths(outcomes) == PathClass.SUCCESSFUL
    household_end = deaths.max(axis=0)
    budget = scenario.budget.monthly_amount_today
    rows = []
    for year, months in collector.months_by_year.items():
        end = months[-1]
        alive = end < deaths
        not_depleted = (outcomes.depletion_month < 0) | (outcomes.depletion_month > end)
        resolved = ~not_depleted | (household_end <= end)
        flows_year = collector.closed[year]
        portfolio = flows_year.portfolio or (None,) * len(PERCENTILES)
        rows.append(
            AnnualRow(
                year=year,
                months=len(months),
                probability_both_alive=float(alive.all(axis=0).mean()),
                probability_person_1_alive=float(alive[0].mean()),
                probability_person_2_alive=float(alive[1].mean()),
                monthly_budget_today=budget,
                monthly_budget_nominal_median=float(np.median(budget * inputs.price_index.level(end))),
                annual_budget_nominal_median=flows_year.spending_median,
                annual_income_median=flows_year.income_median,
                annual_net_withdrawal_median=flows_year.net_withdrawal_median,
                portfolio_p05=portfolio[0],
                portfolio_p25=portfolio[1],
                portfolio_median=portfolio[2],
                portfolio_p75=portfolio[3],
                portfolio_p95=portfolio[4],
                probability_not_depleted_yet=float(not_depleted.mean()),
                estimated_lifetime_success_rate=(
                    float(successful[not_depleted].mean()) if not_depleted.any() else None
                ),
                completed_paths=int(resolved.sum()),
                unresolved_paths=int(n_paths - resolved.sum()),
            )
        )
    return rows


def write_annual_results_csv(rows: Sequence[AnnualRow], path: Path) -> Path:
    raise NotImplementedError
