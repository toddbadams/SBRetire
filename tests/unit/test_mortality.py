"""F-007.2 / F-007.3 — mortality table loading, validation, lookup and coverage (F-007 brief §2, §5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sbretire.config import MortalityAssumptions, load_scenario
from sbretire.mortality import MortalityTableError, load_mortality_table

from mortality_fixtures import META, full_rows, write_table

ROOT = Path(__file__).resolve().parents[2]
REAL_CSV = ROOT / "data" / "ons_mortality.csv"
EXAMPLE = ROOT / "config" / "model.example.yaml"


def test_load_mortality_table_real_file() -> None:
    mortality = load_scenario(EXAMPLE).scenario.mortality
    table = load_mortality_table(REAL_CSV, mortality)
    assert table.path == REAL_CSV
    assert table.meta["projection"] == "principal"
    assert table.meta["raw_sha256"] == "fbc6991bbeeab2691e0e7ce6aabf697fbcbe341a84f8dba6d11f48b29f4e6dac"
    assert table.has("male", 1964, 62)
    assert not table.has("male", 1964, 16)  # before 1981 for this cohort


GOOD = ["female,1960,65,0.01", "male,1960,65,0.02"]


@pytest.mark.parametrize(
    ("header", "rows", "fragment"),
    [
        ("sex,birth_year,age", GOOD, "columns"),
        ("sex,birth_year,age,qx,extra", ["female,1960,65,0.01,1"], "columns"),
        ("sex,age,birth_year,qx", GOOD, "columns"),
        (None, [*GOOD, "male,1960,abc,0.02"], "ons_mortality.csv:4"),
        (None, [*GOOD, "male,1960,66.5,0.02"], "whole number"),
        (None, [*GOOD, "male,1960,65,0.03"], "duplicate"),
        (None, [*GOOD, "male,1960,66,1.5"], "between 0 and 1"),
        (None, [*GOOD, "male,1960,66,-0.1"], "between 0 and 1"),
        (None, [*GOOD, "male,1960,66,nan"], "between 0 and 1"),
        (None, [*GOOD, "male,1960,66,inf"], "between 0 and 1"),
        (None, [*GOOD, "males,1960,66,0.02"], "male, female"),
        (None, [*GOOD, "male,1960,66"], "4 values"),
        (None, [], "no rows"),
    ],
)
def test_load_mortality_table_rejects_invalid_rows(
    tmp_path: Path, header: str | None, rows: list[str], fragment: str
) -> None:
    path = write_table(tmp_path, rows) if header is None else write_table(tmp_path, rows, header=header)
    with pytest.raises(MortalityTableError) as excinfo:
        load_mortality_table(path)
    message = str(excinfo.value)
    assert fragment in message
    assert "ons_mortality.csv" in message
    assert excinfo.value.issues


def test_load_mortality_table_reports_every_bad_row(tmp_path: Path) -> None:
    path = write_table(tmp_path, [*GOOD, "male,1960,66,1.5", "other,1960,67,0.1"])
    with pytest.raises(MortalityTableError) as excinfo:
        load_mortality_table(path)
    assert [issue.location for issue in excinfo.value.issues] == [
        "ons_mortality.csv:4",
        "ons_mortality.csv:5",
    ]


def test_load_mortality_table_rejects_mismatched_sidecar(tmp_path: Path) -> None:
    rows = full_rows(range(1960, 1961), range(65, 67))
    mortality = MortalityAssumptions(
        source="ONS_2024_BASED", geography="UK", projection="principal", data_file="x.csv"
    )

    missing = write_table(tmp_path / "missing", rows, meta={})
    with pytest.raises(MortalityTableError, match=r"ons_mortality\.meta\.json"):
        load_mortality_table(missing, mortality)

    high = write_table(tmp_path / "high", rows, meta={**META, "projection": "high_life_expectancy"})
    with pytest.raises(MortalityTableError) as excinfo:
        load_mortality_table(high, mortality)
    message = str(excinfo.value)
    assert "projection" in message and "high_life_expectancy" in message and "principal" in message

    wales = write_table(tmp_path / "wales", rows, meta={**META, "geography": "Wales"})
    with pytest.raises(MortalityTableError, match="geography"):
        load_mortality_table(wales, mortality)

    no_source = {key: value for key, value in META.items() if key != "source"}
    incomplete = write_table(tmp_path / "incomplete", rows, meta=no_source)
    with pytest.raises(MortalityTableError, match="source"):
        load_mortality_table(incomplete)

    matching = write_table(tmp_path / "ok", rows)
    assert load_mortality_table(matching, mortality).has("female", 1960, 66)
