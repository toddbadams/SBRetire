"""F-012.2 — annual_results.csv format (SPEC §15, §15.1; F-012 brief §2 #10)."""

from __future__ import annotations

import csv
import dataclasses
import re
from pathlib import Path

from test_reporting_annual import _fixture_inputs, _fixture_scenario, _seeded

from sbretire.reporting import ANNUAL_COLUMNS, annual_results, write_annual_results_csv

PROBABILITY_COLUMNS = {
    "probability_both_alive",
    "probability_person_1_alive",
    "probability_person_2_alive",
    "probability_not_depleted_yet",
    "estimated_lifetime_success_rate",
}
INTEGER_COLUMNS = {"year", "months", "completed_paths", "unresolved_paths"}


def test_annual_results_csv_format(tmp_path: Path) -> None:
    for scenario, inputs in (_seeded(300, 3_800), (_fixture_scenario(), _fixture_inputs())):
        rows = annual_results(scenario, inputs)
        path = write_annual_results_csv(rows, tmp_path / "out" / "annual_results.csv")
        raw = path.read_bytes()
        assert b"\r" not in raw and raw.endswith(b"\n")
        text = raw.decode("utf-8")
        assert text.isascii()
        lines = text.splitlines()
        assert tuple(lines[0].split(",")) == ANNUAL_COLUMNS
        assert len(lines) == len(rows) + 1
        for record, row in zip(csv.DictReader(lines), rows, strict=True):
            for column in ANNUAL_COLUMNS:
                value = record[column]
                expected = getattr(row, column)
                if expected is None:
                    assert value == "", (row.year, column)
                    continue
                assert re.fullmatch(r"-?\d+(\.\d+)?", value), (column, value)  # '.' decimals, no separators
                if column in INTEGER_COLUMNS:
                    assert int(value) == expected
                elif column in PROBABILITY_COLUMNS:
                    assert 0.0 <= float(value) <= 1.0
                    assert abs(float(value) - expected) <= 5e-7
                else:
                    assert abs(float(value) - expected) <= 0.005, (column, value, expected)
        assert {field.name for field in dataclasses.fields(rows[0])} == set(ANNUAL_COLUMNS)
