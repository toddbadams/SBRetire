"""F-006.4 — a deterministic inflation fixture produces the expected nominal spending (SPEC §17.2).

Fixture tests/fixtures/scenarios/valid_minimal.yaml with σ = 0, μ = log 1.03, φ = 0, initial rate 0.03, so
every simulated year's rate is exactly 3 % and I_t = 1.03^(t/12) (simulation-conventions §5). Budget
3000/month; alex alone uses the household survivor factor 0.70.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import parse_scenario
from sbretire.inflation import build_price_index
from sbretire.randomness import RandomStreams, ResolvedSeed

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "valid_minimal.yaml"


def test_deterministic_inflation_fixture_expected_nominal_spending() -> None:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["inflation"].update(
        log_mean=math.log(1.03), ar1_coefficient=0.0, innovation_sd=0.0, initial_rate=0.03
    )
    scenario = parse_scenario(raw, base_dir=FIXTURE.parent).scenario
    rng = RandomStreams.from_seed(ResolvedSeed(42, "config")).inflation
    index = build_price_index(scenario, rng, n_paths=2)
    flows = ScenarioCashFlows(scenario, index, n_paths=2)

    both_alive = np.array([[True, True], [True, True]])
    alex_alone = np.array([[True, True], [False, False]])
    for month in (0, 6, 12, 30):
        expected = 3000 * 1.03 ** (month / 12)
        np.testing.assert_allclose(flows.spending(month, both_alive), [expected, expected], rtol=1e-12)
        np.testing.assert_allclose(flows.spending(month, alex_alone), [0.7 * expected] * 2, rtol=1e-12)
    assert flows.spending(30, both_alive)[0] == pytest.approx(3000 * 1.03**2.5, rel=1e-12)
