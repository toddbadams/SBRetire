"""Build data/ons_mortality.csv and its provenance sidecar from the ONS 2024-based UK qx workbook.

One-off and reproducible; never called by a model run (SPEC §2, §19).
Rules: docs/decisions/data-and-calibration.md §1.

- Period sheets give q at exact age x in calendar year y (1981–2074, ages 0–100). Along the diagonal they
  equal the cohort rates, so the cohort born in b at age x takes period q(x, b + x).
- For years after 2074 the cohort sheets (birth years 1981–2074) supply ONS's own projection.
- Cells neither covers (ages 95–100 in 2075–2080, birth years 1975–1980) are interpolated log-linearly in q
  between (x, 2074) and (x, 1981 + x).
- Values are per 100,000 in the workbook and written as probabilities.

Usage: uv run python scripts/build_ons_mortality.py [--raw data/raw/ukppp24qx.xlsx] [--out-dir data]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw" / "ukppp24qx.xlsx"
DEFAULT_OUT = ROOT / "data"

SEXES = {"male": "males", "female": "females"}  # model category -> workbook sheet prefix (no inference)
FIRST_YEAR = 1981
LAST_PERIOD_YEAR = 2074
AGE_MAX = 100
HEADER_ROW = 4
PER = Decimal(100_000)

META = {
    "source": "ONS_2024_BASED",
    "geography": "UK",
    "projection": "principal",
    "dataset": "Mortality rates (qx), principal projection, UK — 2024-based",
    "publication_date": "2026-05-15",
    "retrieved": "2026-10-09",
    "source_url": (
        "https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies/"
        "datasets/mortalityratesqxprincipalprojectionunitedkingdom"
    ),
    "raw_file": "raw/ukppp24qx.xlsx",
    "units": "probability",
    "age_max": AGE_MAX,
    "columns": "sex,birth_year,age,qx",
    "build": "scripts/build_ons_mortality.py",
}

Grid = dict[tuple[int, int], float]  # (age, year or birth year) -> probability


def _year(label: object) -> int:
    digits = "".join(ch for ch in str(label) if ch.isdigit())
    return int(digits)


def read_sheet(book: openpyxl.Workbook, name: str) -> Grid:
    """Read one qx sheet into {(age, column year): probability}, checking its layout."""
    rows = list(book[name].iter_rows(min_row=HEADER_ROW, max_row=HEADER_ROW + AGE_MAX + 1, values_only=True))
    header, body = rows[0], rows[1:]
    if str(header[0]).strip() != "Exact age (years)":
        raise ValueError(f"{name}: unexpected header {header[0]!r}")
    years = [_year(label) for label in header[1:] if label is not None]
    if years != list(range(FIRST_YEAR, LAST_PERIOD_YEAR + 1)):
        raise ValueError(f"{name}: unexpected year columns {years[:2]}…{years[-2:]}")
    grid: Grid = {}
    for expected_age, row in enumerate(body):
        if row[0] != expected_age:
            raise ValueError(f"{name}: expected age {expected_age}, found {row[0]!r}")
        for year, value in zip(years, row[1:], strict=False):
            if not isinstance(value, (int, float)) or not 0 < value < 100_000:
                raise ValueError(f"{name}: invalid qx {value!r} at age {expected_age}, year {year}")
            grid[(expected_age, year)] = float(Decimal(repr(float(value))) / PER)
    return grid


def cohort_rows(period: Grid, cohort: Grid) -> dict[tuple[int, int], float]:
    """{(birth_year, age): q} for every cohort cell available from the period, cohort and gap rules."""
    out: dict[tuple[int, int], float] = {}
    for (age, year), q in period.items():
        out[(year - age, age)] = q
    for (age, birth), q in cohort.items():
        year = birth + age
        if year <= LAST_PERIOD_YEAR:
            if not math.isclose(q, period[(age, year)], rel_tol=1e-12):
                raise ValueError(f"cohort and period disagree at age {age}, year {year}")
        else:
            out[(birth, age)] = q
    for age in range(AGE_MAX + 1):
        low_birth = LAST_PERIOD_YEAR - age  # year 2074 (period)
        high_birth = FIRST_YEAR  # year 1981 + age (cohort)
        if high_birth - low_birth <= 1:
            continue
        low, high = out[(low_birth, age)], out[(high_birth, age)]
        span = high_birth - low_birth
        for birth in range(low_birth + 1, high_birth):
            weight = (birth - low_birth) / span
            out[(birth, age)] = math.exp(math.log(low) + weight * (math.log(high) - math.log(low)))
    return out


def build(raw: Path) -> tuple[str, str]:
    """Return (csv text, sidecar JSON text) for the workbook at ``raw``."""
    book = openpyxl.load_workbook(raw, read_only=True, data_only=True)
    try:
        tables = {
            sex: cohort_rows(read_sheet(book, f"{prefix} period qx"), read_sheet(book, f"{prefix} cohort qx"))
            for sex, prefix in SEXES.items()
        }
    finally:
        book.close()
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["sex", "birth_year", "age", "qx"])
    for sex in sorted(tables):
        for (birth, age), q in sorted(tables[sex].items()):
            writer.writerow([sex, birth, age, repr(q)])
    meta = {**META, "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
    return buffer.getvalue(), json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    csv_text, meta_text = build(args.raw)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "ons_mortality.csv").write_text(csv_text, encoding="utf-8", newline="\n")
    (args.out_dir / "ons_mortality.meta.json").write_text(meta_text, encoding="utf-8", newline="\n")
    print(f"Wrote {args.out_dir / 'ons_mortality.csv'} ({csv_text.count(chr(10)) - 1} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
