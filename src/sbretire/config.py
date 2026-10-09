"""Scenario configuration: loading and validation (SPEC §4)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple


class ScenarioIssue(NamedTuple):
    location: str
    message: str


class ScenarioError(ValueError):
    def __init__(self, issues: tuple[ScenarioIssue, ...]) -> None:
        super().__init__()
        self.issues = issues


class Scenario:
    pass


@dataclass(frozen=True)
class LoadedScenario:
    scenario: Scenario
    source_path: Path | None
    warnings: tuple[ScenarioIssue, ...]


def parse_scenario(
    raw: Mapping[str, object], *, base_dir: Path, require_data_files: bool = False
) -> LoadedScenario:
    raise NotImplementedError
