"""results.json: every result of one run in one JSON document (F-021)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from sbretire.reporting import AnnualRow
from sbretire.results_guide import GuideContext

SCHEMA_VERSION: Final = "1.0"


def build_results(
    context: GuideContext,
    annual: Sequence[AnnualRow],
    *,
    name: str | None,
    config_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    return {}


def write_results_json(results: dict[str, Any], path: Path) -> Path:
    raise NotImplementedError
