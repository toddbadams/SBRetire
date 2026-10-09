---
name: verify
description: Walk every Backlog.md task in Verification status (optionally for one milestone), have a subagent run each task's objective checks, and route the result — pass → Done with a final summary, fail → back to To Do with a dated failure note. Use when the user says "verify", "/verify F-003", or when /implement hands off.
metadata:
  version: "1.0.0"
---

# Verify

`/verify [F-NNN | milestone id]`

Independent check that what `/implement` claimed is true. The verifier is read-only: it runs commands and reads code, it never edits.

## Step 1 — Queue

1. Read `backlog/tasks/*.md` frontmatter; keep `status: Verification`. If a milestone was given, post-filter on `milestone:`.
2. Sort by milestone then id. Announce the queue (id, title). Empty → say so and stop.

## Step 2 — Per task

1. `mcp__backlog__task_view` the task; read its brief section.
2. Build a **3–7 item checklist** of objective checks, each with a command and the expected result:
   - each AC's **named test** — `uv run pytest tests/unit/test_x.py::test_name -q` → passes;
   - the AC is actually asserted by that test (read it — a test that can't fail is not evidence);
   - greps for constraint violations in changed files (e.g. no `requests`/`urllib` imports, no tax terms, no hard-coded dates/amounts in `src/`);
   - seed-dependent claims: the test pins the seed;
   - `uv run ruff check <files>` and `uv run mypy` clean;
   - docs claimed updated really were (README / THESAURUS / data/README / decisions).
   If every check would be manual, mark **skip** and say why.
3. Spawn a general-purpose subagent with a self-contained prompt: repo path, task text, checklist, "read-only — do not edit files or run git write commands", and return **only** JSON:
   ```json
   {"verdict": "pass|fail|skip",
    "steps": [{"n": 1, "result": "pass|fail", "evidence": "<command + key output>"}],
    "failure_summary": "<empty on pass>"}
   ```
   Unparseable output = **fail**.
4. Route (one `mcp__backlog__task_edit` per decision, absolute dates):
   - **pass** → `status: Done`, `finalSummary`: what was delivered + "Verified by agent on YYYY-MM-DD via /verify" + the evidence lines.
   - **fail** → `status: To Do`, append a note `YYYY-MM-DD /verify FAIL:` + failing steps and evidence.
   - **skip** → no change; report why.

Tasks may be verified in parallel (one subagent each) — they're read-only.

## Step 3 — Summarise

Counts and ids for pass / fail / skip. For failures, the one-line cause each.

## Step 4 — Milestone complete?

If every task on the milestone is now `Done`, do `/implement` Step 5 (brief/roadmap/epic → done/delivered, Change Log bullet) and commit the named files only — never `git add backlog/`. Otherwise offer `/implement <milestone>` to fix the failures.
