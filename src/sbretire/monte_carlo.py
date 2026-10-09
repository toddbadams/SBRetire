"""Monte Carlo run: random inputs drawn once, every Path simulated, outcomes summarised (SPEC §10, §11)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario
from sbretire.inflation import StochasticPriceIndex, build_price_index
from sbretire.metrics import SuccessMetrics
from sbretire.mortality import MortalityTable, sample_death_months
from sbretire.portfolio import FloatArray
from sbretire.randomness import RandomStreams, ResolvedSeed
from sbretire.simulation import PathOutcomes, simulate_paths


@dataclass(frozen=True)
class RandomInputs:
    """Every random draw a run needs, made once and reused unchanged across candidates (CRN).

    ``death_months`` is (2, n_paths) in ``scenario.people`` order; ``price_index`` covers the whole horizon.
    """

    seed: ResolvedSeed
    death_months: NDArray[np.int64]
    price_index: StochasticPriceIndex

    @property
    def n_paths(self) -> int:
        return int(self.death_months.shape[1])


def draw_random_inputs(scenario: Scenario, table: MortalityTable, seed: ResolvedSeed) -> RandomInputs:
    """Draw ``model.simulation_count`` Paths from the seed's mortality and inflation Random Streams."""
    streams = RandomStreams.from_seed(seed)
    n_paths = scenario.model.simulation_count
    death_months = sample_death_months(scenario, table, streams.mortality, n_paths)
    death_months.flags.writeable = False
    price_index = build_price_index(scenario, streams.inflation, n_paths)
    return RandomInputs(seed=seed, death_months=death_months, price_index=price_index)


@dataclass(frozen=True)
class MonteCarloResult:
    outcomes: PathOutcomes
    metrics: SuccessMetrics


def run_monte_carlo(
    scenario: Scenario, inputs: RandomInputs, monthly_budget_today: float | FloatArray | None = None
) -> MonteCarloResult:
    """Simulate every Path of ``inputs`` with the Scenario's cash flows and summarise them (no new draws).

    ``monthly_budget_today`` overrides the Budget (today's GBP/month), as a scalar or per path (F-010).
    """
    cash_flows = ScenarioCashFlows(scenario, inputs.price_index, inputs.n_paths, monthly_budget_today)
    outcomes = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=inputs.death_months,
        horizon_months=scenario.model.horizon_years * 12,
        cash_flows=cash_flows,
    )
    return MonteCarloResult(outcomes=outcomes, metrics=SuccessMetrics.from_outcomes(outcomes))
