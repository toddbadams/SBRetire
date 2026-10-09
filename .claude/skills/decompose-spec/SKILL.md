---
name: decompose-spec
description: Decompose docs/SPEC.md (or one section of it) into epics under docs/epics/ and buildable feature milestones (F-NNN) in Backlog.md, with SPEC-section traceability and dependency order. Use when the user says "decompose the spec", "break the spec into features", "plan the build", or after SPEC.md changes. Produces the plan only — per-feature detail comes from /design-brief.
metadata:
  version: "1.0.0"
---

# Decompose Spec

Turn the authoritative specification into an ordered, traceable plan: **SPEC → epics → feature milestones**. Tasks are *not* minted here — each feature gets its tasks from `/design-brief`.

## Inputs

- `docs/SPEC.md` — authoritative. Cite sections as `SPEC §N`.
- `docs/THESAURUS.md` — use its terms in every title.
- `backlog/docs/decisions/` — settled decisions; don't re-open them.
- Existing `docs/epics/*.md` and `mcp__backlog__milestone_list` — never duplicate an existing epic or F-number.

Optional argument: a SPEC section (`/decompose-spec §9`) to decompose only that part, or `refresh` to reconcile the plan after SPEC.md changed.

## Step 1 — Inventory the spec

Read SPEC.md end to end. Build a coverage table, one row per *requirement-bearing* section/subsection:

| SPEC § | Requirement summary | Kind (capability / constraint / test / decision) | Covered by |
|---|---|---|---|

- **Capability** — something the code must do (load config, sample mortality, write CSV).
- **Constraint** — a rule every capability obeys (no tax logic, no live downloads, CRN, reproducibility). Constraints go into CLAUDE.md hard constraints / the Backlog DoD, not into features — but note which feature first *enforces* each one.
- **Test** — SPEC §17 items. Each is attached to the feature that makes it passable.
- **Decision** — SPEC §18 items. Each is attached to the feature that must resolve it, which records it in `backlog/docs/decisions/`.

Every requirement must end up with a non-empty "Covered by". Unmapped rows are a defect in the plan — surface them.

## Step 2 — Group into epics

An epic is a coherent capability area that ships user-visible value when its features are done. Aim for 4–8 epics for a spec this size. Suggested shape for SBRetire V1 (adjust to what the spec actually says):

1. **Foundations** — config schema + validation, as-of date, Random Streams/seed plumbing, run metadata.
2. **Stochastic inputs** — inflation process + calibration data; mortality data ingest, mapping, monthly sampling.
3. **Household cash flows** — income streams (start/end, linking, survivor %), spending with survivor factor.
4. **Simulation engine** — monthly portfolio accounting, depletion/shortfall, censoring, path outcomes, vectorised Monte Carlo.
5. **Analysis & optimization** — success metrics + MC standard error, budget bisection, return search, CRN.
6. **Reporting & release** — the three CSVs + metadata, README, acceptance-criteria sweep (SPEC §17.3).

## Step 3 — Slice epics into feature milestones

Each feature (milestone `F-NNN <Title>`) must be:

- **Vertical and testable on its own** — it ends with green tests that exercise real behaviour, not a stub.
- **One `/design-brief` + `/implement` cycle** — roughly 2–6 tasks. Split anything bigger.
- **Traceable** — lists the SPEC §§ it implements, the §17 tests it makes pass, and the §18 decisions it must record.
- **Ordered** — explicit `depends_on` F-numbers. The first feature must produce a runnable thin slice as early as possible (e.g. deterministic single-path engine with zero inflation and fixed deaths), then widen.

Apply `/decomposing-tasks` slicing guidance (vertical over horizontal, SPIDR). Prefer a walking skeleton early: config → one deterministic path → CSV, then add stochasticity.

## Step 4 — Present and confirm

Show the user, before writing anything:

1. Epic list with one-line goals.
2. Feature table: `F-NNN | Title | Epic | SPEC §§ | §17 tests | §18 decisions | depends_on`.
3. The coverage table's unmapped rows (should be none) and any SPEC ambiguities found — offer `/grill-with-docs` for those.

Ask one question at a time for changes. Don't write until the user approves the plan.

## Step 5 — Write

1. **Epics** — `docs/epics/<kebab-slug>.md` from `docs/epics/_TEMPLATE.md`. Fill `milestones:` with `{ id: F-NNN, title, status: proposed }`.
2. **Roadmap** — `docs/epics/roadmap.md`: ordered feature table (status column: proposed / briefed / in progress / done), `**Last updated**` line, `## Change Log` (newest first).
3. **Milestones** — `mcp__backlog__milestone_add` per feature, title `F-NNN <Title>`. F-numbers are sequential; check `milestone_list` for the highest existing first. Never invent an id the tool assigns.
4. **Coverage** — append the final coverage table to the roadmap so every SPEC § → F-NNN mapping is reviewable.

Commit the named files only: `git add docs/epics/ backlog/milestones/` then `docs(plan): decompose SPEC into epics and F-milestones`.

## Step 6 — Hand off

Recommend the first feature to brief (lowest F-number with no unmet `depends_on`) and offer `/design-brief F-NNN`.

## Refresh mode

When SPEC.md changes: diff it (`git diff -- docs/SPEC.md`), re-run Step 1 for changed sections only, and propose additions/edits to epics and milestones. Never renumber or delete a milestone that has tasks; mark it `superseded` in the epic instead.
