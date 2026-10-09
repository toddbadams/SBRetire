# SBRetire — Development Lifecycle

How work flows from `docs/SPEC.md` to verified code. Adapted (slimmed) from SBFoundation's SDLC. The backlog is
plain markdown in this repository — no tracking tool (`docs/decisions/tooling-and-process.md` §4).

## 1. Artifacts and IDs

| Level | Where | ID |
|---|---|---|
| Specification | `docs/SPEC.md` | `SPEC §N` |
| Epic | `docs/epics/<slug>.md` (from `_TEMPLATE.md`) | slug |
| Roadmap | `docs/epics/roadmap.md` — one row per feature, the index of all work | — |
| Feature | roadmap row + design brief | `F-NNN` |
| Optimization | roadmap row + design brief | `O-NNN` |
| Design brief | `docs/backlog/<feature\|optimization\|bugfix>-<kebab>-design-brief.md` | same as its feature |
| Task | `### <ID> <title>` block inside its brief's `## 10. Tasks` | `F-NNN.N` / `O-NNN.N` |
| Bug | a task in the parent feature's brief, or its own bugfix brief (`parent: F-NNN`) | `B-NNN.N` (NNN = parent feature) |
| Decision | `docs/decisions/<topic>.md`, numbered `## N.` sections | `<topic> §N` |
| Glossary | `docs/THESAURUS.md` | term |

Ids are never reused. Next task number = highest `.N` in that brief + 1; next feature number = highest in the roadmap + 1;
next bug number = highest `B-NNN.N` for that parent across `docs/backlog/` + 1.

## 2. Task format

Inside a brief, under `## 10. Tasks`:

```markdown
### F-001.2 Cross-field and date consistency rules
- **Status**: To Do
- **Depends on**: F-001.1

What to build, which files, which brief sections.

**Acceptance criteria**
- [ ] Duplicate person ids are rejected — `test_duplicate_ids_rejected`
- [ ] README documents the command — `check: grep -n "sbretire validate" README.md`

**Notes**
- 2026-10-10: implementation note / surprise / verification result (append-only, absolute dates)
```

- **Status**: `To Do → In Progress → Verification → Done`. Only `/verify` sets `Done`.
- **Depends on**: `—` or comma-separated task ids (any brief).
- Every AC names its evidence: a test (`` `test_…` ``) or a command (`` `check: …` ``). An AC is ticked `[x]` by
  `/implement` when its evidence passes; `Verification` and `Done` require every AC ticked.

Feature status (roadmap `Status` column and epic `milestones[].status`, always equal):
`proposed → briefed → in-progress → done` (or `superseded`). Brief frontmatter `status`: `planned → in-progress → done`.

`scripts/backlog_check.py` enforces all of the above and runs inside `scripts/check.py`;
`python scripts/backlog_check.py --next` prints the next-work view.

## 3. Flow

```
SPEC.md ──/decompose-spec──▶ epics + roadmap rows (proposed)
        ──/design-brief────▶ brief + tasks (To Do); roadmap: briefed
        ──/implement───────▶ per task: test commit → code commit (Verification); roadmap: in-progress
        ──/verify──────────▶ Done (or back to To Do with a dated note)
        ──all tasks Done───▶ brief/roadmap/epic: done
```

`/backlog-next` says where you are and hands off. `/backlog-add` captures a bug or chore into an existing brief.
`/grill-with-docs` and `/ubiquitous-language` sharpen language and decisions; `/improve-codebase-architecture` runs
between features.

## 4. Definition of done (every task)

1. `uv run python scripts/check.py` passes (ruff, ruff format, mypy --strict, backlog check, pytest).
2. Tests written first for all changed production code; SPEC §17 tests covered where the task touches them.
3. Every AC ticked, each traceable to a SPEC section via the brief.
4. No tax logic, hard-coded personal assumptions or live data downloads in `src/` (SPEC §2, §4, §16).
5. Any SPEC §18 item resolved is recorded in `docs/decisions/`.
6. README / `docs/THESAURUS.md` / `data/README.md` updated where behaviour, terms or data provenance changed.

## 5. Validation tiers

- **T1** — unit tests, ruff, mypy --strict (`scripts/check.py --fast`).
- **T2** — seeded end-to-end run on a small fixture scenario (integration tests).
- **T3** — statistical/regression snapshot: known-answer checks (closed-form cases) and pinned-seed output snapshots.

Evidence rules: every acceptance criterion names the test that proves it; every seed- or date-dependent claim pins
the seed / as-of date.

## 6. Commits

Straight to `main` (single developer). Per task: `test(F-NNN.N): …` then `feat(F-NNN.N): …` including the brief.
Governance: `docs(F-NNN): …`. Stage named paths only. Push only when asked.

## 7. Skills vs commands

Multi-step judgment workflows are skills in `.claude/skills/<name>/SKILL.md` with `metadata.version`. Thin wrappers
around a script would be commands in `.claude/commands/`. A capability lives in one place.

| Skill | Origin |
|---|---|
| decompose-spec | new for SBRetire |
| design-brief, implement, verify | slimmed from SBFoundation; markdown backlog |
| backlog-next, backlog-add | rewritten over `scripts/backlog_check.py` and briefs |
| grill-with-docs, improve-codebase-architecture | adapted from SBFoundation (mattpocock/skills lineage) |
| ubiquitous-language, decomposing-tasks | copied from SBFoundation |
