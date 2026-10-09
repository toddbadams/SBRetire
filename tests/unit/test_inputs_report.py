"""F-017.1 — input rows, inputs.csv and the console Inputs block (F-017 brief §2 #1–#7).

Fixture tests/fixtures/scenarios/valid_minimal.yaml (as-of 2026-10, horizon 60 years, seed 7; alex born
1958-03-01 has no own survivor factor, annuity_b has an end date) and config/model.example.yaml.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sbretire.config import Scenario, load_scenario
from sbretire.inputs_report import (
    INPUT_COLUMNS,
    InputRow,
    format_inputs,
    scenario_input_rows,
    write_inputs_csv,
)
from sbretire.randomness import ResolvedSeed

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"
EXAMPLE = ROOT / "config" / "model.example.yaml"
SEED = ResolvedSeed(7, "config")


def _scenario(path: Path = FIXTURE) -> Scenario:
    return load_scenario(path).scenario


def _leaves(scenario: Scenario) -> dict[str, object]:
    """Every leaf field of the validated Scenario, keyed by its config path (list entries by id)."""
    leaves: dict[str, object] = {}
    for section in type(scenario).model_fields:
        value = getattr(scenario, section)
        entries = value if isinstance(value, tuple) else (value,)
        for entry in entries:
            prefix = f"{section}[{entry.id}]" if isinstance(value, tuple) else section
            for field in type(entry).model_fields:
                leaves[f"{prefix}.{field}"] = getattr(entry, field)
    return leaves


def test_scenario_input_rows_cover_every_field() -> None:
    for path in (FIXTURE, EXAMPLE):
        scenario = _scenario(path)
        rows = scenario_input_rows(scenario, SEED)
        config_items = [row.item for row in rows if row.section != "derived"]
        assert len(config_items) == len(set(config_items)), path.name
        assert set(config_items) == set(_leaves(scenario)), path.name
        assert all(row.label and row.section for row in rows)


def test_scenario_input_rows_values_exact() -> None:
    scenario = _scenario()
    leaves = _leaves(scenario)
    rows = {row.item: row for row in scenario_input_rows(scenario, SEED)}
    for item, expected in leaves.items():
        value = rows[item].value
        if expected is None:
            assert value == "", item
        elif isinstance(expected, bool):
            assert value == ("true" if expected else "false"), item
        elif isinstance(expected, int | float):
            assert float(value) == expected, item
        elif isinstance(expected, date):
            assert value == expected.isoformat(), item
        elif isinstance(expected, Path):
            assert value == expected.name and "/" not in value and "\\" not in value, item
        elif isinstance(expected, tuple):
            assert [float(part) for part in value.split(";")] == list(expected), item
        else:
            assert value == str(expected), item
    assert rows["people[alex].survivor_budget_factor"].value == ""
    assert rows["income[annuity_b].end_date"].value == "2040-04-01"
    assert rows["income[pension_a].end_date"].value == ""
    assert rows["portfolio.annual_return"].value == "0.04"
    assert rows["inflation.data_file"].value == "uk_cpi.csv"


def test_scenario_input_rows_derived() -> None:
    rows = {row.item: row for row in scenario_input_rows(_scenario(), SEED) if row.section == "derived"}
    assert (rows["run.seed"].value, rows["run.seed"].unit) == ("7", "config")
    generated = scenario_input_rows(_scenario(), ResolvedSeed(123456789, "generated"))
    assert [row.unit for row in generated if row.item == "run.seed"] == ["generated"]
    assert rows["people[alex].age_at_as_of"].value == "68"  # born 1958-03-01, as-of 2026-10-01
    assert rows["people[sam].age_at_as_of"].value == "64"  # born 1962-07-15
    assert rows["model.last_month"].value == "2086-09"  # 60 years of months from 2026-10


def test_inputs_csv_format(tmp_path: Path) -> None:
    rows = scenario_input_rows(_scenario(), SEED)
    path = write_inputs_csv(rows, tmp_path / "inputs.csv")
    data = path.read_bytes()
    assert b"\r" not in data
    assert data.decode("utf-8").splitlines()[0] == ",".join(INPUT_COLUMNS)
    with path.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == len(rows)
    assert [InputRow(**{column: line[column] for column in INPUT_COLUMNS}) for line in written] == rows


def test_format_inputs_lists_every_row() -> None:
    rows = scenario_input_rows(_scenario(), SEED)
    text = format_inputs(Path("config/x.yaml"), rows)
    lines = text.splitlines()
    assert lines[0].startswith("Inputs") and "config" in lines[0]
    for row in rows:
        matching = [line for line in lines if f"{row.label}: " in line]
        assert matching, row.item
        if not row.unit.startswith("GBP"):
            assert any(row.value in line for line in matching), row.item
    assert "500,000" in text  # money with thousands separators
    sections = [line.strip() for line in lines if line and not line.startswith("    ")][1:]
    expected = ["Model", "Portfolio", "Budget", "Inflation", "Mortality", "People", "Income", "Derived"]
    assert sections == expected
