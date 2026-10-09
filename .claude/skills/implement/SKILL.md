---
name: implement
description: Implement a feature's tasks (or named task ids like F-001.2) with TDD from the markdown backlog — write failing tests, make them pass, one test commit + one code commit per task on main, move each task to Verification in its brief, then hand off to /verify. Use when the user says "implement F-003", "build F-001.2", or after /design-brief.
metadata:
  version: "2.0.0"
---

# Implement

`/implement <F-NNN | O-NNN | task id …>` — backlog format: `docs/project-sdlc.md` §2.

## Step 1 — Resolve the task set

1. Find the brief: `docs/backlog/*-design-brief.md` whose frontmatter `id` matches (task ids: the brief holding that
   `### <id>` heading).
2. Read its `## 10. Tasks`. Drop `Done` tasks. `Verification` tasks are already built — they go to `/verify`.
3. Order by **Depends on**, then id. A dependency in another brief that isn't `Done` blocks the task — say so.
4. Show the list (id, title, status, depends on). Confirm.

## Step 2 — Clean baseline

1. `git status --porcelain`. If only `docs/` is dirty, commit it first as `chore(docs): sync before F-NNN`. Any
   other dirty file: stop and ask.
2. Run `uv run python scripts/check.py --fast`. If red before you start, stop and report.
3. First task of the feature: brief `status: in-progress`; roadmap row and epic entry → `in-progress`.

## Step 3 — Per task (TDD)

For each task in order:

1. Edit the task block: `- **Status**: In Progress`.
2. Read the task, its brief sections, the SPEC §§ it cites, and the `docs/THESAURUS.md` terms involved.
3. **Red** — write tests first in `tests/unit/test_<module>.py` (or `tests/integration/`), named
   `test_<unit>_<scenario>_<expected>` or exactly the name the AC gives, fully type-annotated. Each AC has its named
   test.
   - Run them; confirm they **fail on assertions**, not import errors. If an import fails because the module doesn't
     exist yet, create only the empty module/signature needed to import — no logic.
   - Commit: `test(F-NNN.N): <what is specified>`.
4. **Green** — implement the minimum production code in `src/sbretire/` to pass. Follow CLAUDE.md hard constraints.
5. **Refactor** — tidy while green. Docstrings on new public functions (units: nominal vs today's GBP, monthly vs
   annual).
6. Run `uv run python scripts/check.py --fast`. Fix until green. **Never** weaken, skip, xfail, or delete a test to
   go green — if a test is wrong, stop and ask.
7. In the brief: tick each AC `[x]` whose evidence now passes; append a dated `**Notes**` bullet (what changed, files);
   append any surprise to brief §9; set `- **Status**: Verification`.
8. Commit code + the brief together: `feat(F-NNN.N): <summary>` (`fix(B-NNN.N)`, `perf(O-NNN.N)`). Stage named paths
   only — never `git add .`.

**Subagents (optional)**: independent tasks (no shared files, no dependency) may each go to a general-purpose
subagent with a self-contained prompt (task block, brief excerpt, constraints, the red→green→check steps). It leaves
code uncommitted and returns a receipt (files changed, tests added, check result). You review the diff, then do steps
7–8 yourself. Never run two subagents that touch the same file, and only you edit the brief.

**Decisions**: if implementation forces a SPEC §18 decision not in the brief, stop, ask the user, then record it in
`docs/decisions/<topic>.md` and the brief's Decision Log.

## Step 4 — Full gate and verify

1. `uv run python scripts/check.py` (full, including slow tests and the backlog check). Red → group failures by root
   cause, reproduce each alone, fix one root cause per commit.
2. Invoke `/verify F-NNN`.

## Step 5 — Close the feature

When every task in the brief is `Done` (after `/verify`):
1. Brief frontmatter `status: done`, bump `updated:`; roadmap row → `done`; epic `milestones:` entry → `done`;
   prepend a roadmap Change Log bullet (absolute date).
2. `uv run python scripts/backlog_check.py` passes.
3. Commit those named files: `docs(F-NNN): mark done`.
4. Report: tasks done, tests added, decisions recorded, anything deferred. Suggest the next feature
   (`scripts/backlog_check.py --next`).

`git push` only when the user asks.
