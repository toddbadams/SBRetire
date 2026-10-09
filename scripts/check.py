#!/usr/bin/env python
"""Run the full quality gate: ruff lint, ruff format check, mypy (strict), pytest.

Usage:
    uv run python scripts/check.py           # full gate (what CI runs)
    uv run python scripts/check.py --fast    # skip tests marked @pytest.mark.slow
    uv run python scripts/check.py --fix     # apply ruff fixes + formatting first

Exits non-zero on the first failing step. This is the single gate referenced by
CLAUDE.md, the Backlog definition of done, and CI.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(label: str, cmd: list[str]) -> None:
    print(f"\n=== {label}: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        print(f"\nFAILED: {label}", flush=True)
        sys.exit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fast", action="store_true", help="skip slow tests")
    parser.add_argument("--fix", action="store_true", help="apply ruff fixes and formatting before checking")
    args = parser.parse_args()

    py = sys.executable
    if args.fix:
        _run("ruff fix", [py, "-m", "ruff", "check", "--fix", "."])
        _run("ruff format", [py, "-m", "ruff", "format", "."])
    _run("ruff lint", [py, "-m", "ruff", "check", "."])
    _run("ruff format", [py, "-m", "ruff", "format", "--check", "."])
    _run("mypy", [py, "-m", "mypy"])
    pytest_cmd = [py, "-m", "pytest", "-q"]
    if args.fast:
        pytest_cmd += ["-m", "not slow"]
    _run("pytest", pytest_cmd)
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
