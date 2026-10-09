---
name: verify
description: Walk every markdown-backlog task in Verification status (optionally for one feature), have a subagent run each task's objective checks, and route the result in the brief — pass → Done with a dated verification note, fail → back to To Do with a dated failure note. Use when the user says "verify", "/verify F-003", or when /implement hands off.
metadata:
  version: "2.0.0"
---

# Verify

`/verify [F-NNN | O-NNN]` — backlog format: `docs/project-sdlc.md` §2.

Independent check that what `/implement` claimed is true. The verifier subagent is read-only; only you edit briefs.

## Step 1 — Queue

1. Read `## 10. Tasks` of every `docs/backlog/*-design-brief.md` (or the one feature's brief); keep tasks with
   `- **Status**: Verification`.
2. Sort by feature then task id. Announce the queue. Empty → say so and stop.

## Step 2 — Per task

1. Read the task block and its brief sections.
2. Build a **3–7 item checklist** of objective checks, each a command with its expected result:
   - each AC's named evidence — `uv run pytest tests/unit/test_x.py::test_name -q` passes, or the `check:` command
     produces the stated result;
   - the test really asserts the AC (read it — a test that can't fail is not evidence);
   - constraint greps on changed files (no `requests`/`urllib`, no tax terms, no hard-coded dates/amounts in `src/`);
   - seed-dependent claims: the test pins the seed;
   - `uv run ruff check <files>` and `uv run mypy` clean;
   - docs claimed updated really were (README / THESAURUS / data/README / decisions).
   If every check would be manual, mark **skip** and say why.
3. Spawn a general-purpose subagent with a self-contained prompt: repo path, task block, checklist, "read-only — do
   not edit files or run git write commands", and return **only** JSON:
   ```json
   {"verdict": "pass|fail|skip",
    "steps": [{"n": 1, "result": "pass|fail", "evidence": "<command + key output>"}],
    "failure_summary": "<empty on pass>"}
   ```
   Unparseable output = **fail**. Tasks may be verified in parallel (one subagent each).
4. Route, editing the task block in the brief (absolute dates):
   - **pass** → `- **Status**: Done`; append `**Notes**` bullet `YYYY-MM-DD /verify PASS:` + one line per evidence.
   - **fail** → `- **Status**: To Do`; un-tick the failing ACs; append `YYYY-MM-DD /verify FAIL:` + failing steps.
   - **skip** → no status change; append `YYYY-MM-DD /verify SKIP: <why>`.

## Step 3 — Record

Run `uv run python scripts/backlog_check.py`, then commit the brief(s): `docs(F-NNN): verify <ids>`.
Summarise pass / fail / skip counts and ids, with a one-line cause per failure.

## Step 4 — Feature complete?

If every task in the brief is now `Done`, do `/implement` Step 5 (brief/roadmap/epic → `done`, Change Log bullet,
commit named files). Otherwise offer `/implement F-NNN` to fix the failures.
