"""Annual results: calendar-year rows aggregated as the engine runs (SPEC §12; simulation-conventions §8)."""

from __future__ import annotations

from dataclasses import dataclass

from sbretire.config import Scenario
from sbretire.monte_carlo import RandomInputs


@dataclass(frozen=True)
class AnnualRow:
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


def annual_results(scenario: Scenario, inputs: RandomInputs) -> list[AnnualRow]:
    raise NotImplementedError
