"""F-001.1 — field-level validation of the Scenario (SPEC §4.2, §4.3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from sbretire.config import Scenario, ScenarioError, ScenarioIssue, parse_scenario

from scenario_helpers import delete_at, set_at

REQUIRED_KEYS = [
    "model",
    "portfolio",
    "budget",
    "inflation",
    "mortality",
    "people",
    "model.currency",
    "model.as_of_date",
    "model.simulation_count",
    "model.confidence_levels",
    "model.frequency",
    "model.horizon_years",
    "model.random_seed",
    "portfolio.starting_balance",
    "portfolio.annual_return",
    "budget.monthly_amount_today",
    "budget.survivor_budget_factor",
    "inflation.source",
    "inflation.source_period",
    "inflation.annual_mean",
    "inflation.annual_standard_deviation",
    "inflation.model",
    "inflation.parameter_units",
    "mortality.source",
    "mortality.geography",
    "mortality.projection",
    "mortality.data_file",
    "people[0].id",
    "people[0].name",
    "people[0].date_of_birth",
    "people[0].sex",
    "income[0].id",
    "income[0].name",
    "income[0].start_date",
    "income[0].annual_amount_today",
    "income[0].inflation_linked",
    "income[0].survivor_percentage",
    "income[0].recipient",
]


def issues_for(raw: dict[str, Any]) -> tuple[ScenarioIssue, ...]:
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(raw, base_dir=Path("."))
    return exc.value.issues


def locations(raw: dict[str, Any]) -> list[str]:
    return [issue.location for issue in issues_for(raw)]


def test_parse_valid_minimal_returns_typed_scenario(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(valid_raw, base_dir=Path(".")).scenario
    assert isinstance(scenario, Scenario)
    assert scenario.model.as_of_date == date(2026, 10, 1)
    assert scenario.model.confidence_levels == (0.90, 0.95)
    assert scenario.model.unknown_keys == "error"
    assert scenario.portfolio.starting_balance == 500000.0
    assert isinstance(scenario.portfolio.starting_balance, float)
    assert scenario.people[1].survivor_budget_factor == 0.65
    assert scenario.people[0].survivor_budget_factor is None
    assert scenario.income[0].end_date is None
    assert scenario.income[1].end_date == date(2040, 4, 1)
    assert scenario.income[0].inflation_linked is True


def test_scenario_is_immutable(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(valid_raw, base_dir=Path(".")).scenario
    with pytest.raises(ValueError, match="frozen"):
        scenario.portfolio.starting_balance = 1.0  # type: ignore[misc]


def test_income_section_is_optional(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(delete_at(valid_raw, "income"), base_dir=Path(".")).scenario
    assert scenario.income == ()


def test_random_seed_may_be_null(valid_raw: dict[str, Any]) -> None:
    scenario = parse_scenario(set_at(valid_raw, "model.random_seed", None), base_dir=Path(".")).scenario
    assert scenario.model.random_seed is None


@pytest.mark.parametrize("path", REQUIRED_KEYS)
def test_missing_required_field_reports_location(valid_raw: dict[str, Any], path: str) -> None:
    issues = issues_for(delete_at(valid_raw, path))
    assert [issue.location for issue in issues] == [path]
    assert "required" in issues[0].message


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("portfolio.annual_return", "0.05"),
        ("portfolio.starting_balance", True),
        ("income[0].inflation_linked", "yes"),
        ("income[0].inflation_linked", 1),
        ("model.simulation_count", "100"),
        ("model.simulation_count", 100.0),
        ("model.simulation_count", True),
        ("model.random_seed", 7.5),
        ("model.as_of_date", "01/10/2026"),
        ("model.as_of_date", "2026-10-01T00:00:00"),
        ("people[0].date_of_birth", 19580301),
        ("people[0].name", 42),
        ("model.confidence_levels", "0.9"),
    ],
)
def test_strict_scalars_reject_coercion(valid_raw: dict[str, Any], path: str, value: object) -> None:
    assert locations(set_at(valid_raw, path, value))[0].startswith(path)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("portfolio.starting_balance", -1),
        ("portfolio.annual_return", -1.0),
        ("portfolio.annual_return", -1.5),
        ("budget.monthly_amount_today", -0.01),
        ("budget.survivor_budget_factor", -0.1),
        ("people[1].survivor_budget_factor", -0.1),
        ("income[0].annual_amount_today", -5),
        ("income[0].survivor_percentage", 1.5),
        ("income[0].survivor_percentage", -0.1),
        ("inflation.annual_standard_deviation", -0.01),
        ("model.confidence_levels", [0.9, 1.0]),
        ("model.confidence_levels", [0.0]),
        ("model.confidence_levels", []),
        ("model.confidence_levels", [0.9, 0.9]),
        ("model.simulation_count", 0),
        ("model.horizon_years", -3),
        ("model.random_seed", -1),
        ("model.currency", "USD"),
        ("model.frequency", "annual"),
        ("model.unknown_keys", "ignore"),
        ("people[0].sex", "M"),
        ("people[0].id", ""),
        ("income[0].id", ""),
    ],
)
def test_out_of_range_values_rejected(valid_raw: dict[str, Any], path: str, value: object) -> None:
    assert locations(set_at(valid_raw, path, value))[0].startswith(path)


def test_all_issues_reported_together(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "portfolio.annual_return", -2)
    raw = set_at(raw, "income[1].survivor_percentage", 2)
    raw = delete_at(raw, "model.horizon_years")

    with pytest.raises(ScenarioError) as exc:
        parse_scenario(raw, base_dir=Path("."))

    assert [issue.location for issue in exc.value.issues] == [
        "income[1].survivor_percentage",
        "model.horizon_years",
        "portfolio.annual_return",
    ]
    lines = str(exc.value).splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("income[1].survivor_percentage: ")
    assert "2" in lines[0]  # the offending value is echoed back


def test_config_accepts_128_bit_random_seed(valid_raw: dict[str, Any]) -> None:
    seed = 2**128 - 1
    scenario = parse_scenario(set_at(valid_raw, "model.random_seed", seed), base_dir=Path(".")).scenario
    assert scenario.model.random_seed == seed
    assert isinstance(scenario.model.random_seed, int)
