"""The run's inputs as rows: the console Inputs block and ``inputs.csv`` (F-017)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sbretire.config import Scenario
from sbretire.randomness import ResolvedSeed

INPUT_COLUMNS: Final = ("section", "item", "label", "value", "unit")


@dataclass(frozen=True)
class InputRow:
    section: str
    item: str
    label: str
    value: str
    unit: str


def scenario_input_rows(scenario: Scenario, seed: ResolvedSeed) -> list[InputRow]:
    return []


def write_inputs_csv(rows: Sequence[InputRow], path: Path) -> Path:
    path.write_text("", encoding="utf-8")
    return path


def format_inputs(config: Path, rows: Sequence[InputRow]) -> str:
    return ""
