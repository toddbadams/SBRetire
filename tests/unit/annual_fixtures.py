"""Shared scenarios and random inputs for the annual-results tests (F-012).

A plain helper module (like ``scenario_helpers``) so test files never import each other — importing one test
module from another breaks IDE test discovery.

``hand_scenario`` + ``hand_inputs``: tests/fixtures/scenarios/valid_minimal.yaml with As-Of 2026-10, a 5-year
horizon (months 0-59), balance 50,000, budget 3,000, zero return, zero inflation and one household income of
1,000/month paid while anyone is alive. Path A: alex dies d=5, sam d=20 (Successful). Path B: alex d=60
(alive at the horizon), sam d=30; depletes in month 25 (Failed). Hand-derived rows: ``test_reporting_annual``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from sbretire.config import Scenario, parse_scenario
from sbretire.inflation import StochasticPriceIndex
from sbretire.monte_carlo import RandomInputs, draw_random_inputs
from sbretire.mortality import load_mortality_table
from sbretire.randomness import ResolvedSeed

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def hand_scenario() -> Scenario:
    raw: dict[str, Any] = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["model"].update(simulation_count=2, horizon_years=5)
    raw["portfolio"].update(starting_balance=50_000, annual_return=0.0)
    raw["inflation"].update(log_mean=0.0, innovation_sd=0.0, initial_rate=0.0)
    raw["income"] = [
        {
            "id": "rent",
            "name": "Rent",
            "start_date": "2026-10-01",
            "annual_amount_today": 12_000,
            "inflation_linked": True,
            "survivor_percentage": 1.0,
            "recipient": "household",
        }
    ]
    return parse_scenario(raw, base_dir=FIXTURE.parent).scenario


def hand_inputs() -> RandomInputs:
    deaths = np.array([[5, 60], [20, 30]], dtype=np.int64)
    return RandomInputs(ResolvedSeed(0, "config"), deaths, StochasticPriceIndex.constant(2, 5, 0.0))


def seeded(paths: int, budget: float) -> tuple[Scenario, RandomInputs]:
    """The fixture scenario with ``paths`` paths at ``budget``, real data files, seed 21."""
    raw: dict[str, Any] = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["model"]["simulation_count"] = paths
    raw["budget"]["monthly_amount_today"] = budget
    scenario = parse_scenario(raw, base_dir=FIXTURE.parent).scenario
    table = load_mortality_table(ROOT / "data" / "ons_mortality.csv")
    return scenario, draw_random_inputs(scenario, table, ResolvedSeed(21, "config"))
