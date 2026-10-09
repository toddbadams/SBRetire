"""Render the results viewer to PDF for review (F-023)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RUNS = ROOT / "docs" / "design" / "sample" / "runs"


def find_browser() -> Path | None:
    return Path("browser")


def render(runs: Path, out: Path, browser: Path) -> list[Path]:
    return [out / "missing.pdf"]
