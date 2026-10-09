"""F-015 — deterministic preview (F-015 brief).

Fixture tests/fixtures/scenarios/valid_minimal.yaml: As-Of 2026-10-01, horizon 60 years (720 months);
alex born 1958-03-01 (68 at As-Of), sam born 1962-07-15 (64 at As-Of).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sbretire.config import Scenario, parse_scenario
from sbretire.preview import death_months_from_ages


def scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=Path(".")).scenario


def test_death_months_from_ages_uses_birthday_month(valid_raw: dict[str, Any]) -> None:
    months = death_months_from_ages(scenario(valid_raw), (90, 90))
    # alex 90 -> 2048-03 = (2048-2026)*12 + (3-10) = 257; sam 90 -> 2052-07 = 26*12 - 3 = 309
    assert months.shape == (2, 1)
    assert months[:, 0].tolist() == [257, 309]
    assert death_months_from_ages(scenario(valid_raw), (69, 65))[:, 0].tolist() == [5, 9]


def test_death_months_from_ages_validates_range(valid_raw: dict[str, Any]) -> None:
    s = scenario(valid_raw)
    for ages in ((68, 90), (90, 64), (0, 90), (-5, 90)):
        with pytest.raises(ValueError, match="current age"):
            death_months_from_ages(s, ages)
    # beyond the horizon: alex 130 -> 2088-03 = 737 >= 720 (alive at the horizon)
    assert death_months_from_ages(s, (130, 130))[0, 0] >= 720
