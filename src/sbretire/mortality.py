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
from pathlib import Path
from typing import Final, Literal, get_args

import numpy as np
from numpy.typing import NDArray

from sbretire.config import MortalityAssumptions, Scenario, ScenarioIssue
from sbretire.metadata import DataFileRecord

Sex = Literal["male", "female"]
AGE_MAX: Final = 100
"""Last tabulated age; above it the cohort's age-100 rate is held (data-and-calibration §1)."""
SEXES: Final[tuple[Sex, ...]] = get_args(Sex)
COLUMNS: Final = ("sex", "birth_year", "age", "qx")
SIDECAR_SUFFIX: Final = ".meta.json"
REQUIRED_META: Final = ("source", "geography", "projection", "publication_date", "retrieved")
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
        raise NotImplementedError

    def data_file_record(self) -> DataFileRecord:
        raise NotImplementedError


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


def coverage_issues(table: MortalityTable, scenario: Scenario) -> list[ScenarioIssue]:
    raise NotImplementedError
