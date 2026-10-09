"""F-007.1 — ONS workbook → data/ons_mortality.csv + sidecar (F-007 brief §2; data-and-calibration §1)."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import openpyxl
import pytest

import build_ons_mortality

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "ukppp24qx.xlsx"
CSV_PATH = ROOT / "data" / "ons_mortality.csv"
META_PATH = ROOT / "data" / "ons_mortality.meta.json"
RAW_SHA256 = "fbc6991bbeeab2691e0e7ce6aabf697fbcbe341a84f8dba6d11f48b29f4e6dac"

Key = tuple[str, int, int]


def _committed() -> dict[Key, float]:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return {
            (row["sex"], int(row["birth_year"]), int(row["age"])): float(row["qx"])
            for row in csv.DictReader(handle)
        }


def _workbook_cell(sheet: str, column_year: int, age: int) -> float:
    """Independent read: header row 4 holds years from column B = 1981; ages 0.. start at row 5."""
    book = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    value = book[sheet].cell(row=5 + age, column=2 + column_year - 1981).value
    book.close()
    assert isinstance(value, (int, float))
    return float(value)


def test_build_ons_mortality_reproduces_committed_files(tmp_path: Path) -> None:
    build_ons_mortality.main(["--raw", str(RAW), "--out-dir", str(tmp_path)])
    assert (tmp_path / "ons_mortality.csv").read_bytes() == CSV_PATH.read_bytes()
    assert (tmp_path / "ons_mortality.meta.json").read_bytes() == META_PATH.read_bytes()


def test_ons_mortality_known_answers() -> None:
    q = _committed()
    assert q[("male", 1964, 62)] == 0.0092454  # period 2026, age 62
    assert q[("female", 1969, 57)] == 0.0039146  # period 2026, age 57
    assert q[("male", 1964, 62)] == pytest.approx(_workbook_cell("males period qx", 2026, 62) / 100_000)
    # Beyond 2074: born 1981, age 100 (year 2081) comes from the cohort sheet.
    assert q[("male", 1981, 100)] == pytest.approx(
        _workbook_cell("males cohort qx", 1981, 100) / 100_000, rel=1e-12
    )
    assert q[("male", 1981, 100)] == 0.3275388
    assert q[("female", 2000, 90)] == pytest.approx(
        _workbook_cell("females cohort qx", 2000, 90) / 100_000, rel=1e-12
    )
    # Period diagonal for a pre-1981 cohort: born 1900 at age 100 is year 2000.
    assert q[("female", 1900, 100)] == pytest.approx(_workbook_cell("females period qx", 2000, 100) / 100_000)


def test_build_fills_gap_log_linear() -> None:
    q = _committed()
    for sex in ("male", "female"):
        for age in range(95, 101):
            first_gap_birth, last_gap_birth = 2075 - age, 1980
            low = q[(sex, first_gap_birth - 1, age)]  # year 2074, period sheet
            high = q[(sex, 1981, age)]  # year 1981 + age, cohort sheet
            span = 1981 - (first_gap_birth - 1)
            for birth in range(first_gap_birth, last_gap_birth + 1):
                weight = (birth - (first_gap_birth - 1)) / span
                expected = math.exp(math.log(low) + weight * (math.log(high) - math.log(low)))
                assert q[(sex, birth, age)] == pytest.approx(expected, rel=1e-12), (sex, birth, age)
                assert min(low, high) < q[(sex, birth, age)] < max(low, high)
    assert (("male", 1974, 101)) not in q


def test_ons_mortality_csv_is_well_formed() -> None:
    lines = CSV_PATH.read_bytes().split(b"\n")
    assert lines[0] == b"sex,birth_year,age,qx"
    assert lines[-1] == b""
    assert b"\r" not in CSV_PATH.read_bytes()
    q = _committed()
    assert len(q) == len(lines) - 2  # no duplicate keys
    keys = list(q)
    assert keys == sorted(keys)
    assert {sex for sex, _, _ in keys} == {"male", "female"}
    assert {age for _, _, age in keys} == set(range(0, 101))
    assert all(0.0 < value < 1.0 for value in q.values())
    births = {birth for _, birth, _ in keys}
    assert min(births) == 1881 and max(births) == 2074
    # Every cohort born 1881–2074 has a contiguous run of ages ending at its last covered age.
    for sex in ("male", "female"):
        for birth in (1881, 1964, 1968, 1975, 1980, 2074):
            ages = sorted(age for s, b, age in keys if s == sex and b == birth)
            assert ages == list(range(ages[0], ages[-1] + 1))
    assert sorted(a for s, b, a in keys if s == "male" and b == 1964) == list(range(17, 101))


def test_ons_mortality_meta_records_provenance() -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert meta["raw_sha256"] == RAW_SHA256
    assert meta["source"] == "ONS_2024_BASED"
    assert meta["geography"] == "UK"
    assert meta["projection"] == "principal"
    assert meta["publication_date"] == "2026-05-15"
    assert meta["retrieved"] == "2026-10-09"
    assert meta["units"] == "probability"
    assert meta["age_max"] == 100
    assert meta["raw_file"] == "raw/ukppp24qx.xlsx"
    assert meta["source_url"].startswith("https://www.ons.gov.uk/")
