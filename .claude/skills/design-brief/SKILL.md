---
name: design-brief
description: Author a design brief for one feature (F-NNN), optimization (O-NNN) or bug fix (B-NNN.N) by interviewing the user one question at a time, then write its tasks inline in the brief (markdown backlog). Use when the user says "brief F-003", "plan this feature", "design the fix for…", or after /decompose-spec picks the next feature.
metadata:
  version: "2.0.0"
---

# Design Brief

Interview relentlessly until we share one understanding, write it down as a brief with its tasks, so `/implement`
can execute them with TDD. **This skill does not write production code.** Backlog format: `docs/project-sdlc.md` §2.

## Step 0 — Type gate

Ask: **Feature**, **Optimization**, or **Bug**? (Skip if the argument already says, e.g. `F-003`.)

- Feature → its row in `docs/epics/roadmap.md`, or add the next F-number row (status `proposed`) and its epic entry.
- Optimization → next `O-NNN` roadmap row; needs a behaviour invariant and baseline numbers.
- Bug → `B-<parent NNN>.<N>`; must name its parent feature. A small bug is just a task in the parent brief (use
  `/backlog-add`); a bug needing design gets its own `bugfix-*` brief with `parent: F-NNN` and B- tasks.

## Step 1 — Scope and context

1. One-sentence scope, confirmed by the user.
2. Read cheaply: the feature's roadmap row and epic, the SPEC §§ it cites, `docs/THESAURUS.md`, relevant
   `docs/decisions/`, and the code it touches. Follow `grill-with-docs/DOMAIN-AWARENESS.md`.

## Step 2 — Decision tree interview

Ask **one question at a time** (AskUserQuestion, recommended option first), each with:

> **Q:** … · **My recommendation:** … (with the reason, citing SPEC § / code) · **Alternatives:** …

If the codebase or SPEC answers it, don't ask — state the answer and move on. **Settled is settled**: don't re-ask
anything already in `docs/decisions/` or the brief.

**Feature branches** (skip ones that don't apply):
identity & name (thesaurus) · placement (module) · public interface (signatures, array shapes, dtypes) · config fields
& validation · data inputs & provenance · randomness (which Random Stream, CRN impact) · timing convention · failure
model & error messages · outputs (CSV columns/units, metadata) · SPEC §17 tests covered · SPEC §18 decisions resolved
· docs to update · acceptance criteria.

**Optimization**: invariant that must not change (outputs identical for a fixed seed?) · baseline measurement ·
measurement plan · target.

**Bug**: symptom and evidence (command + output) · root-cause hypothesis marked **UNVERIFIED** until reproduced · the
regression test that fails today · fix plan.

## Step 3 — Write the brief

Path: `docs/backlog/<feature|optimization|bugfix>-<kebab>-design-brief.md`

```markdown
---
id: F-NNN            # or O-NNN / B-NNN.N
type: feature        # feature | optimization | bug
parent: <epic slug, or F-NNN for bugs>
status: planned      # planned | in-progress | done
complexity: <1-8>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
# <Title>

## 1. Purpose            — what and why, citing SPEC §§ (bugs: §1a Symptom, §1b Evidence, §1c Hypothesis, §1d Regression test)
## 2. Settled Decisions  — table: # | Decision | Choice | Why | Source (SPEC § / docs/decisions/<topic> §N)
## 3. Context            — current code state, constraints that apply
## 4. Touch-points       — New / Modified / Deleted files tables
## 5. Interfaces         — signatures, array shapes, config keys, CSV columns
## 6. Plan of Work       — ordered steps
## 7. Validation         — T1 unit + ruff + mypy · T2 seeded end-to-end run · T3 statistical/regression snapshot
## 8. Decision Log       — append-only, dated
## 9. Surprises          — append-only, dated (filled during implementation)
## 10. Tasks             — task blocks (format below)
## 11. Open Questions
## 12. Acceptance Criteria — numbered, each objectively checkable, each naming its test
```

**Evidence rules** (every AC, in §12 and in tasks):
- **Named evidence** — the test (`` `test_…` ``) or command (`` `check: …` ``) that would fail if the AC were broken.
- **Pinned randomness** — any seed- or date-dependent AC pins the seed / as-of date in the test.

Record any SPEC §18 decision resolved here as a new numbered entry in the matching `docs/decisions/<topic>.md`
(format: `grill-with-docs/ADR-FORMAT.md`) and strike it from that file's open list.

## Step 4 — Tasks

1. Split §6 into tasks: each is one session of work, has a verifiable done condition, and tests-first is possible.
   Prefer vertical slices. Map every §12 AC to exactly one task.
2. Show the list (id, title, ACs, depends on); confirm with the user.
3. Write them into `## 10. Tasks`, ids `F-NNN.1`, `F-NNN.2`, … (B-/O- likewise), each block:

   ```markdown
   ### F-NNN.N <Title>
   - **Status**: To Do
   - **Depends on**: — | F-NNN.M, …

   What to build, files, brief sections it implements.

   **Acceptance criteria**
   - [ ] <criterion> — `test_name`
   ```

   Don't copy the definition of done into tasks — it lives once in `docs/project-sdlc.md` §4.
4. Roadmap row status → `briefed`; the epic's `milestones:` entry → `briefed`; roadmap Change Log bullet.
5. Run `uv run python scripts/backlog_check.py` — fix every problem it reports.

## Step 5 — Close

Commit named paths only — the brief, the epic, `docs/epics/roadmap.md`, touched `docs/decisions/*.md`:
`docs(F-NNN): design brief + tasks`. Offer `/implement F-NNN`.

## Refining an existing brief

Edit in place. Append to Decision Log / Surprises — never rewrite history. Bump `updated:`. New tasks take the next
free number; never renumber existing tasks.
