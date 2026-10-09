"""results_guide.md: a plain-English guide to one run's results (F-018)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sbretire.config import Scenario
from sbretire.inputs_report import InputRow
from sbretire.metrics import SuccessMetrics
from sbretire.optimization import BudgetResult, ReturnResult
from sbretire.randomness import ResolvedSeed

COLUMN_GUIDE: Final[dict[str, dict[str, tuple[str, str]]]] = {}


@dataclass(frozen=True)
class GuideContext:
    config: Path
    scenario: Scenario
    seed: ResolvedSeed
    input_rows: Sequence[InputRow]
    metrics: SuccessMetrics
    budgets: Sequence[BudgetResult]
    returns: Sequence[ReturnResult]


def results_guide_markdown(context: GuideContext) -> str:
    return ""


def write_results_guide(context: GuideContext, path: Path) -> Path:
    path.write_text(results_guide_markdown(context), encoding="utf-8")
    return path
