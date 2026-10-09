"""ONS cohort mortality table: loading, validation and lookup (SPEC §7; data-and-calibration §1)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sbretire.config import MortalityAssumptions, ScenarioIssue

Sex = Literal["male", "female"]


class MortalityTableError(ValueError):
    issues: tuple[ScenarioIssue, ...]


@dataclass(frozen=True)
class MortalityTable:
    path: Path
    meta: Mapping[str, object]

    def has(self, sex: Sex, birth_year: int, age: int) -> bool:
        raise NotImplementedError


def load_mortality_table(path: Path, mortality: MortalityAssumptions | None = None) -> MortalityTable:
    raise NotImplementedError
