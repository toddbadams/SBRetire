---
id: F-023
type: feature
parent: results-viewer
status: planned
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-023 Print and PDF

## 1. Purpose

A **Save as PDF** button on the results viewer that produces a black-and-white A4 document in which cards and table
rows never split across pages. Requested by the user on 2026-10-09; the plan follows the investigation of the same
day, in which the viewer was printed to PDF with headless Edge before and after experimental print rules.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Mechanism | The button calls `window.print()`; the user picks "Save as PDF" in the browser dialog. No PDF library | Offline, no dependency, vector text; JS PDF libraries rasterise; a page cannot choose the destination itself | investigation 2026-10-09 |
| 2 | File name | Before printing, `document.title` becomes `SBRetire <run> [vs <run>] <created date>` (the browser's default PDF file name); restored after printing | Sensible default name without a library | investigation |
| 3 | Black and white | Every print is black and white: a print-only token set in `theme.css` (`@media print`) gives every colour and chart token a neutral grey (oklch chroma 0); page CSS stays token-only. Charts stay distinguishable by the design's dash patterns, hatching and circle/square markers. No `filter: grayscale()` (rasterises in Chromium) | User asked for black and white; the theme stays the one source of colour | viewer §1 |
| 4 | Page | A4 portrait, 14 mm / 12 mm margins; header (run names) and footer (page X of Y) from `@page` margin boxes | UK paper; navigable PDF | investigation |
| 5 | Keep together | Cards, charts, table rows: `break-inside: avoid`. On `beforeprint`, each section's heading and intro are wrapped with its first card in one unbreakable block (restored on `afterprint`) — `break-after: avoid` alone did not hold in Edge | Headings never stranded at a page foot | investigation |
| 6 | Screen-only items | Hidden in print: theme and PDF buttons, pickers' "Compare with: No comparison", (i) buttons, hover/keyboard help, tabs, fold toggles. Folded sections (year table, glossary) print expanded | Clean document | investigation |
| 7 | Year table | Print shows two portrait tables for the run in the year table: (a) year, months, survival, budget, spending, income, net withdrawal; (b) year, portfolio p05–p95, money not run out yet, lifetime success estimate, completed, unresolved. The 19-column screen table is hidden in print | 19 columns do not fit even landscape A4 | investigation |
| 8 | Review tool | `scripts/render_viewer_pdf.py` prints the viewer for the example sample (single run and compare) to PDF with headless Edge/Chrome for review; an optional slow test uses it to check A4 pages when a browser is present | Repeatable visual check without personal data | investigation |

## 3. Context

- `src/sbretire/web/viewer/` (F-022): `index.html`, `viewer.css` (an `@media print` block already hides controls and
  avoids breaks inside cards), `viewer.js` (opens the year table on `beforeprint`); `src/sbretire/web/theme.css`.
- Tests in `tests/unit/test_viewer.py` forbid colour literals outside `theme.css` and network calls.

## 4. Touch-points

**Modified**: `src/sbretire/web/theme.css`, `src/sbretire/web/viewer/{index.html,viewer.css,viewer.js}`,
`tests/unit/test_viewer.py`, `README.md`, `CHANGELOG.md`, `docs/decisions/viewer.md` (§3).

**New**: `scripts/render_viewer_pdf.py`, `tests/unit/test_viewer_pdf.py` (slow, skipped without Edge/Chrome).

## 5. Interfaces

- `theme.css`: `@media print { :root, :root[data-theme] { --color-…: oklch(L 0 0); --chart-…: … } }`.
- `viewer.css`: `@page { size: A4; margin: 14mm 12mm; @top-left …; @bottom-right … }`; `.print-only`,
  `.screen-only`, `.print-keep`.
- `viewer.js`: `#pdf-button` click → `printPdf()`; `beforeprint` / `afterprint` handlers.
- `scripts/render_viewer_pdf.py [--out DIR]` → `viewer-single.pdf`, `viewer-compare.pdf`.

## 6. Plan of Work

1. Print tokens in the theme.
2. Print layout (A4, header/footer, keep-together, hidden UI, expanded folds, two year tables).
3. Save as PDF button and file name.
4. PDF review script and slow page check; docs.

## 7. Validation

- **T1**: token tests (every colour/chart token neutral in print, AA contrast in print), static checks on CSS/JS.
- **T2**: headless-Edge PDFs of the sample: A4 portrait pages, page count, visual review (single + compare).

## 8. Decision Log

- 2026-10-09 — §2 #1–#8 from the investigation; the user asked to brief and implement the proposed plan.

## 9. Surprises

## 10. Tasks

### F-023.1 Black-and-white print tokens
- **Status**: To Do
- **Depends on**: —

`theme.css` `@media print` token set (§2 #3).

**Acceptance criteria**
- [ ] Every `--color-*` and `--chart-*` token of the light theme is redefined in the print block with chroma 0 (alpha allowed), for both `:root` and `:root[data-theme]` — `test_print_tokens_are_neutral`
- [ ] In the print tokens, text on every background is at least 4.5:1 and every mark on the background at least 3:1 — `test_print_contrast_meets_aa`

### F-023.2 Print layout
- **Status**: To Do
- **Depends on**: F-023.1

`viewer.css` print rules, `beforeprint`/`afterprint` keep-together wrapping, print-only year tables (§2 #4–#7).

**Acceptance criteria**
- [ ] The print CSS sets A4 portrait with margins and header/footer margin boxes, keeps cards, charts, rows and `.print-keep` blocks unbroken, hides the screen-only items and shows `.print-only` content only in print — `test_print_css_layout_rules`
- [ ] `beforeprint` opens every fold and wraps each section's heading, intro and first card in `.print-keep`; `afterprint` restores the DOM — `test_print_keep_together_script`
- [ ] The year table renders two print-only tables whose columns together cover every annual column exactly once (plus the year in both) — `test_print_year_tables_cover_all_columns`

### F-023.3 Save as PDF button
- **Status**: To Do
- **Depends on**: F-023.2

`#pdf-button` in the masthead; `printPdf()` sets the title and calls `window.print()`, restoring the title after
(§2 #1–#2).

**Acceptance criteria**
- [ ] The masthead has a "Save as PDF" button that is hidden in print; its handler sets `document.title` from the run names and created date, calls `window.print()`, and restores the title on `afterprint` — `test_pdf_button_sets_title_and_prints`

### F-023.4 PDF review script and docs
- **Status**: To Do
- **Depends on**: F-023.3

`scripts/render_viewer_pdf.py`, slow test, README, CHANGELOG, decision viewer §3.

**Acceptance criteria**
- [ ] With Edge or Chrome present, the sample renders to single and compare PDFs whose every page is A4 portrait — `test_viewer_pdf_pages_are_a4`
- [ ] Reviewed PDFs (single and compare) are black and white, have no heading stranded at a page foot, no card or table row split, the year tables complete, and header/footer present — `check: scripts/render_viewer_pdf.py and visual review`
- [ ] README documents Save as PDF; viewer §3 records the decisions — `check: grep -n "Save as PDF" README.md docs/decisions/viewer.md`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Neutral print tokens — `test_print_tokens_are_neutral`
2. Print contrast — `test_print_contrast_meets_aa`
3. Layout rules — `test_print_css_layout_rules`
4. Keep together — `test_print_keep_together_script`
5. Year tables — `test_print_year_tables_cover_all_columns`
6. Button — `test_pdf_button_sets_title_and_prints`
7. A4 pages — `test_viewer_pdf_pages_are_a4`
8. Visual review — `check: scripts/render_viewer_pdf.py`
9. Docs — `check: grep -n "Save as PDF" README.md docs/decisions/viewer.md`
