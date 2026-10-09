# SBRetire — Development Lifecycle

How work flows from `docs/SPEC.md` to verified code. Adapted (slimmed) from SBFoundation's SDLC.

## 1. Artifacts and IDs

| Level | Where | ID | Created by |
|---|---|---|---|
| Specification | `docs/SPEC.md` | `SPEC §N` | user |
| Epic | `docs/epics/<slug>.md` (from `_TEMPLATE.md`) | slug | `/decompose-spec` |
| Roadmap | `docs/epics/roadmap.md` | — | `/decompose-spec` |
| Feature | Backlog.md milestone `F-NNN <Title>` | `F-NNN` (milestone file id `m-N`) | `/decompose-spec`, `/design-brief` |
| Optimization | milestone `O-NNN <Title>` | `O-NNN` | `/design-brief` |
| Bug | tasks on the parent feature's milestone, title `B-NNN.M: …` | `B-NNN.M` | `/backlog-add`, `/design-brief` |
| Design brief | `docs/backlog/<type>-<kebab>-design-brief.md` | same as feature/bug | `/design-brief` |
| Task | `backlog/tasks/task-NNN - <Title>.md` | `TASK-NNN` | `/design-brief`, `/backlog-add` |
| Decision | `backlog/docs/decisions/doc-00N - <Topic>-Decisions.md`, `## N.` sections | topic §N | `/grill-with-docs`, `/design-brief` |
| Glossary | `docs/THESAURUS.md` | term | `/ubiquitous-language` |

Backlog state (tasks, milestones, decision docs) is written through the Backlog.md MCP / CLI, never hand-edited.

## 2. Flow

```
SPEC.md ──/decompose-spec──▶ epics + F-milestones + roadmap
        ──/design-brief────▶ brief + tasks (To Do)
        ──/implement───────▶ test commit → code commit per task (Verification)
        ──/verify──────────▶ Done (or back to To Do with failure note)
        ──milestone done───▶ brief/roadmap/epic marked delivered
```

`/backlog-next` tells you where you are and hands off to the right step. `/grill-with-docs` and `/ubiquitous-language` are used whenever language or a design decision is fuzzy. `/improve-codebase-architecture` is run periodically between features.

## 3. Task statuses

`To Do → In Progress → Verification → Done`. Only `/verify` moves a task to Done.

## 4. Validation tiers

- **T1** — unit tests, ruff, mypy --strict (`scripts/check.py --fast`).
- **T2** — seeded end-to-end run on a small fixture scenario (integration tests).
- **T3** — statistical/regression snapshot: known-answer checks (closed-form cases) and pinned-seed output snapshots.

Evidence rules: every acceptance criterion names the test that proves it; every seed- or date-dependent claim pins the seed / as-of date.

## 5. Commits

Straight to `main` (single developer). Per task: `test(TASK-NNN): …` then `feat(F-NNN/TASK-NNN): …` including the task file. Governance: `docs(F-NNN): …`. Stage named paths only.

## 6. Skills vs commands

Multi-step judgment workflows are skills in `.claude/skills/<name>/SKILL.md` with `metadata.version`. Thin wrappers around a script would be commands in `.claude/commands/`. A capability lives in one place.

| Skill | Origin |
|---|---|
| decompose-spec | new for SBRetire |
| design-brief, implement, verify | slimmed from SBFoundation |
| backlog-next, backlog-add | rewritten over Backlog.md (SBFoundation versions used a retired CLI) |
| grill-with-docs, improve-codebase-architecture | adapted from SBFoundation (mattpocock/skills lineage) |
| ubiquitous-language, decomposing-tasks | copied from SBFoundation |
