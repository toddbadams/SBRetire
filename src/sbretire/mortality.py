"""ONS cohort mortality table: loading, validation and lookup (SPEC §7; data-and-calibration §1).

The table holds annual death probabilities q per cohort: ``qx`` for (``sex``, ``birth_year``, ``age``) is the
probability that a person born in ``birth_year``, aged exactly ``age`` in year ``birth_year + age``, dies
before ``age + 1``. It is built from the ONS workbook by ``scripts/build_ons_mortality.py``; a run never
downloads data.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final, Literal, get_args

import numpy as np
from numpy.typing import NDArray

from sbretire.config import MortalityAssumptions, Person, Scenario, ScenarioIssue
from sbretire.metadata import DataFileRecord, file_sha256
from sbretire.timeline import month_index

Sex = Literal["male", "female"]
AGE_MAX: Final = 100
"""Last tabulated age; above it the cohort's age-100 rate is held (data-and-calibration §1)."""
SEXES: Final[tuple[Sex, ...]] = get_args(Sex)
COLUMNS: Final = ("sex", "birth_year", "age", "qx")
SIDECAR_SUFFIX: Final = ".meta.json"
REQUIRED_META: Final = ("source", "geography", "projection", "edition", "publication_date", "retrieved")
CHECKED_AGAINST_CONFIG: Final = ("source", "geography", "projection")


class MortalityTableError(ValueError):
    """The mortality data file or its sidecar is invalid; ``issues`` lists every problem found."""

    def __init__(self, issues: list[ScenarioIssue]) -> None:
        self.issues = tuple(issues)
        lines = "\n".join(f"  {issue.location}: {issue.message}" for issue in self.issues)
        super().__init__(f"invalid mortality data ({len(self.issues)} problem(s)):\n{lines}")


@dataclass(frozen=True)
class MortalityTable:
    """Validated cohort q: per sex a dense ``[birth_year - first_birth_year, age]`` grid (NaN = absent)."""

    path: Path
    meta: Mapping[str, object]
    first_birth_year: int
    grids: Mapping[Sex, NDArray[np.float64]] = field(repr=False)

    def has(self, sex: Sex, birth_year: int, age: int) -> bool:
        """Whether the table holds q for this cohort and age (ages above the table are not 'held')."""
        row = birth_year - self.first_birth_year
        grid = self.grids[sex]
        return 0 <= row < grid.shape[0] and 0 <= age < grid.shape[1] and not math.isnan(grid[row, age])

    def annual_q(self, sex: Sex, birth_year: int, ages: NDArray[np.int64]) -> NDArray[np.float64]:
        """Annual probability of dying between exact age x and x + 1 for the cohort born in ``birth_year``.

        Vectorised over ``ages`` (completed years, any shape); a person aged x uses q(x, birth_year + x) for
        that whole year of age, and ages above :data:`AGE_MAX` use q(100, birth_year + 100). Raises
        ``KeyError`` naming sex, birth year and age when the table does not cover a requested age.
        """
        ages = np.asarray(ages, dtype=np.int64)
        grid = self.grids[sex]
        row = birth_year - self.first_birth_year
        if not 0 <= row < grid.shape[0]:
            last = self.first_birth_year + grid.shape[0] - 1
            age = int(ages.flat[0]) if ages.size else None
            raise KeyError(
                f"no {sex} mortality rate for birth year {birth_year} at age {age} in {self.path.name} "
                f"(birth years {self.first_birth_year}-{last})"
            )
        looked_up = np.minimum(ages, AGE_MAX)
        inside = (looked_up >= 0) & (looked_up < grid.shape[1])
        values = np.full(ages.shape, np.nan)
        values[inside] = grid[row, looked_up[inside]]
        missing = np.isnan(values)
        if missing.any():
            age = int(ages[missing].flat[0])
            cohort = f"{sex} mortality rate for birth year {birth_year} at age {age}"
            raise KeyError(f"no {cohort} in {self.path.name}")
        return values

    def data_file_record(self) -> DataFileRecord:
        """This table as a Run Metadata data-file entry (SHA-256 of the CSV; version and retrieval date)."""
        return DataFileRecord(
            role="mortality",
            path=str(self.path),
            sha256=file_sha256(self.path),
            version=f"{self.meta['edition']} (published {self.meta['publication_date']})",
            retrieved=str(self.meta["retrieved"]),
        )


def sidecar_path(path: Path) -> Path:
    """``ons_mortality.csv`` -> ``ons_mortality.meta.json`` beside it."""
    return path.with_name(path.stem + SIDECAR_SUFFIX)


def _parse_row(values: list[str]) -> tuple[Sex, int, int, float] | str:
    """The parsed row, or a fix-it message."""
    if len(values) != len(COLUMNS):
        return f"expected {len(COLUMNS)} values ({','.join(COLUMNS)}), found {len(values)}"
    sex, birth_text, age_text, q_text = (value.strip() for value in values)
    if sex not in SEXES:
        return f"sex must be one of {', '.join(SEXES)}; found {sex!r}"
    try:
        birth_year, age = int(birth_text), int(age_text)
    except ValueError:
        return f"birth_year and age must be whole numbers; found {birth_text!r}, {age_text!r}"
    if age < 0:
        return f"age must be 0 or more; found {age}"
    try:
        q = float(q_text)
    except ValueError:
        return f"qx must be a number; found {q_text!r}"
    if not (math.isfinite(q) and 0.0 <= q <= 1.0):
        return f"qx must be a probability between 0 and 1; found {q_text!r}"
    return sex, birth_year, age, q


def _read_rows(path: Path, issues: list[ScenarioIssue]) -> dict[tuple[Sex, int, int], float]:
    name = path.name
    values: dict[tuple[Sex, int, int], float] = {}
    first_line: dict[tuple[Sex, int, int], int] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None or tuple(cell.strip() for cell in header) != COLUMNS:
            found = "nothing" if header is None else ",".join(header)
            issues.append(ScenarioIssue(f"{name}:1", f"columns must be {','.join(COLUMNS)}; found {found}"))
            return values
        for line, row in enumerate(reader, start=2):
            if not row:
                continue
            parsed = _parse_row(row)
            location = f"{name}:{line}"
            if isinstance(parsed, str):
                issues.append(ScenarioIssue(location, parsed))
                continue
            sex, birth_year, age, q = parsed
            key = (sex, birth_year, age)
            if key in values:
                first_seen = first_line[key]
                cohort = f"{sex}, birth year {birth_year}, age {age}"
                message = f"duplicate row for {cohort} (first on line {first_seen})"
                issues.append(ScenarioIssue(location, message))
                continue
            values[key] = q
            first_line[key] = line
    if not values and not issues:
        issues.append(ScenarioIssue(f"{name}:2", "the table has no rows"))
    return values


def _read_meta(
    path: Path, mortality: MortalityAssumptions | None, issues: list[ScenarioIssue]
) -> dict[str, object]:
    sidecar = sidecar_path(path)
    if not sidecar.is_file():
        issues.append(
            ScenarioIssue(sidecar.name, f"provenance sidecar not found next to {path.name}: {sidecar}")
        )
        return {}
    try:
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(ScenarioIssue(sidecar.name, f"not valid JSON: {exc}"))
        return {}
    if not isinstance(meta, dict):
        issues.append(ScenarioIssue(sidecar.name, "must be a JSON object"))
        return {}
    for key in REQUIRED_META:
        if key not in meta:
            issues.append(ScenarioIssue(f"{sidecar.name}:{key}", "missing required key"))
    if mortality is not None:
        for key in CHECKED_AGAINST_CONFIG:
            expected = getattr(mortality, key)
            if key in meta and meta[key] != expected:
                message = f"data file is {meta[key]!r} but the config's mortality.{key} is {expected!r}"
                issues.append(ScenarioIssue(f"{sidecar.name}:{key}", message))
    return meta


def load_mortality_table(path: Path, mortality: MortalityAssumptions | None = None) -> MortalityTable:
    """Load and validate ``path`` and its sidecar; with ``mortality`` also check source/geography/projection.

    Raises ``MortalityTableError`` listing every problem (file:line locations) or ``FileNotFoundError``.
    """
    if not path.is_file():
        raise FileNotFoundError(f"mortality data file not found: {path}")
    issues: list[ScenarioIssue] = []
    values = _read_rows(path, issues)
    meta = _read_meta(path, mortality, issues)
    if issues:
        raise MortalityTableError(issues)
    births = [birth for _, birth, _ in values]
    first, last = min(births), max(births)
    max_age = max(age for _, _, age in values)
    grids: dict[Sex, NDArray[np.float64]] = {
        sex: np.full((last - first + 1, max_age + 1), np.nan) for sex in SEXES
    }
    for (sex, birth_year, age), q in values.items():
        grids[sex][birth_year - first, age] = q
    for grid in grids.values():
        grid.flags.writeable = False
    return MortalityTable(path=path, meta=meta, first_birth_year=first, grids=grids)


def _age_ranges(ages: list[int]) -> str:
    """[91, 92, 93, 97] -> '91-93, 97' (ASCII, for CLI output)."""
    spans: list[list[int]] = []
    for age in ages:
        if spans and age == spans[-1][1] + 1:
            spans[-1][1] = age
        else:
            spans.append([age, age])
    return ", ".join(str(low) if low == high else f"{low}-{high}" for low, high in spans)


def coverage_issues(table: MortalityTable, scenario: Scenario) -> list[ScenarioIssue]:
    """Ages each person needs that the table lacks: their age at the As-Of month up to :data:`AGE_MAX`.

    Ages are completed years counted from the birth month; above 100 the age-100 rate is used (SPEC §4.3).
    """
    issues: list[ScenarioIssue] = []
    as_of = scenario.model.as_of_date
    for index, person in enumerate(scenario.people):
        birth_year = person.date_of_birth.year
        age_now = month_index(person.date_of_birth.replace(day=1), as_of) // 12
        needed = range(min(age_now, AGE_MAX), AGE_MAX + 1)
        missing = [age for age in needed if not table.has(person.sex, birth_year, age)]
        if missing:
            message = (
                f"{table.path.name} has no {person.sex} rates for birth year {birth_year} at age(s) "
                f"{_age_ranges(missing)}; the model needs ages {needed.start}-{AGE_MAX}"
            )
            issues.append(ScenarioIssue(f"people[{index}].date_of_birth", message))
    return issues


def monthly_death_probabilities(
    table: MortalityTable, person: Person, as_of: date, horizon_months: int
) -> NDArray[np.float64]:
    """Probability of dying during each simulated month, shape (horizon_months,), for one person.

    Month t uses the person's age in completed years at that month's start, counted from the birth month,
    and the cohort rate q(x, b + x) (ages above 100 hold the age-100 rate), converted with
    q_m = 1 − (1 − q)^(1/12) (SPEC §7.2; data-and-calibration §1).
    """
    months_old = month_index(person.date_of_birth.replace(day=1), as_of) + np.arange(horizon_months)
    annual = table.annual_q(person.sex, person.date_of_birth.year, months_old // 12)
    monthly: NDArray[np.float64] = 1.0 - (1.0 - annual) ** (1.0 / 12.0)
    return monthly


def survival_curve(monthly_q: NDArray[np.float64]) -> NDArray[np.float64]:
    """S_0 = 1, S_{t+1} = S_t (1 − q_m,t): probability of being alive at the start of month t, (H + 1,)."""
    curve: NDArray[np.float64] = np.concatenate(
        [[1.0], np.cumprod(1.0 - np.asarray(monthly_q, dtype=np.float64))]
    )
    return curve


def sample_death_months(
    scenario: Scenario, table: MortalityTable, rng: np.random.Generator, n_paths: int
) -> NDArray[np.int64]:
    raise NotImplementedError
