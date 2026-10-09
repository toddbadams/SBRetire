"""F-019 — End-of-Life Reserve: config, per-path index, reserve-aware metrics and budget search.

Hand fixture (``annual_fixtures.hand_scenario``): 5-year horizon, balance 50,000, budget 3,000, zero return,
one household income of 1,000/month. Inflation is injected through the random inputs.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import yaml

from sbretire.config import ScenarioError, parse_scenario
from sbretire.inflation import StochasticPriceIndex
from sbretire.metadata import config_sha256
from sbretire.metrics import PathClass, SuccessMetrics, classify_paths
from sbretire.monte_carlo import RandomInputs, required_end_balance, run_monte_carlo
from sbretire.randomness import ResolvedSeed
from sbretire.simulation import PathOutcomes

from annual_fixtures import FIXTURE, hand_scenario
from scenario_helpers import set_at

FIXTURE_HASH = "69bab36469edb5d58d2c6d2086b5dbf8e9ac07c348f65ecb3a67fe421a55d589"  # pinned before F-019


def _raw() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    return loaded


def test_budget_end_reserve_months_validated() -> None:
    assert parse_scenario(_raw(), base_dir=FIXTURE.parent).scenario.budget.end_reserve_months == 0
    twelve = parse_scenario(set_at(_raw(), "budget.end_reserve_months", 12), base_dir=FIXTURE.parent)
    assert twelve.scenario.budget.end_reserve_months == 12
    for bad in (-1, 1.5, "12", True):
        with pytest.raises(ScenarioError) as caught:
            parse_scenario(set_at(_raw(), "budget.end_reserve_months", bad), base_dir=FIXTURE.parent)
        assert [issue.location for issue in caught.value.issues] == ["budget.end_reserve_months"], bad


def test_price_index_level_at_matches_level() -> None:
    rates = np.random.Generator(np.random.PCG64(5)).uniform(-0.02, 0.12, size=(5, 7))
    index = StochasticPriceIndex(rates)
    for month in range(61):
        months = np.full(7, month, dtype=np.int64)
        np.testing.assert_allclose(index.level_at(months), index.level(month), rtol=1e-14)
    mixed = np.array([0, 11, 12, 13, 47, 59, 60], dtype=np.int64)
    expected = [index.level(int(month))[path] for path, month in enumerate(mixed)]
    np.testing.assert_allclose(index.level_at(mixed), expected, rtol=1e-14)
    with pytest.raises(ValueError):
        index.level_at(np.array([0, 0, 0, 0, 0, 0, 61], dtype=np.int64))


def _outcomes(final: list[float], depletion: list[int], censored: list[bool]) -> PathOutcomes:
    n = len(final)
    return PathOutcomes(
        depletion_month=np.array(depletion, dtype=np.int64),
        shortfall=np.zeros(n),
        household_end_month=np.where(np.array(censored), -1, 30).astype(np.int64),
        censored=np.array(censored),
        final_balance=np.array(final, dtype=np.float64),
    )


def test_classify_paths_end_reserve() -> None:
    outcomes = _outcomes(
        final=[100.0, 99.99, 500.0, 0.0, 800.0],
        depletion=[-1, -1, -1, 12, -1],
        censored=[False, False, False, False, True],
    )
    required = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
    v1 = [
        PathClass.SUCCESSFUL,
        PathClass.SUCCESSFUL,
        PathClass.SUCCESSFUL,
        PathClass.FAILED,
        PathClass.UNRESOLVED,
    ]
    assert list(classify_paths(outcomes)) == v1
    reserve = [
        PathClass.SUCCESSFUL,
        PathClass.FAILED,
        PathClass.SUCCESSFUL,
        PathClass.FAILED,
        PathClass.UNRESOLVED,
    ]
    assert list(classify_paths(outcomes, required)) == reserve
    metrics = SuccessMetrics.from_outcomes(outcomes, required)
    assert (metrics.n_successful, metrics.n_failed, metrics.n_unresolved) == (2, 2, 1)
    assert SuccessMetrics.from_outcomes(outcomes) == SuccessMetrics.from_outcomes(outcomes, np.zeros(5))


def test_required_end_balance_hand_computed() -> None:
    scenario = hand_scenario()
    deaths = np.array([[5, 60, 30], [20, 30, 30]], dtype=np.int64)  # Household End 20, censored, 30
    inputs = RandomInputs(ResolvedSeed(0, "config"), deaths, StochasticPriceIndex.constant(3, 5, 0.03))
    outcomes = run_monte_carlo(scenario, inputs).outcomes
    required = required_end_balance(inputs, outcomes, 3_000.0, 12)
    expected = [12 * 3_000 * 1.03 ** (20 / 12), 0.0, 12 * 3_000 * 1.03 ** (30 / 12)]
    np.testing.assert_allclose(required, expected, rtol=1e-12)
    np.testing.assert_allclose(required_end_balance(inputs, outcomes, 3_000.0, 0), 0.0)

    v1 = run_monte_carlo(scenario, inputs).metrics
    reserve = run_monte_carlo(scenario, inputs, end_reserve_months=12).metrics
    meets = (classify_paths(outcomes) == PathClass.SUCCESSFUL) & (outcomes.final_balance >= required)
    assert reserve.n_successful == int(meets.sum())
    assert reserve.n_unresolved == v1.n_unresolved == 1
    assert reserve.n_successful + reserve.n_failed == v1.n_successful + v1.n_failed
    budget = np.array([3_000.0, 3_000.0, 3_000.0])
    per_path = required_end_balance(inputs, outcomes, budget, 12)
    np.testing.assert_allclose(per_path, expected, rtol=1e-12)


def test_config_sha256_default_options_excluded() -> None:
    raw = _raw()
    assert config_sha256(parse_scenario(raw, base_dir=FIXTURE.parent).scenario) == FIXTURE_HASH
    explicit = set_at(raw, "budget.end_reserve_months", 0)
    assert config_sha256(parse_scenario(explicit, base_dir=FIXTURE.parent).scenario) == FIXTURE_HASH
    twelve = set_at(raw, "budget.end_reserve_months", 12)
    assert config_sha256(parse_scenario(twelve, base_dir=FIXTURE.parent).scenario) != FIXTURE_HASH
