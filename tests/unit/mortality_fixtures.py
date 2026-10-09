"""Small hand-made mortality tables (CSV + sidecar) for tests."""

from __future__ import annotations

import json
from pathlib import Path

META = {
    "source": "ONS_2024_BASED",
    "geography": "UK",
    "projection": "principal",
    "edition": "2024-based",
    "publication_date": "2026-05-15",
    "retrieved": "2026-10-09",
    "units": "probability",
    "age_max": 100,
}
HEADER = "sex,birth_year,age,qx"


def write_table(
    directory: Path, rows: list[str], *, header: str = HEADER, meta: dict[str, object] | None = None
) -> Path:
    """Write ``ons_mortality.csv`` (+ sidecar unless ``meta`` is ``{}``) and return the CSV path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "ons_mortality.csv"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8", newline="\n")
    sidecar = META if meta is None else meta
    if sidecar:
        (directory / "ons_mortality.meta.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return path


def full_rows(births: range, ages: range, *, q: float = 0.01) -> list[str]:
    """Every (sex, birth_year, age) in the ranges with qx growing slightly with age."""
    return [
        f"{sex},{birth},{age},{q * (1 + age / 100)!r}"
        for sex in ("female", "male")
        for birth in births
        for age in ages
    ]
