"""F-004.2 — a Scenario drives the engine end to end; outcome matches hand arithmetic (T2).

Fixture tests/fixtures/scenarios/valid_minimal.yaml with annual_return 0 and a flat price index:
- start 500 000; budget 3000/month
- survivor factors: sam alone 0.65 (own), alex alone 0.70 (household default)
- pension_a 1000/month from month 3 (x0.5 after alex dies)
- annuity_b 500/month months 0..161 while sam lives
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import parse_scenario
from sbretire.inflation import FlatPriceIndex
from sbretire.simulation import simulate_paths

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "valid_minimal.yaml"


def test_cash_flows_end_to_end_matches_hand_total() -> None:
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw["portfolio"]["annual_return"] = 0.0
    scenario = parse_scenario(raw, base_dir=FIXTURE.parent).scenario
    death_month = np.array([[24, 400, 10_000], [300, 100, 10_000]], dtype=np.int64)

    out = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=0.0,
        death_month=death_month,
        horizon_months=720,
        cash_flows=ScenarioCashFlows(scenario, FlatPriceIndex(3), n_paths=3),
    )

    # Path 0: alex dies 24, sam 300. Income 240 000 (see test_income_end_to_end);
    #   spending 24 x 3000 (both) + 276 x 1950 (sam alone) = 610 200.
    path_0 = 500_000 + 240_000 - (24 * 3000 + 276 * 1950)
    # Path 1: sam dies 100, alex 400. Income 447 000; spending 100 x 3000 + 300 x 2100 (alex alone) = 930 000.
    path_1 = 500_000 + 447_000 - (100 * 3000 + 300 * 2100)
    # Path 2: both alive. Net -2500 in months 0-2, -1500 in months 3-161, -2000 from month 162:
    #   after month 161: 500 000 - 3*2500 - 159*1500 = 254 000
    #   after month 288: 254 000 - 127*2000 = 0 (funded exactly: 2000 + 1000 income == 3000)
    #   month 289: 0 + 1000 < 3000 -> depleted, shortfall 2000
    assert out.final_balance.tolist() == [path_0, path_1, 0.0]
    assert [path_0, path_1] == [129_800, 17_000]
    assert out.depletion_month.tolist() == [-1, -1, 289]
    assert out.shortfall.tolist() == [0.0, 0.0, 2000.0]
    assert out.household_end_month.tolist() == [300, 400, -1]
