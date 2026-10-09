"""Monte Carlo run: random inputs drawn once, every Path simulated, outcomes summarised (SPEC §10, §11)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sbretire.config import Scenario
from sbretire.inflation import StochasticPriceIndex
from sbretire.metrics import SuccessMetrics
from sbretire.mortality import MortalityTable
from sbretire.randomness import ResolvedSeed
from sbretire.simulation import PathOutcomes


@dataclass(frozen=True)
class RandomInputs:
    seed: ResolvedSeed
    death_months: NDArray[np.int64]
    price_index: StochasticPriceIndex


def draw_random_inputs(scenario: Scenario, table: MortalityTable, seed: ResolvedSeed) -> RandomInputs:
    raise NotImplementedError


@dataclass(frozen=True)
class MonteCarloResult:
    outcomes: PathOutcomes
    metrics: SuccessMetrics


def run_monte_carlo(scenario: Scenario, inputs: RandomInputs) -> MonteCarloResult:
    raise NotImplementedError
