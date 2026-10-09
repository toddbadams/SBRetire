#!/usr/bin/env python
"""Claude Code PostToolUse hook: ruff-check a just-edited Python file.

Wired into `.claude/settings.json` on `Edit|Write`. Reads the hook JSON payload
on stdin; if the edited file is a `.py` file inside this repo, runs
`ruff check` on it. On failure it exits 2 so the ruff output is fed back to the
model for immediate self-correction.

Fail-open: any unexpected error (no payload, ruff missing, path outside repo)
exits 0 so the hook can never wedge an editing session. The heavier gate
(mypy + pytest) stays in `scripts/check.py` and CI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        raw = (payload.get("tool_input") or {}).get("file_path")
        if not raw:
            return 0
        path = Path(raw).resolve()
        if path.suffix != ".py":
            return 0
        path.relative_to(REPO_ROOT)
    except (json.JSONDecodeError, ValueError, OSError):
        return 0

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--quiet", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if result.returncode == 1:
        sys.stderr.write(f"ruff found issues in {path.name}:\n{result.stdout}{result.stderr}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
