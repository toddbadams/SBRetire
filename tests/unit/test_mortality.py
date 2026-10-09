"""F-007.2 / F-007.3 — mortality table loading, validation, lookup and coverage (F-007 brief §2, §5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from sbretire.__main__ import main
from sbretire.config import MortalityAssumptions, load_scenario, parse_scenario
from sbretire.metadata import file_sha256
from sbretire.mortality import AGE_MAX, MortalityTableError, coverage_issues, load_mortality_table

from mortality_fixtures import META, full_rows, write_table
from scenario_helpers import set_at

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


def _real() -> Any:
    return load_mortality_table(REAL_CSV)


def test_annual_q_lookup_and_tail() -> None:
    table = _real()
    ages = np.array([62, 63, 99, 100, 101, 120], dtype=np.int64)
    q = table.annual_q("male", 1964, ages)
    assert q.dtype == np.float64
    assert q.shape == ages.shape
    assert q[0] == 0.0092454  # period 2026, age 62 (F-007.1 known answer)
    assert 0 < q[0] < q[1] < q[2] < q[3] < 1
    assert AGE_MAX == 100
    np.testing.assert_array_equal(q[3:], [q[3]] * 3)  # above 100: hold q(100, 1964 + 100)
    assert table.annual_q("female", 1968, np.array([100]))[0] != q[3]
    single = {age: table.annual_q("female", 1968, np.array([age]))[0] for age in (57, 58, 100)}
    np.testing.assert_array_equal(
        table.annual_q("female", 1968, np.array([[57, 58], [101, 100]])),
        [[single[57], single[58]], [single[100], single[100]]],
    )


@pytest.mark.parametrize(
    ("sex", "birth_year", "age", "fragment"),
    [("male", 1964, 16, "age 16"), ("female", 1800, 90, "birth year 1800"), ("male", 1964, -1, "age -1")],
)
def test_annual_q_uncovered_age_raises(sex: Any, birth_year: int, age: int, fragment: str) -> None:
    with pytest.raises(KeyError) as excinfo:
        _real().annual_q(sex, birth_year, np.array([70, age]))
    message = str(excinfo.value)
    assert fragment in message and sex in message


def _gapped_table(directory: Path) -> Path:
    """Fixture people (valid_minimal): alex male b. 1958 (age 68), sam female b. 1962 (age 64).

    Cohort 1962 lacks ages 91–100."""
    rows = full_rows(range(1958, 1959), range(60, 101)) + full_rows(range(1962, 1963), range(60, 91))
    return write_table(directory, rows)


def test_coverage_issues_reports_missing_ages(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    example = load_scenario(EXAMPLE).scenario
    assert coverage_issues(_real(), example) == []

    gapped = load_mortality_table(_gapped_table(tmp_path))
    scenario = parse_scenario(valid_raw, base_dir=tmp_path).scenario
    issues = coverage_issues(gapped, scenario)
    assert [issue.location for issue in issues] == ["people[1].date_of_birth"]
    assert "female" in issues[0].message and "1962" in issues[0].message and "91" in issues[0].message

    # A person already over 100 needs only q(100, b + 100).
    old = set_at(set_at(valid_raw, "people[0].date_of_birth", "1920-01-01"), "income", [])
    rows = full_rows(range(1920, 1921), range(100, 101)) + full_rows(range(1962, 1963), range(60, 101))
    over_100 = load_mortality_table(write_table(tmp_path / "old", rows))
    assert coverage_issues(over_100, parse_scenario(old, base_dir=tmp_path).scenario) == []


def test_cli_validate_reports_mortality_coverage(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", "--config", str(EXAMPLE), "--require-data-files"]) == 0
    capsys.readouterr()

    table = _gapped_table(tmp_path / "data")
    config = tmp_path / "gapped.yaml"
    raw = set_at(valid_raw, "mortality.data_file", "data/ons_mortality.csv")
    config.write_text(yaml.safe_dump(raw), encoding="utf-8")
    assert main(["validate", "--config", str(config)]) == 0  # contents checked only on request
    assert main(["validate", "--config", str(config), "--require-data-files"]) == 2
    err = capsys.readouterr().err
    assert "people[1].date_of_birth" in err and "91" in err

    table.write_text(table.read_text(encoding="utf-8") + "male,1958,59,7\n", encoding="utf-8")
    assert main(["validate", "--config", str(config), "--require-data-files"]) == 2
    assert "between 0 and 1" in capsys.readouterr().err


def test_mortality_data_file_record() -> None:
    record = _real().data_file_record()
    assert record.role == "mortality"
    assert record.path == str(REAL_CSV)
    assert record.sha256 == file_sha256(REAL_CSV)
    assert record.version == "2024-based (published 2026-05-15)"
    assert record.retrieved == "2026-10-09"
