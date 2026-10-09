---
name: implement
description: Implement a Backlog.md milestone's tasks (or named TASK ids) with TDD — commit pending backlog/doc changes, write failing tests, make them pass, one test commit + one code commit per task on main, move each task to Verification, then hand off to /verify. Use when the user says "implement F-003", "build TASK-012", or after /design-brief.
metadata:
  version: "1.0.0"
---

# Implement

`/implement <F-NNN | milestone id | TASK-NNN …>`

## Step 1 — Resolve the task set

1. Read `backlog/tasks/*.md` frontmatter in bulk (Grep `^milestone:` / `^status:` / `^dependencies:`). Keep tasks whose `milestone:` matches the requested milestone's id (`m-N`), or the named TASK ids. Don't rely on fuzzy milestone filters.
2. Drop `Done` tasks. Note `Verification` tasks (already built — they go to `/verify`).
3. Order by `dependencies` then id. `dependencies:` may be inline (`[]`) or a block list — handle both.
4. Show the list (id, title, status, deps) and the brief path. Confirm.

## Step 2 — Clean baseline

1. `git status --porcelain`. If `backlog/` or `docs/` are dirty, commit them first as `chore(backlog): sync before F-NNN`. Any other dirty file: stop and ask.
2. Run `uv run python scripts/check.py --fast`. If red before you start, stop and report — don't build on a broken baseline.

## Step 3 — Per task (TDD)

For each task in order:

1. `mcp__backlog__task_edit` → `status: In Progress`.
2. Read the task, its brief section, the SPEC §§ it cites, and `docs/THESAURUS.md` terms involved.
3. **Red** — write tests first in `tests/unit/test_<module>.py` (or `tests/integration/`), named `test_<unit>_<scenario>_<expected>`, fully type-annotated. Each AC maps to at least one named test.
   - Run them; confirm they **fail on assertions**, not on import errors. If an import fails because the module doesn't exist yet, create only the empty module/signature needed to import — no logic.
   - Commit: `test(TASK-NNN): <what is specified>`.
4. **Green** — implement the minimum production code in `src/sbretire/` to pass. Follow CLAUDE.md hard constraints (vectorised over paths, injected Random Streams, no tax logic, no hard-coded assumptions, no network).
5. **Refactor** — tidy while green. Docstrings on new public functions (units: nominal GBP vs today's GBP, monthly vs annual).
6. Run `uv run python scripts/check.py --fast`. Fix until green. **Never** weaken, skip, xfail, or delete a test to go green — if a test is wrong, stop and ask.
7. Tick ACs and DoD items via `mcp__backlog__task_edit`, add implementation notes (what changed, any surprise → also append to brief §9 Surprises), set `status: Verification`.
8. Commit code + the task file together: `feat(F-NNN/TASK-NNN): <summary>` (or `fix(B-NNN.M/TASK-NNN)`, `perf(O-NNN/TASK-NNN)`). Stage named paths only — never `git add .`.

**Subagents (optional)**: independent tasks (no shared files, no dependency) may be delegated one per general-purpose subagent with a self-contained prompt (task text, ACs, brief excerpt, constraints, the red→green→check steps). The subagent leaves code uncommitted and returns a short receipt (files changed, tests added, check result). You review the diff, then do steps 7–8 yourself. Never run two subagents that touch the same file.

**Decisions**: if implementation forces a SPEC §18 decision not in the brief, stop, ask the user, then record it in `backlog/docs/decisions/` via `mcp__backlog__document_update` and the brief's Decision Log.

## Step 4 — Full gate and verify

1. `uv run python scripts/check.py` (full, including slow tests). Red → group failures by root cause, reproduce each alone, fix one root cause per commit.
2. Invoke `/verify <milestone>`.

## Step 5 — Close the milestone

When `/verify` reports every task in the milestone `Done`:
1. Brief frontmatter `status: done`; roadmap row → `done`; epic `milestones:` entry → `status: delivered`; prepend a Change Log bullet (absolute date).
2. Commit those named files: `docs(F-NNN): mark delivered`.
3. Report: tasks done, tests added, decisions recorded, anything deferred. Suggest the next feature from the roadmap.

`git push` only when the user asks.
