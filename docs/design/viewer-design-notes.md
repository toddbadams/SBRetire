> Viewer design notes as returned by Claude Design on 2026-10-09 (kept for reference). Decision: direction **A · Paper** was
> chosen (`docs/decisions/viewer.md` §1); direction B, the review switch and `theme-instrument.css` were dropped.

# Handoff: SBRetire HTML results viewer (F-022)

## Overview
A single static page that lets the household pick a saved SBRetire run, read its results at a glance and in
detail, compare two runs side by side, and see exactly which inputs produced the numbers. Built against the brief
`docs/design/claude-design-handoff.md` and the sample `docs/design/sample/runs/runs.js`.

## About the design files
The files in this folder are **design references built in HTML/CSS/JS**: a working prototype of the intended look and
behaviour. Because the brief targets exactly this stack (plain HTML + CSS + JS, no build step, opens from
`file://`), the prototype is written to be close to drop-in. Treat it as the reference implementation: move it into
the repo, then review, harden and test it to the repo's standards (see "Work remaining") rather than shipping it
unread.

## Fidelity
**High-fidelity.** Final layout, copy, number formatting, colours (as tokens), typography and interactions.
Two theme directions are supplied; one must be chosen (F-022.2) and recorded in `docs/decisions/viewer.md` §1.

## Files
| File | Role |
|---|---|
| `index.html` | Page shell: masthead, section skeleton with static headings/intros, "About these numbers", footer. Loads `theme.css`, `viewer.css`, `runs/runs.js`, `viewer.js`. |
| `theme.css` | **Common SBRetire theme**, Direction A "Paper". Only CSS custom properties on `:root`; light + dark. |
| `theme-instrument.css` | Direction B "Instrument". Same token names; drop-in replacement. |
| `viewer.css` | Page layout and components. Uses only `var(--…)`; no literal colours. |
| `viewer.js` | All rendering: pickers, sections, SVG charts, tooltips, theme toggle. IIFE, ES5-style, no dependencies. |
| `THEME-NOTES.md` | Token list with light/dark values and layout decisions (the "note on tokens" deliverable). |
| `runs/runs.js` | Copy of the sample data (two illustrative runs). Not for the repo; real file is generated. |

Suggested repo placement: `viewer/index.html`, `viewer/viewer.css`, `viewer/viewer.js`, and `theme.css` somewhere
shared by future SBRetire pages (e.g. `viewer/theme.css` or `web/theme.css`; adjust the `<link>`). The page expects
`runs/runs.js` **relative to `index.html`**.

## Data contract (as consumed)
- `window.SBRETIRE_RUNS = { schema_version, index: [...], runs: { name: results.json } }`. No `fetch()` anywhere.
- Picker lists `index` entries **that also exist in `runs`**, in `index` order (newest first).
- Schema check: a run whose `schema_version` major ≠ `1` shows a polite "newer results format" card and nothing else.
- Empty/missing data: "No named runs yet" card with `sbretire run --config … --name <name>`.
- Inputs are read from `inputs[]` by `item` key (e.g. `portfolio.starting_balance`, `people[<id>].<field>`,
  `income[<id>].<field>`, `mortality.source`, `inflation.source|source_period|log_mean`).
- Column notes come from `columns[file][column] = {unit, meaning}`; files used: `lifestyle_results.csv`,
  `lifestyle_reserve_results.csv`, `sustainability_results.csv`, `annual_results.csv`, `inputs.csv`.

## Number and wording rules (implemented in `F` in viewer.js)
| What | Rule | Example |
|---|---|---|
| Budgets / money | floor to whole £, en-GB separators, true minus for negatives | `£10,172`, `−£78,536` |
| Required return | **ceil** to 2 dp, always signed | `+4.59%`, `−6.53%` |
| Assumed return | exact to 2 dp | `4.00%` |
| Success rates / probabilities | **floor** to 2 dp (never overstate) | `81.62%`, `100.00%` |
| Standard error | `±` + 3 dp | `±0.122%` |
| Targets | trimmed | `90%`, `99.5%` |
| Input percentages (share / rate units) | ×100, up to 2 dp, trailing zeros trimmed | `4%`, `70%`, `3.4%` |
| Long-run inflation | `exp(log_mean) − 1`, as above | `2.81% a year` |
| Dates | `1 Oct 2026`; months `Sept 2126`; created_at shown in UTC | |
| `null` | em dash `—` plus the row's `note` if any; in `annual` a tooltip "No simulated future still running this year" | |
Banned wording per brief §5 (“safe withdrawal rate”, “guarantee”, “retirement income”, advice phrasing) is not used;
keep it that way when editing copy.

## Screens / views
One page, one column on narrow screens; `--layout-max` (74rem A / 76rem B) centred with `--layout-gutter`.

### 1. Masthead
- Bar: wordmark “SBRetire” (`--font-display`, `--text-h1`, semibold) + “RESULTS” (small caps style, `--tracking-caps`,
  muted); right: theme toggle pill “Theme: Auto|Light|Dark” (cycles, stored in `localStorage['sbretire-theme']`;
  sets `html[data-theme]`).
- Pickers grid: 1 col; ≥760px `1.25fr 1fr`. “Run” (circle marker) and “Compare with” (square marker; only when ≥2 runs).
  Each is a `<details>` disclosure: button shows run name (semibold, ellipsis) + meta line
  “9 Oct 2026 · £10,500/mo · 4.00% return · 81.62% success”. Panel: radio rows (name + same meta), filter box when
  >6 runs, max-height 20rem scroll. Compare list has “No comparison” and disables the run chosen in A.
  Keyboard: arrows move/preview, Enter closes, Escape closes and returns focus; outside click closes.
- Run meta chips: As of · Horizon N years, to Mon YYYY · N simulated futures · £/month budget · assumed return;
  option chips (accent outline) “12-month reserve”, “Spends at least income”. Provenance line: created (UTC),
  config file, seed (source), SBRetire version, first 10 chars of config sha (full in `title`).
- Sticky section nav (Success rate, Budget, Return, Portfolio, Survival, Year by year, Inputs, Glossary), horizontal
  scroll on narrow screens.
- Selection persists in URL hash `#run=<a>&compare=<b>`.

### 2. Compare differences (compare mode only)
Table Setting | run A | run B, listing only settings that differ (monthly budget, assumed return, reserve,
spend-at-least-income, starting balance, as-of date, horizon, paths, targets). Below: “Same in both: …” and
“N of the run inputs differ in total” linking to Inputs.

### 3. Headline — “Success rate at the current budget”
Card per run (two columns ≥900px in compare). Contents:
- Eyebrow “Success rate at £X/month” + (i); figure `--text-figure` in `--font-figures`; “±SE simulation noise”.
- Status pill vs the run's own targets: ✓ “Meets every target (…)”, ✓ “Meets the 90% target, not 95%”,
  ! “Below the 90% target” (warning). Glyph + text, never colour alone.
- If reserve on: second figure (`--text-figure-sm`) “…and leaving a 12-month reserve at the second death”.
- Counts bar (12px pill, 2px gaps): successful = solid success; failed = diagonal hatch failure/failure-soft;
  unresolved = vertical stripe. Legend with counts. `role="img"` with full text label.
- Secondary line: completed-path rate ± SE, or “No simulated future completed within the horizon…”; when all succeed:
  “All N simulated futures succeeded, so the simulation noise is zero.”
- Note under cards: ± is one Monte Carlo standard error, not a confidence interval.

### 4. About these numbers (always visible)
Sunken panel, 1/2/3 columns at <760 / ≥760 / ≥1100px. Six points: pre-tax; one fixed return (no crashes); what
varies (lifetimes, inflation; path count filled from data); today's vs nominal money; unresolved ≠ success;
model, not financial advice.

### 5. Maximum sustainable budget (+ reserve)
- Chart card: dot chart, one row per target (union across runs), one lane per run. Filled marker = max budget;
  hollow marker = with reserve, joined by a 2px line (the reserve's cost); dashed vertical = current budget with label
  “Budget £10,500” above. Value labels beside markers. Infeasible rows print “— <note>”.
- Below, `.grid-2` (2 cols ≥900px): “Maximum sustainable budget” table and, only when any run has a reserve,
  “Leaving an end-of-life reserve”. Columns: Target | (Run) | Per month (big) with “£X a year” beneath | Success with
  ±SE beneath | (reserve only) Cost “£252 / a month” = floor(no-reserve) − floor(reserve). No Search column: a footer
  note “✓ Every search converged to within £1 a month.” or, if any `converged:false`, a “! Not converged” tag in that
  row's Per month cell. **Tables must not need horizontal scroll at the 2-column width.**
  (Note: “£1” is hard-coded; ideally read `budget_tolerance`.)

### 6. Required return
Dot chart: required return per target (filled marker), assumed return as dashed vertical, bar between them —
solid success = margin, dashed warning = shortfall; zero line when the domain crosses 0. Table: Target | (Run) |
Required | Assumed | Margin tag (“✓ +10.53 pts” / “! 0.59 pts short”) | Success at required ± SE | Search.
Note on negative returns shown only when any are negative.

### 7. Portfolio over time (fan)
Segmented toggle “Main span | All years” (shared with survival). Main span = rows until the last year where
`unresolved_paths / n_paths ≥ 0.001`, plus one. Bands p05–p95 (`--chart-fan-outer`) and p25–p75
(`--chart-fan-inner`), median line 2.25px. Compare: run B drawn as dashed p05/p95 outlines, dotted p25/p75, dashed
median in `--chart-run-b`. Y axis nominal £ (`£1.5m`), never converted to today's money. Hover or focus + arrow keys
shows a tooltip per year; nulls break the paths.

### 8. Survival and money lasting
Lines: person 1 alive (dash 7 4, `--chart-person-1`), person 2 alive (dash 2 3.5, `--chart-person-2`), both alive
(solid 1.5px, `--chart-both`), money not run out yet (3.25px, run colour; run B dashed). Names from `people`. In
compare, survival lines come from run A (they depend only on the people). Same hover/keyboard behaviour.

### 9. Year by year
Collapsed `<details>` “Show the table · N rows · 2026–2092”. Compare: tabs to choose the run. Scroll box max-height
34rem, sticky header row and sticky Year column. 18 columns from `annual`; every header has an (i) from
`columns['annual_results.csv']`. Null cells show `—` with the tooltip text. `beforeprint` opens it.

### 10. Inputs
Cards per input section (2 columns ≥1000px for a single run; 1 column in compare). Generic sections: table
Setting | Value (unit merged into the value; no Unit column, no config item names). Compare: Setting | A | B, rows
that differ get warning-soft background + “Differs” tag. Special condensed cards:
- **People**: Name | Born (Mon YYYY) | Sex (mortality table) | Budget as survivor (“70% of budget” / “Household
  default”). Note: only year and month of birth are used.
- **Mortality**: one row “Source” with a friendly name (`ONS_2024_BASED` → “ONS 2024-based mortality
  projections”; pattern `ONS_<yyyy>_BASED` handled generically).
- **Inflation**: Source (“UK Consumer Prices Index (CPI)”), Years included (“1989–2025”), Long-run average
  (“2.81% a year”). Note about each future drawing its own path.
- **Household income**: Income | Paid to (person name or Household) | From | Until (“No end”) | Per year |
  Rises with inflation | After recipient's death (%). Note: today's money; Until = first month no longer paid.

### 11. Glossary — “What each figure means”
Collapsed `<details>` listing every `columns` entry by file: monospace column name, meaning, unit.

### Footer
Privacy line, and a dashed **design-review-only** control switching theme direction A/B
(`localStorage['sbretire-review-direction']`). **Remove once a theme is chosen.**

## Interactions & behaviour summary
- (i) buttons: one floating fixed-position tooltip (`#tip`) on hover/focus; Escape or scroll hides it.
- Charts are SVG strings rebuilt at container width on load and on window resize (debounced 120ms).
- All focusable elements get `outline: var(--focus-width) solid var(--color-focus)`.
- Motion: only short colour/rotate transitions using `--duration-*`; zeroed under `prefers-reduced-motion`.
- Print: light tokens always (dark blocks are `@media screen`), controls hidden, scroll boxes expanded.

## State
`{ a: runName, b: runName|null, allYears: bool, tableRun: 'a'|'b' }` plus theme preference in localStorage.
`render()` redraws every section; pickers are built once and synced (so keyboard focus survives).

## Design tokens
All values are in `theme.css` / `theme-instrument.css` and summarised in `THEME-NOTES.md`. Groups: colour
(bg, surface, raised, sunken, border, border-strong, text, text-muted, accent, accent-soft, on-accent, focus,
tooltip, success/warning/failure + soft), chart (run-a, run-b, person-1, person-2, both, fan-outer, fan-inner,
fan-median, grid, axis, axis-text, zero, hover), type (display/body/figures/mono families, `--numeric`,
figure → small sizes, weights, leadings, caps tracking), spacing `--space-0…9` (0–96px, 4px base), radius
sm/md/lg/pill, shadow sm/md/lg, layout max/gutter, motion durations + easing. Colours are written in `oklch()`.
Fonts are system stacks only (no downloads).

## Assets
None. No images, icon fonts or external scripts; glyphs used are text characters (✓, !, —, ±, −).

## Work remaining
1. Choose theme direction; delete the other file and the footer review control.
2. Place files in the repo; wire `runs/runs.js` generation path (the CLI already writes it per F-022).
3. Browser-test against the sample and real runs: 360px phone, wide desktop, dark mode, print, keyboard-only.
4. Contrast audit of both themes (AA for text and essential chart marks).
5. Optional: read `budget_tolerance` instead of the hard-coded “£1”; add a lint/check that `viewer.css`/`viewer.js`
   contain no literal colours.
