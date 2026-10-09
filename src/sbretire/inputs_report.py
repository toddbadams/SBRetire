"""The run's inputs as rows: the console Inputs block and ``inputs.csv`` (F-017).

One row per leaf field of the validated Scenario — every section, every person and every Income Stream, list
entries addressed by ``id`` — plus a few derived values. Values are the validated values exactly (floats as
``repr``, dates ISO, unset optional fields empty); data files appear by file name only, since the full path is
machine-specific (configuration §7).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from sbretire.config import Scenario
from sbretire.randomness import ResolvedSeed
from sbretire.timeline import month_start

INPUT_COLUMNS: Final = ("section", "item", "label", "value", "unit")

_SECTION_TITLES: Final = {
    "model": "Model",
    "portfolio": "Portfolio",
    "budget": "Budget",
    "inflation": "Inflation",
    "mortality": "Mortality",
    "people": "People",
    "income": "Income",
    "derived": "Derived",
}

_SELF_EVIDENT_UNITS: Final = frozenset({"date", "file", "month"})
"""Units left off the console block (kept in ``inputs.csv``)."""

# (label, unit) per field, keyed "section.field" (people and income: one entry per field of every list item).
# A config field without an entry raises KeyError, so a new key cannot silently miss the display.
_FIELD_TEXT: Final[dict[str, tuple[str, str]]] = {
    "model.currency": ("Currency", ""),
    "model.as_of_date": ("As-of date (first simulated month)", "date"),
    "model.simulation_count": ("Simulated paths", "paths"),
    "model.confidence_levels": ("Target success rates", "share of paths"),
    "model.frequency": ("Time step", ""),
    "model.horizon_years": ("Horizon", "years"),
    "model.random_seed": ("Random seed (empty = generate one)", ""),
    "model.unknown_keys": ("Unknown config keys", ""),
    "portfolio.starting_balance": ("Starting balance", "GBP"),
    "portfolio.annual_return": ("Fixed annual return (after fees)", "annual effective rate (0.05 = 5%)"),
    "budget.monthly_amount_today": ("Monthly budget", "GBP/month, today's money"),
    "budget.survivor_budget_factor": ("Survivor budget factor (household default)", "share of the budget"),
    "inflation.source": ("Inflation source", ""),
    "inflation.source_period": ("Calibration period", "years"),
    "inflation.data_file": ("CPI data file", "file"),
    "inflation.model": ("Inflation model", ""),
    "inflation.parameter_units": ("Parameter units", ""),
    "inflation.log_mean": ("Long-run mean of log(1 + inflation)", "log annual"),
    "inflation.ar1_coefficient": ("AR(1) persistence", ""),
    "inflation.innovation_sd": ("Yearly shock SD of log(1 + inflation)", "log annual"),
    "inflation.initial_rate": ("Inflation in the year before the as-of date", "annual rate"),
    "mortality.source": ("Mortality source", ""),
    "mortality.geography": ("Geography", ""),
    "mortality.projection": ("Projection", ""),
    "mortality.data_file": ("Mortality data file", "file"),
    "people.id": ("Id", ""),
    "people.name": ("Name", ""),
    "people.date_of_birth": ("Date of birth", "date"),
    "people.sex": ("Sex (mortality table)", ""),
    "people.survivor_budget_factor": (
        "Survivor budget factor when this person survives (empty = household default)",
        "share of the budget",
    ),
    "income.id": ("Id", ""),
    "income.name": ("Name", ""),
    "income.start_date": ("First month paid", "date"),
    "income.end_date": ("First month no longer paid (empty = no end)", "date"),
    "income.annual_amount_today": ("Annual amount", "GBP/year, today's money"),
    "income.inflation_linked": ("Rises with inflation", ""),
    "income.survivor_percentage": ("Share paid after the recipient's death", "share"),
    "income.recipient": ("Recipient", "person id or household"),
}


@dataclass(frozen=True)
class InputRow:
    """One input of a run: where it lives in the config, what it means, its exact value and unit."""

    section: str
    """model | portfolio | budget | inflation | mortality | people | income | derived"""
    item: str
    """Config path, e.g. ``people[person_1].date_of_birth``; derived rows use ``run.seed`` and similar."""
    label: str
    value: str
    """Exact validated value as text; empty when an optional field is unset."""
    unit: str


def _value_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Path):
        return value.name
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return ";".join(_value_text(part) for part in value)
    return str(value)


def _model_rows(section: str, prefix: str, model: BaseModel, label_prefix: str = "") -> list[InputRow]:
    rows = []
    for field in type(model).model_fields:
        label, unit = _FIELD_TEXT[f"{section}.{field}"]
        value = _value_text(getattr(model, field))
        rows.append(InputRow(section, f"{prefix}.{field}", label_prefix + label, value, unit))
    return rows


def _age(born: date, on: date) -> int:
    """Completed years of age on ``on``."""
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def scenario_input_rows(scenario: Scenario, seed: ResolvedSeed) -> list[InputRow]:
    """Every validated Scenario field as a row (in config order), then the derived rows.

    ``seed`` is the seed the run actually used: the configured ``random_seed`` or a generated one.
    """
    rows: list[InputRow] = []
    for section in ("model", "portfolio", "budget", "inflation", "mortality"):
        rows += _model_rows(section, section, getattr(scenario, section))
    for person in scenario.people:
        rows += _model_rows("people", f"people[{person.id}]", person, f"{person.name}: ")
    for stream in scenario.income:
        rows += _model_rows("income", f"income[{stream.id}]", stream, f"{stream.name}: ")
    as_of = scenario.model.as_of_date
    rows.append(InputRow("derived", "run.seed", "Random seed used", str(seed.value), seed.source))
    for person in scenario.people:
        rows.append(
            InputRow(
                "derived",
                f"people[{person.id}].age_at_as_of",
                f"{person.name}: age at the as-of date",
                str(_age(person.date_of_birth, as_of)),
                "completed years",
            )
        )
    last = month_start(as_of, scenario.model.horizon_years * 12 - 1)
    rows.append(InputRow("derived", "model.last_month", "Last simulated month", f"{last:%Y-%m}", "month"))
    return rows


def write_inputs_csv(rows: Sequence[InputRow], path: Path) -> Path:
    """Write ``inputs.csv`` (UTF-8, LF, header :data:`INPUT_COLUMNS`), one line per row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(INPUT_COLUMNS)
        writer.writerows([getattr(row, column) for column in INPUT_COLUMNS] for row in rows)
    return path


def display_value(row: InputRow) -> str:
    """The row's value for people: money with thousands separators, everything else as written."""
    if row.unit.startswith("GBP") and row.value:
        amount = float(row.value)
        return f"{amount:,.0f}" if amount.is_integer() else f"{amount:,.2f}"
    return row.value


def format_inputs(config: Path, rows: Sequence[InputRow]) -> str:
    """Plain-text Inputs block: a heading per section, then ``label: value unit`` per row."""
    lines = [f"Inputs ({config}):"]
    section = None
    for row in rows:
        if row.section != section:
            section = row.section
            lines.append(f"  {_SECTION_TITLES[section]}")
        value = display_value(row) or "(not set)"
        unit = "" if row.unit in _SELF_EVIDENT_UNITS else row.unit
        lines.append(f"    {row.label}: {value} {unit}".rstrip())
    return "\n".join(lines)
