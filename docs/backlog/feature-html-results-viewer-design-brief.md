---
id: F-022
type: feature
parent: results-viewer
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-022 HTML Results Viewer

## 1. Purpose

A static web page that shows the results of named runs (F-021): pick a run, read its results, compare two runs. It is
designed in Claude Design from a hand-off document, then built into the repo. All its styling comes from one
**common CSS theme**, a shared set of design tokens that every SBRetire page will use. The theme itself is still
to be determined and will be settled with Claude Design (SPEC §11–§15 results; epic `results-viewer`).

Requested by the user on 2026-10-09: "create a handoff document for claude design as part of F-022, include in this
design doc the requirement for a common css theme to be determined."

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Hand-off | `docs/design/claude-design-handoff.md`: purpose, data contract, page parts, wording and number rules, edge cases, theme requirement, deliverables | One document Claude Design can work from | user request |
| 2 | Common theme | Every colour, font, size, space, radius, shadow and chart colour comes from CSS custom properties in **one** `theme.css`; the page's own CSS uses only `var(--…)`. Light and dark are two token sets in that file. The palette, typography and token names are **to be determined**: Claude Design proposes them, and the chosen theme is recorded as a decision before the page is built | User: common CSS theme, to be determined | user request |
| 3 | Data | The page reads `window.SBRETIRE_RUNS` from `runs/runs.js` loaded with a `<script>` tag (F-021); no fetch, no server, no network | Works from `file://`, offline | F-021 §2 #6 |
| 4 | Sample | `docs/design/sample/runs/` from the example config only: `example-base` and `example-stretch` (9,500/month, 4 % return, 12-month reserve, so failures and a reserve table appear) | Informative charts; no personal data | F-021 §2 #8 |
| 5 | Placement of the built page | Open: decided in F-022.3 with the design (e.g. `viewer/` copied next to `output/runs/`) | Depends on the design's file set | — |

## 3. Context

- F-021 delivers `results.json`, `schemas/results.schema.json`, `index.json`, `runs.js` and the sample generator.
- Wording rules: `docs/THESAURUS.md` (Forbidden Lexicon), README "Reading the results", B-011.1 rounding.

## 4. Touch-points

**New**: `docs/design/claude-design-handoff.md`, `tests/unit/test_design_handoff.py` (hand-off tests), later
`viewer/` (page, `theme.css`), `docs/decisions/viewer.md`.

**Modified**: `scripts/build_design_sample.py` and `docs/design/sample/` (stretch variant).

## 5. Interfaces

The page consumes `window.SBRETIRE_RUNS = {schema_version, index: [...], runs: {name: results.json}}`
(`schemas/results.schema.json`). The theme is a stylesheet of custom properties, e.g. `--color-surface`,
`--color-text`, `--chart-series-1`; the final token list comes with the theme decision.

## 6. Plan of Work

1. Hand-off document + stretch sample (now).
2. User designs in Claude Design; theme chosen and recorded (`docs/decisions/viewer.md` §1, `viewer/theme.css`).
3. Build the page from the design; test it in a browser against the sample.

## 7. Validation

- **T1**: hand-off covers every schema section, every page part and the theme requirement; sample valid.
- **T2** (F-022.3): page opened from disk in the built-in browser shows the sample runs, compare mode works, no
  console errors, no network requests.

## 8. Decision Log

- 2026-10-09 — Hand-off moved here from F-021.3 at the user's request, with the common CSS theme requirement (#2).

## 9. Surprises

## 10. Tasks

### F-022.1 Claude Design hand-off document
- **Status**: Verification
- **Depends on**: F-021.3

`docs/design/claude-design-handoff.md` per §2 #1–#4; stretch sample variant in `scripts/build_design_sample.py`
and a regenerated `docs/design/sample/`.

**Acceptance criteria**
- [x] The hand-off names every `results.json` section and every page part (run picker, compare mode, headline, budget and reserve tables, required return, portfolio fan chart, survival curves, inputs, column notes), the wording rules, offline `file://` loading of `runs/runs.js`, light and dark, and points at the sample — `test_design_handoff_covers_schema_sections`
- [x] The hand-off requires one common `theme.css` of CSS custom properties with no hard-coded colours in page CSS, light and dark token sets, states that the theme is to be determined, and lists the token groups to propose — `test_design_handoff_requires_common_theme`
- [x] The sample's second run is `example-stretch` with failures and a reserve table, still example-only data — `test_design_sample_is_valid_example_data`

**Notes**
- 2026-10-09 `docs/design/claude-design-handoff.md`: purpose and readers, deliverables (index.html, theme.css, optional viewer.css/js; no build, server or network), data contract (window.SBRETIRE_RUNS from runs/runs.js; index fields; every results.json section), 11 page parts, wording/number rules, edge cases, §7 Common CSS theme (one theme.css of custom properties, no colour literals in page CSS, light/dark via prefers-color-scheme and data-theme, theme to be determined with token groups to propose), layout/accessibility, privacy, next steps. `scripts/build_design_sample.py`: second run now `example-stretch` (10,500/month, 4 %, 12-month reserve; 81.6 % success); sample regenerated. Tests in `tests/unit/test_design_handoff.py` (3 for this task); full gate 411 passed.

### F-022.2 Choose and record the common CSS theme
- **Status**: To Do
- **Depends on**: F-022.1

After Claude Design proposes a theme: record it in `docs/decisions/viewer.md` §1 and commit `viewer/theme.css`.
Criteria may be refined when the design is back.

**Acceptance criteria**
- [ ] `docs/decisions/viewer.md` §1 records the chosen theme and `viewer/theme.css` defines every token it names, for light and dark — `test_theme_css_defines_decided_tokens`

### F-022.3 Build the results viewer page
- **Status**: To Do
- **Depends on**: F-022.2

Build the page from the Claude Design output against the sample; decide its placement (§2 #5). Criteria may be
refined when the design is back.

**Acceptance criteria**
- [ ] The page's own CSS and markup use colours, fonts and spacing only through theme tokens (no colour literals outside `theme.css`) — `test_viewer_uses_only_theme_tokens`
- [ ] Opened from disk with the sample, the page lists both runs, shows every part, compares two runs, and logs no console errors or network requests — `check: built-in browser on the viewer with docs/design/sample/runs`

## 11. Open Questions

- The common theme (palette, typography, token names) — to be determined with Claude Design (F-022.2).
- Where the built page lives and how it reaches `output/runs/runs.js` (F-022.3).

## 12. Acceptance Criteria

1. Hand-off covers the schema and page — `test_design_handoff_covers_schema_sections`
2. Common theme requirement — `test_design_handoff_requires_common_theme`
3. Stretch sample — `test_design_sample_is_valid_example_data`
4. Theme decision, page build — added with the design (F-022.2, F-022.3)
