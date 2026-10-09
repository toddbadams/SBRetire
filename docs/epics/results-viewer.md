---
epic: results-viewer
title: Results Viewer
status: delivered
spec_sections: [§11, §12, §13, §14, §15]
depends_on: [v1-1-enhancements]
milestones:
  - { id: F-021, title: Named Runs and results.json, status: done }
  - { id: F-022, title: HTML Results Viewer, status: done }
created: 2026-10-09
updated:
  - 2026-10-09: created from the user's request to display results on an HTML page designed with Claude Design
  - 2026-10-09: F-021 and F-022 done
---

# Results Viewer

## Goal

Let the household look at, and compare, model runs in a browser. Each run gets a name on the command line and one
JSON file holding everything it produced. A static HTML page, designed with Claude Design, picks a run (or two to
compare) and shows its results. The page works by double-clicking it, offline, with no server.

## Scope

**In** (user decisions, 2026-10-09):
- F-021 `sbretire run --name <name> [--overwrite]` writes everything to `output/runs/<name>/`, including
  `results.json` (one file per run, versioned schema with a JSON Schema in the repo). Every run also refreshes
  `output/runs/index.json` and `output/runs/runs.js` (`window.SBRETIRE_RUNS`), so the page needs no server.
  Unnamed runs behave as before (plus `results.json`). Claude Design hand-off in `docs/design/`: a sample built from
  `config/model.example.yaml` (never personal data) and a design prompt.
- F-022 The viewer page built from the Claude Design output (after the user has designed it).

**Out:**
- A web server, accounts or any upload of results; the CSVs stay the specified outputs (SPEC §15).

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-021 | Named Runs and results.json | §11–§15 | — | — | F-020 |
| F-022 | HTML Results Viewer | §11–§15 | — | — | F-021 + Claude Design output |

## Risks and open questions

- Personal data: `results.json` holds names, dates of birth and amounts. `output/` stays git-ignored, and only the
  example-config sample is committed or given to Claude Design.
