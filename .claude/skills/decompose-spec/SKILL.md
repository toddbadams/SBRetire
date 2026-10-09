---
name: decompose-spec
description: Decompose docs/SPEC.md (or one section of it) into epics under docs/epics/ and buildable feature rows (F-NNN) in docs/epics/roadmap.md, with SPEC-section traceability and dependency order. Use when the user says "decompose the spec", "break the spec into features", "plan the build", or after SPEC.md changes. Produces the plan only — per-feature tasks come from /design-brief.
metadata:
  version: "2.0.0"
---

# Decompose Spec

Turn the authoritative specification into an ordered, traceable plan: **SPEC → epics → features**. Tasks are *not*
created here — each feature gets its tasks from `/design-brief`. Backlog format: `docs/project-sdlc.md`.

## Inputs

- `docs/SPEC.md` — authoritative. Cite sections as `SPEC §N`.
- `docs/THESAURUS.md` — use its terms in every title.
- `docs/decisions/` — settled decisions; don't re-open them.
- Existing `docs/epics/*.md` and `docs/epics/roadmap.md` — never duplicate an epic or reuse an F-number.

Optional argument: a SPEC section (`/decompose-spec §9`) to decompose only that part, or `refresh` to reconcile the
plan after SPEC.md changed.

## Step 1 — Inventory the spec

Read SPEC.md end to end. Build a coverage table, one row per *requirement-bearing* section/subsection:

| SPEC § | Requirement summary | Kind (capability / constraint / test / decision) | Covered by |
|---|---|---|---|

- **Capability** — something the code must do (load config, sample mortality, write CSV).
- **Constraint** — a rule every capability obeys (no tax logic, no live downloads, CRN, reproducibility). Constraints
  go into CLAUDE.md hard constraints / the definition of done, not into features — but note which feature first
  *enforces* each one.
- **Test** — SPEC §17 items. Each is attached to the feature that makes it passable.
- **Decision** — SPEC §18 items. Each is attached to the feature that must resolve it, which records it in
  `docs/decisions/`.

Every requirement must end up with a non-empty "Covered by". Unmapped rows are a defect in the plan — surface them.

## Step 2 — Group into epics

An epic is a coherent capability area that ships user-visible value when its features are done. Aim for 4–8 epics
for a spec this size.

## Step 3 — Slice epics into features

Each feature (`F-NNN <Title>`) must be:

- **Vertical and testable on its own** — it ends with green tests that exercise real behaviour, not a stub.
- **One `/design-brief` + `/implement` cycle** — roughly 2–6 tasks. Split anything bigger.
- **Traceable** — lists the SPEC §§ it implements, the §17 tests it makes pass, and the §18 decisions it must record.
- **Ordered** — explicit `depends_on` F-numbers. Produce a runnable thin slice as early as possible, then widen.

Apply `/decomposing-tasks` slicing guidance (vertical over horizontal, SPIDR).

## Step 4 — Present and confirm

Show the user, before writing anything:

1. Epic list with one-line goals.
2. Feature table: `F-NNN | Title | Epic | SPEC §§ | §17 tests | §18 decisions | depends_on`.
3. The coverage table's unmapped rows (should be none) and any SPEC ambiguities found — offer `/grill-with-docs`.

Ask one question at a time for changes. Don't write until the user approves the plan.

## Step 5 — Write

1. **Epics** — `docs/epics/<kebab-slug>.md` from `docs/epics/_TEMPLATE.md`. Fill `milestones:` with
   `{ id: F-NNN, title, status: proposed }`.
2. **Roadmap** — `docs/epics/roadmap.md`: one row per feature in build order, exactly
   `| F-NNN | Title | [epic](epic.md) | depends_on | proposed |`; a `**Last updated**` line; the §18 decision → feature
   table; the coverage table; `## Change Log` (newest first). Next F-number = highest in the roadmap + 1.
3. Run `uv run python scripts/backlog_check.py` — fix every problem it reports.

Commit the named files only: `git add docs/epics/` then `docs(plan): decompose SPEC into epics and features`.

## Step 6 — Hand off

Recommend the first feature to brief (`uv run python scripts/backlog_check.py --next` → NEXT FEATURE) and offer
`/design-brief F-NNN`.

## Refresh mode

When SPEC.md changes: diff it (`git diff -- docs/SPEC.md`), re-run Step 1 for changed sections only, and propose
additions/edits to epics and roadmap rows. Never renumber or delete a feature that has a brief; set its status to
`superseded` in the roadmap and epic instead.
