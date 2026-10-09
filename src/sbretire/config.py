"""Scenario configuration: typed, immutable, validated (SPEC §4).

A **Scenario** is one YAML configuration. :func:`parse_scenario` turns an already-loaded mapping into a frozen
:class:`Scenario`, or raises one :class:`ScenarioError` listing *every* problem with its YAML location
(e.g. ``income[2].survivor_percentage``) — fail fast, fix once (SPEC §4.3).

Scalars are strict: no string→number, no number→bool, dates only as YAML dates or ISO ``YYYY-MM-DD`` strings.
Money is GBP; fields ending ``_today`` are in today's GBP at the As-Of Date.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, NamedTuple

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------- strict scalar types


def _number(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"must be a number (got {value!r})")
    return float(value)


def _integer(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"must be a whole number (got {value!r})")
    return value


def _boolean(value: object) -> object:
    if not isinstance(value, bool):
        raise ValueError(f"must be true or false (got {value!r})")
    return value


def _text(value: object) -> object:
    if not isinstance(value, str):
        raise ValueError(f"must be text (got {value!r})")
    return value


def _iso_date(value: object) -> object:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and _ISO_DATE.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValueError(f"must be an ISO date YYYY-MM-DD (got {value!r})")


def _first_of_month(value: date) -> date:
    if value.day != 1:
        raise ValueError(f"must be the 1st of a month, e.g. {value:%Y-%m}-01 (got {value.isoformat()})")
    return value


def _unique(values: tuple[float, ...]) -> tuple[float, ...]:
    if len(set(values)) != len(values):
        raise ValueError(f"must not contain duplicates (got {list(values)!r})")
    return values


Number = Annotated[float, BeforeValidator(_number)]
Integer = Annotated[int, BeforeValidator(_integer)]
Boolean = Annotated[bool, BeforeValidator(_boolean)]
Text = Annotated[str, BeforeValidator(_text)]
Identifier = Annotated[str, BeforeValidator(_text), Field(min_length=1)]
IsoDate = Annotated[date, BeforeValidator(_iso_date)]
MonthStart = Annotated[date, BeforeValidator(_iso_date), AfterValidator(_first_of_month)]
Probability = Annotated[float, BeforeValidator(_number), Field(gt=0, lt=1)]
NonNegative = Annotated[float, BeforeValidator(_number), Field(ge=0)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------- scenario sections


class ModelSettings(_Frozen):
    """Run-level settings (SPEC §4.2 Model)."""

    currency: Literal["GBP"]
    as_of_date: MonthStart
    simulation_count: Annotated[Integer, Field(gt=0)]
    confidence_levels: Annotated[tuple[Probability, ...], Field(min_length=1), AfterValidator(_unique)]
    frequency: Literal["monthly"]
    horizon_years: Annotated[Integer, Field(gt=0)]
    random_seed: Annotated[Integer, Field(ge=0)] | None
    unknown_keys: Literal["error", "warn"] = "error"


class PortfolioAssumptions(_Frozen):
    """Starting capital (GBP) and fixed annual effective nominal return (SPEC §4.2 Portfolio)."""

    starting_balance: NonNegative
    annual_return: Annotated[Number, Field(gt=-1)]


class BudgetAssumptions(_Frozen):
    """Base monthly Budget in today's GBP and the household Survivor Budget Factor (SPEC §4.2 Budget)."""

    monthly_amount_today: NonNegative
    survivor_budget_factor: NonNegative


class InflationAssumptions(_Frozen):
    """Inflation source and parameters; F-006 narrows ``model`` to a precise process (SPEC §4.2, §6)."""

    source: Text
    source_period: Text
    annual_mean: Number
    annual_standard_deviation: NonNegative
    model: Text
    parameter_units: Text


class MortalityAssumptions(_Frozen):
    """Mortality dataset reference; contents are validated by F-007 (SPEC §4.2 Mortality)."""

    source: Text
    geography: Text
    projection: Text
    data_file: Annotated[Path, BeforeValidator(_text)]


class Person(_Frozen):
    """One of the two people; ``sex`` uses the mortality table's categories (SPEC §4.2 People)."""

    id: Identifier
    name: Text
    date_of_birth: IsoDate
    sex: Literal["male", "female"]
    survivor_budget_factor: NonNegative | None = None


class IncomeStream(_Frozen):
    """One configured inflow; annual amount in today's GBP, ``end_date`` exclusive (SPEC §4.2, §8)."""

    id: Identifier
    name: Text
    start_date: MonthStart
    end_date: MonthStart | None = None
    annual_amount_today: NonNegative
    inflation_linked: Boolean
    survivor_percentage: Annotated[Number, Field(ge=0, le=1)]
    recipient: Identifier


class Scenario(_Frozen):
    """A complete, validated scenario (SPEC §4)."""

    model: ModelSettings
    portfolio: PortfolioAssumptions
    budget: BudgetAssumptions
    inflation: InflationAssumptions
    mortality: MortalityAssumptions
    people: tuple[Person, ...]
    income: tuple[IncomeStream, ...] = ()


# ---------------------------------------------------------------- issues


class ScenarioIssue(NamedTuple):
    """One validation problem: where it is in the YAML and what to do about it."""

    location: str
    message: str


class ScenarioError(ValueError):
    """Every problem found in a scenario, sorted by location; ``str()`` gives one issue per line."""

    def __init__(self, issues: Sequence[ScenarioIssue]) -> None:
        self.issues = tuple(sorted(issues, key=lambda issue: _location_key(issue.location)))
        super().__init__("\n".join(f"{issue.location}: {issue.message}" for issue in self.issues))


@dataclass(frozen=True)
class LoadedScenario:
    """A validated scenario plus non-fatal warnings and where it came from."""

    scenario: Scenario
    source_path: Path | None
    warnings: tuple[ScenarioIssue, ...]


def _format_location(loc: Sequence[int | str]) -> str:
    text = ""
    for part in loc:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text or "(scenario)"


def _location_key(location: str) -> list[tuple[int, str, int]]:
    """Natural sort: ``income[2]`` before ``income[10]``."""
    return [(1, "", int(p)) if p.isdigit() else (0, p, 0) for p in re.split(r"[.\[\]]+", location) if p]


_MESSAGES = {
    "missing": "required key is missing",
    "extra_forbidden": "unknown key",
}


def _issue(error: Mapping[str, Any]) -> ScenarioIssue:
    kind = str(error["type"])
    message = _MESSAGES.get(kind) or str(error["msg"]).removeprefix("Value error, ")
    message = message.replace("Input should be", "must be", 1)
    if kind not in _MESSAGES and kind != "value_error" and "input" in error:
        message += f" (got {error['input']!r})"
    return ScenarioIssue(_format_location(error["loc"]), message)


# ---------------------------------------------------------------- cross-field rules


def _consistency_issues(scenario: Scenario) -> list[ScenarioIssue]:
    """Rules spanning several fields (configuration decisions §3). Run only once every field is valid."""
    as_of = scenario.model.as_of_date
    issues: list[ScenarioIssue] = []

    def flag(location: str, problem: str, got: object) -> None:
        shown = got.isoformat() if isinstance(got, date) else repr(got)
        issues.append(ScenarioIssue(location, f"{problem} (got {shown})"))

    person_ids = [p.id for p in scenario.people]
    for section, ids in (("people", person_ids), ("income", [s.id for s in scenario.income])):
        for index, item_id in enumerate(ids):
            if item_id in ids[:index]:
                flag(f"{section}[{index}].id", "duplicate id", item_id)
    if len(scenario.people) != 2:
        flag("people", "exactly two people are required", len(scenario.people))
    for index, person in enumerate(scenario.people):
        if person.date_of_birth >= as_of:
            flag(f"people[{index}].date_of_birth", f"must be before as_of_date {as_of}", person.date_of_birth)
    for index, stream in enumerate(scenario.income):
        where = f"income[{index}]"
        if stream.recipient not in person_ids:
            flag(f"{where}.recipient", f"must be one of the people ids {person_ids}", stream.recipient)
        end = stream.end_date
        if end is not None and end <= stream.start_date:
            flag(f"{where}.end_date", f"must be after start_date {stream.start_date}", end)
        elif end is not None and end <= as_of:
            flag(f"{where}.end_date", f"must be after as_of_date {as_of}; the stream would never pay", end)
    return issues


# ---------------------------------------------------------------- entry point


def parse_scenario(
    raw: Mapping[str, object], *, base_dir: Path, require_data_files: bool = False
) -> LoadedScenario:
    """Validate an already-loaded scenario mapping.

    ``base_dir`` is the directory relative paths resolve against (the config file's directory).
    Raises :class:`ScenarioError` with every issue found.
    """
    try:
        scenario = Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError([_issue(e) for e in exc.errors()]) from None
    if issues := _consistency_issues(scenario):
        raise ScenarioError(issues)
    return LoadedScenario(scenario=scenario, source_path=None, warnings=())


def load_scenario(path: Path | str, *, require_data_files: bool = False) -> LoadedScenario:
    raise NotImplementedError
