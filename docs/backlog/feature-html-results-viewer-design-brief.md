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
| 4 | Sample | `docs/design/sample/runs/` from the example config only: `example-base` and `example-stretch` (10,500/month, 4 % return, 12-month reserve, so failures and a reserve table appear) | Informative charts; no personal data | F-021 §2 #8 |
| 5 | Placement of the built page | Source in the package: `src/sbretire/web/theme.css` (common theme, shared by future pages) and `src/sbretire/web/viewer/` (`index.html`, `viewer.css`, `viewer.js`). Every named run copies all four next to `runs/` in `<output-dir>`, so the household opens `<output-dir>/index.html` | Works with any `--output-dir`, from `file://`; the copy always matches the installed version | user decision 2026-10-09 |
| 6 | Theme | Direction **A · Paper** from Claude Design: warm off-white, ink text, deep green accent, serif headings and figures, system sans body, oklch tokens, light + dark; recorded in `docs/decisions/viewer.md` §1. Direction B and the footer design-review switch are dropped | User chose A after reviewing both in the browser | user decision 2026-10-09 |
| 7 | Hardening of the design prototype | Remove the design-review control and direction-B code; read the budget search tolerance from `budget_tolerance` instead of a hard-coded "£1"; keep the design's notes in `docs/design/` | Design README "Work remaining" | Claude Design hand-back |

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

- 2026-10-09 — Claude Design returned a working prototype (`index.html`, `viewer.css`, `viewer.js`) and two theme
  directions with the same token names; the user picked A · Paper after viewing both in the built-in browser.

## 10. Tasks

### F-022.1 Claude Design hand-off document
- **Status**: Done
- **Depends on**: F-021.3

`docs/design/claude-design-handoff.md` per §2 #1–#4; stretch sample variant in `scripts/build_design_sample.py`
and a regenerated `docs/design/sample/`.

**Acceptance criteria**
- [x] The hand-off names every `results.json` section and every page part (run picker, compare mode, headline, budget and reserve tables, required return, portfolio fan chart, survival curves, inputs, column notes), the wording rules, offline `file://` loading of `runs/runs.js`, light and dark, and points at the sample — `test_design_handoff_covers_schema_sections`
- [x] The hand-off requires one common `theme.css` of CSS custom properties with no hard-coded colours in page CSS, light and dark token sets, states that the theme is to be determined, and lists the token groups to propose — `test_design_handoff_requires_common_theme`
- [x] The sample's second run is `example-stretch` with failures and a reserve table, still example-only data — `test_design_sample_is_valid_example_data`

**Notes**
- 2026-10-09 `docs/design/claude-design-handoff.md`: purpose and readers, deliverables (index.html, theme.css, optional viewer.css/js; no build, server or network), data contract (window.SBRETIRE_RUNS from runs/runs.js; index fields; every results.json section), 11 page parts, wording/number rules, edge cases, §7 Common CSS theme (one theme.css of custom properties, no colour literals in page CSS, light/dark via prefers-color-scheme and data-theme, theme to be determined with token groups to propose), layout/accessibility, privacy, next steps. `scripts/build_design_sample.py`: second run now `example-stretch` (10,500/month, 4 %, 12-month reserve; 81.6 % success); sample regenerated. Tests in `tests/unit/test_design_handoff.py` (3 for this task); full gate 411 passed.
- 2026-10-09 /verify PASS:
  - 4 hand-off tests pass and can fail; full suite 411
  - every field the hand-off lists exists in the schema and the sample, none invented; sample table figures, return bounds, wording and rounding rules all match the code and THESAURUS
  - common CSS theme section meets the user's request (one theme.css, custom properties only, light/dark, to be determined, token groups, WCAG AA)
  - minor points then fixed in the hand-off: other nulls (incl. annual rows without a note) and negative required returns; brief §2 #4 figure corrected to 10,500

### F-022.2 Choose and record the common CSS theme
- **Status**: In Progress
- **Depends on**: F-022.1

After Claude Design proposes a theme: record it in `docs/decisions/viewer.md` §1 and commit `viewer/theme.css`.
Criteria may be refined when the design is back.

**Acceptance criteria**
- [ ] `docs/decisions/viewer.md` §1 records the chosen theme and `src/sbretire/web/theme.css` defines every token it names, with a dark value for every colour and chart token in both the `prefers-color-scheme` block and `[data-theme="dark"]` — `test_theme_css_defines_decided_tokens`
- [ ] Text tokens meet WCAG AA in light and dark: body and muted text on background, surface and sunken surface ≥ 4.5:1; status colours, chart run colours and the accent on background ≥ 3:1 — `test_theme_contrast_meets_aa`

### F-022.3 Build the results viewer page
- **Status**: In Progress
- **Depends on**: F-022.2

Build the page from the Claude Design output against the sample; decide its placement (§2 #5). Criteria may be
refined when the design is back.

**Acceptance criteria**
- [ ] The page's own CSS, markup and script use colours only through theme tokens (no hex, rgb, hsl, oklch or named colour literals outside `theme.css`), make no network requests (`fetch`, `XMLHttpRequest`, external URLs) and contain no design-review switch or second theme — `test_viewer_uses_only_theme_tokens`
- [ ] The budget tables' convergence note uses `budget_tolerance` from the data, not a hard-coded amount — `test_viewer_reads_budget_tolerance`
- [ ] A named run copies `index.html`, `theme.css`, `viewer.css` and `viewer.js` into `<output-dir>/` byte-equal to the package files; an unnamed run does not — `test_cli_named_run_copies_viewer`
- [ ] Served with the sample runs, the page lists both runs, shows every section, compares two runs, switches light/dark, and logs no console errors or network requests to other hosts — `check: built-in browser on the viewer with docs/design/sample/runs`

## 11. Open Questions

- None (theme and placement decided 2026-10-09, §2 #5–#6).

## 12. Acceptance Criteria

1. Hand-off covers the schema and page — `test_design_handoff_covers_schema_sections`
2. Common theme requirement — `test_design_handoff_requires_common_theme`
3. Stretch sample — `test_design_sample_is_valid_example_data`
4. Theme decision, page build — added with the design (F-022.2, F-022.3)
