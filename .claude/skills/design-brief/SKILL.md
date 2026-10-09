---
name: design-brief
description: Author a design brief (and ExecPlan) for one feature (F-NNN), optimization (O-NNN) or bug fix (B-NNN.M) by interviewing the user one question at a time, then mint the milestone if needed and break the brief into Backlog.md tasks. Use when the user says "brief F-003", "plan this feature", "design the fix for…", or after /decompose-spec picks the next feature.
metadata:
  version: "1.0.0"
---

# Design Brief

Interview relentlessly until we share one understanding, write it down as a brief, then split it into tasks that `/implement` can execute with TDD. **This skill does not write production code.**

## Step 0 — Type gate

Ask: **Feature**, **Optimization**, or **Bug**?

- Feature → an existing `F-NNN` milestone from `/decompose-spec`, or mint the next one.
- Optimization → `O-NNN`; needs a behaviour invariant and baseline numbers.
- Bug → `B-<parent F>.<M>`; must name its parent feature. Bugs never get their own milestone — their tasks go on the parent's.

## Step 1 — Scope and context

1. One-sentence scope, confirmed by the user.
2. Read cheaply: the feature's row in `docs/epics/roadmap.md` and its epic, the SPEC §§ it cites, `docs/THESAURUS.md`, relevant `backlog/docs/decisions/`, and the code it touches. Follow `grill-with-docs/DOMAIN-AWARENESS.md`.

## Step 2 — Decision tree interview

Ask **one question at a time**, each formatted:

> **Q:** …
> **My recommendation:** … (with the reason, citing SPEC § / code)
> **Alternatives:** …

If the codebase or SPEC answers it, don't ask — state the answer and move on. **Settled is settled**: don't re-ask anything already in decisions or the brief.

**Feature branches** (skip ones that don't apply):
identity & name (thesaurus) · placement (module) · public interface (signatures, array shapes, dtypes) · config fields & validation · data inputs & provenance · randomness (which Random Stream, CRN impact) · timing convention (month ordering, death timing) · failure model & error messages · outputs (CSV columns/units, metadata) · SPEC §17 tests covered · SPEC §18 decisions resolved · docs to update · acceptance criteria.

**Optimization**: invariant that must not change (outputs identical for a fixed seed?) · baseline measurement (timing, memory, path count) · measurement plan · target.

**Bug**: symptom and evidence (command + output) · root-cause hypothesis marked **UNVERIFIED** until reproduced · the regression test that fails today · fix plan.

## Step 3 — Write the brief

Path: `docs/backlog/<feature|optimization|bugfix>-<kebab>-design-brief.md`

```markdown
---
id: F-NNN            # or O-NNN / B-NNN.M
type: feature        # feature | optimization | bug
parent: <epic slug or F-NNN for bugs>
status: planned      # planned | in-progress | done
complexity: <1-8>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
# <Title>

## 1. Purpose            — what and why, citing SPEC §§ (bugs: §1a Symptom, §1b Evidence, §1c Hypothesis, §1d Regression test)
## 2. Settled Decisions  — table: Decision | Choice | Why | Source (SPEC § / decision doc)
## 3. Context            — current code state, constraints that apply
## 4. Touch-points       — New / Modified / Deleted files tables
## 5. Interfaces         — signatures, array shapes, config keys, CSV columns
## 6. Plan of Work       — ordered steps
## 7. Validation         — T1 unit + ruff + mypy · T2 seeded end-to-end run on a fixture YAML · T3 statistical/regression snapshot (when applicable). Name the test for each AC.
## 8. Decision Log       — append-only, dated
## 9. Surprises          — append-only, dated (filled during implementation)
## 10. Task Breakdown    — TASK ids once minted
## 11. Open Questions
## 12. Acceptance Criteria — numbered, each objectively checkable
```

**Evidence rules** (apply to every AC):
- **Named test** — each AC names the test that would fail if the AC were broken. A pass count is not evidence.
- **Pinned randomness** — any seed- or date-dependent AC pins the seed / as-of date in the test.

Record any SPEC §18 decision resolved here in the matching `backlog/docs/decisions/` topic doc via `mcp__backlog__document_update` (format: `grill-with-docs/ADR-FORMAT.md`).

## Step 4 — Milestone and tasks

1. If the milestone doesn't exist: `mcp__backlog__milestone_list` → next number → `mcp__backlog__milestone_add` (`F-NNN <Title>`). Add `{id, title, status: proposed}` to the epic's `milestones:`.
2. Split the plan into tasks: each is one session of work, has a verifiable done condition, and references the brief section. Prefer vertical slices; tests-first must be possible.
3. Show the task list; confirm with the user.
4. `mcp__backlog__task_create` for each: title, description (brief path + section), acceptance criteria (from brief §12, with named tests), `milestone`, labels (`feature`/`bug`/`optimization` + an area label), `dependencies`, `references` (files). Never invent task ids.
5. Write the TASK ids into brief §10. Update the roadmap row to `briefed`.

## Step 5 — Close

Commit named paths only: the brief, the epic, `docs/epics/roadmap.md`, `backlog/tasks/`, `backlog/milestones/`, `backlog/docs/decisions/`:
`docs(F-NNN): design brief + tasks`.

Offer `/implement F-NNN`.

## Refining an existing brief

Edit in place. Append to Decision Log / Surprises — never rewrite history. Bump `updated:`.
