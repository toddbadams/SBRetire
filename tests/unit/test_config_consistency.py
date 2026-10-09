"""F-001.2 — cross-field and date consistency rules (SPEC §4.3; decisions simulation-conventions §1,
configuration §3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from scenario_helpers import set_at

from sbretire.config import ScenarioError, ScenarioIssue, parse_scenario


def issues_for(raw: dict[str, Any]) -> tuple[ScenarioIssue, ...]:
    with pytest.raises(ScenarioError) as exc:
        parse_scenario(raw, base_dir=Path("."))
    return exc.value.issues


def test_duplicate_ids_rejected(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "people[1].id", "alex")
    raw = set_at(raw, "income[0].recipient", "alex")
    raw = set_at(raw, "income[1].recipient", "alex")
    raw = set_at(raw, "income[1].id", "pension_a")

    issues = issues_for(raw)

    assert [issue.location for issue in issues] == ["income[1].id", "people[1].id"]
    assert all("duplicate" in issue.message for issue in issues)
    assert "'pension_a'" in issues[0].message


@pytest.mark.parametrize(
    ("path", "value", "fragment"),
    [
        ("model.as_of_date", "2026-10-09", "1st of a month"),
        ("income[0].start_date", "2027-01-15", "1st of a month"),
        ("income[1].end_date", "2040-04-02", "1st of a month"),
        ("income[1].end_date", "2024-04-01", "after start_date"),
        ("income[1].end_date", "2023-01-01", "after start_date"),
        ("income[1].end_date", "2026-10-01", "after as_of_date"),
        ("people[0].date_of_birth", "2026-10-01", "before as_of_date"),
        ("people[1].date_of_birth", "2030-01-01", "before as_of_date"),
    ],
)
def test_date_rules_rejected(valid_raw: dict[str, Any], path: str, value: str, fragment: str) -> None:
    issues = issues_for(set_at(valid_raw, path, value))
    assert [issue.location for issue in issues] == [path]
    assert fragment in issues[0].message


def test_income_start_before_as_of_accepted(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "income[0].start_date", "2001-01-01")
    scenario = parse_scenario(raw, base_dir=Path(".")).scenario
    assert scenario.income[0].start_date == date(2001, 1, 1) < scenario.model.as_of_date


def test_people_count_and_recipient_reference(valid_raw: dict[str, Any]) -> None:
    one_person = set_at(valid_raw, "people", valid_raw["people"][:1])
    one_person = set_at(one_person, "income", valid_raw["income"][:1])
    assert [(i.location, "exactly two people" in i.message) for i in issues_for(one_person)] == [
        ("people", True)
    ]

    third = dict(valid_raw["people"][0], id="kim", name="Kim")
    three_people = set_at(valid_raw, "people", [*valid_raw["people"], third])
    assert [i.location for i in issues_for(three_people)] == ["people"]

    issues = issues_for(set_at(valid_raw, "income[0].recipient", "nobody"))
    assert [i.location for i in issues] == ["income[0].recipient"]
    assert "'nobody'" in issues[0].message and "alex" in issues[0].message


def test_consistency_issues_reported_together(valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "income[0].recipient", "nobody")
    raw = set_at(raw, "people[0].date_of_birth", "2027-01-01")
    assert [i.location for i in issues_for(raw)] == ["income[0].recipient", "people[0].date_of_birth"]
