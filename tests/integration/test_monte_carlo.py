"""F-009.2 — random inputs drawn once, Monte Carlo run, SPEC §17.1/§17.2 scenarios (F-009 brief §2 #4, #7).

Fixture tests/fixtures/scenarios/valid_minimal.yaml (As-Of 2026-10, 60-year horizon, budget 3000/month, start
500,000, return 4 %) with the real ONS mortality and CPI files.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from sbretire.config import Scenario, load_scenario, parse_scenario
from sbretire.metrics import PathClass, SuccessMetrics, classify_paths
from sbretire.monte_carlo import RandomInputs, draw_random_inputs, run_monte_carlo
from sbretire.mortality import MortalityTable, load_mortality_table
from sbretire.randomness import ResolvedSeed

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"
EXAMPLE = ROOT / "tests" / "fixtures" / "scenarios" / "example_v1.yaml"  # frozen V1 example: pinned values
SEED = ResolvedSeed(7, "config")


def _raw() -> dict[str, Any]:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    raw["model"]["simulation_count"] = 2_000
    return raw


def _scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=FIXTURE.parent).scenario


@functools.cache
def _table() -> MortalityTable:
    return load_mortality_table(ROOT / "data" / "ons_mortality.csv")


def _inputs(scenario: Scenario, seed: ResolvedSeed = SEED) -> RandomInputs:
    return draw_random_inputs(scenario, _table(), seed)


def test_monte_carlo_fixed_seed_reproduces_outputs() -> None:
    scenario = _scenario(_raw())
    first = run_monte_carlo(scenario, _inputs(scenario))
    second = run_monte_carlo(scenario, _inputs(scenario))
    for name in ("depletion_month", "shortfall", "household_end_month", "censored", "final_balance"):
        np.testing.assert_array_equal(getattr(first.outcomes, name), getattr(second.outcomes, name))
    assert first.metrics == second.metrics
    assert first.metrics.n_paths == 2_000
    other = run_monte_carlo(scenario, _inputs(scenario, ResolvedSeed(8, "config")))
    assert not np.array_equal(first.outcomes.final_balance, other.outcomes.final_balance)


def test_monte_carlo_reuses_inputs_across_budgets() -> None:
    raw = _raw()
    low = _scenario(raw)
    raw["budget"]["monthly_amount_today"] = 4_000
    high = _scenario(raw)
    inputs = _inputs(low)
    deaths_before = inputs.death_months.copy()
    levels_before = [inputs.price_index.level(month).copy() for month in (0, 13, 300, 719)]

    at_low = run_monte_carlo(low, inputs)
    at_high = run_monte_carlo(high, inputs)

    np.testing.assert_array_equal(inputs.death_months, deaths_before)
    for month, level in zip((0, 13, 300, 719), levels_before, strict=True):
        np.testing.assert_array_equal(inputs.price_index.level(month), level)
    low_classes, high_classes = classify_paths(at_low.outcomes), classify_paths(at_high.outcomes)
    assert not np.any((high_classes == PathClass.SUCCESSFUL) & (low_classes != PathClass.SUCCESSFUL))
    assert not np.any((low_classes == PathClass.FAILED) & (high_classes != PathClass.FAILED))
    assert at_high.metrics.n_failed > at_low.metrics.n_failed  # the budget really changed the outcome
    np.testing.assert_array_equal(at_low.outcomes.censored, at_high.outcomes.censored)  # same deaths


def test_monte_carlo_zero_spending_never_fails() -> None:
    raw = _raw()
    raw["budget"]["monthly_amount_today"] = 0
    metrics = run_monte_carlo(_scenario(raw), _inputs(_scenario(raw))).metrics
    assert metrics.n_failed == 0

    raw["portfolio"]["starting_balance"] = 10_000_000
    rich = run_monte_carlo(_scenario(raw), _inputs(_scenario(raw)))
    assert rich.metrics.n_failed == 0
    assert rich.metrics.n_successful == rich.metrics.n_completed
    assert rich.metrics.completed_success_rate == 1.0
    assert np.all(rich.outcomes.final_balance >= 10_000_000)


def test_monte_carlo_no_capital_no_income_fails() -> None:
    raw = _raw()
    raw["portfolio"]["starting_balance"] = 0
    raw["income"] = []
    result = run_monte_carlo(_scenario(raw), _inputs(_scenario(raw)))
    assert result.metrics.n_failed == result.metrics.n_paths
    np.testing.assert_array_equal(result.outcomes.depletion_month, 0)
    assert result.metrics.conservative_success_rate == 0.0


def test_monte_carlo_example_snapshot() -> None:
    """Regression snapshot: example config at budget 11,000/month and a 30-year horizon (all three outcomes
    occur), seed 42, 2,000 paths. Values pinned when F-009.2 went green; a change means the model changed.
    """
    loaded = load_scenario(EXAMPLE).scenario
    model = loaded.model.model_copy(update={"simulation_count": 2_000, "horizon_years": 30})
    budget = loaded.budget.model_copy(update={"monthly_amount_today": 11_000})
    scenario = loaded.model_copy(update={"model": model, "budget": budget})
    result = run_monte_carlo(scenario, _inputs(scenario, ResolvedSeed(42, "config")))
    assert result.metrics == SuccessMetrics(
        n_paths=2_000,
        n_successful=725,
        n_failed=203,
        n_unresolved=1_072,
        n_completed=928,
        conservative_success_rate=0.3625,
        conservative_standard_error=0.010749273231246845,
        completed_success_rate=0.78125,
        completed_standard_error=0.013570475269133813,
        unresolved_share=0.536,
    )
    assert float(result.outcomes.final_balance.sum()) == pytest.approx(2_598_116_369.580387, rel=1e-9)
