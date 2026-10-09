# SBRetire results viewer — Claude Design hand-off

**For:** Claude Design · **Feature:** F-022 (`docs/backlog/feature-html-results-viewer-design-brief.md`) ·
**Status:** ready to design · **Date:** 2026-10-09

## 1. What we are designing

SBRetire is a retirement-planning model for one UK household of two people. It simulates 100,000 possible futures
(each with its own lifetimes and inflation) and asks: *how much can we spend each month, rising with inflation, and
still not run out of money while either of us is alive?* Each model run is saved under a name, for example `base` or
`stress-3pct`.

Design **one static web page** that lets the household:

1. pick a run and understand its results at a glance, then in detail;
2. compare two runs side by side (for example a 5 % return against a 4 % one);
3. see exactly which inputs produced the numbers.

The readers are the two people whose plan it is: numerate but not statisticians. Calm and trustworthy, never
alarming or salesy. The page explains; it does not advise.

## 2. Deliverables

- `index.html`: the page.
- `theme.css`: the **common CSS theme** (section 7). Every colour, font, size, space, radius, shadow and chart
  colour lives here.
- Optionally `viewer.css` and `viewer.js` for page-specific layout and behaviour (using only theme tokens).
- A short note listing the theme tokens you defined, with light and dark values, and any layout decisions.

No build step, framework install, server or network. Plain HTML, CSS and JavaScript that work offline when the
file is double-clicked (`file://`). If a chart library is truly needed it must be a single file we can copy into the
repo; inline SVG drawn by our own script is preferred.

## 3. How the page gets its data

The page loads one script, **`runs/runs.js`**, relative to `index.html`, with a plain `<script>` tag. It sets:

```js
window.SBRETIRE_RUNS = {
  schema_version: "1.0",
  index: [ /* one summary per run, newest first */ ],
  runs: { "<name>": { /* the run's results.json */ } }
};
```

Use `fetch()` nowhere: browsers block it from `file://`. If `window.SBRETIRE_RUNS` is missing or has no runs, show a
friendly empty state ("No named runs yet. Run `sbretire run --config … --name <name>`.").

**Sample data to design against:** `docs/design/sample/runs/runs.js` (plus each run's `results.json` and
`index.json` in the same folder). It holds two runs of the illustrative example config, with no real people:

| Run | Budget | Return | Reserve | Conservative success |
|---|---|---|---|---|
| `example-base` | 6,667/month | 5 % | off | 100 % |
| `example-stretch` | 10,500/month | 4 % | 12 months | 81.6 % |

The full contract is `schemas/results.schema.json` (JSON Schema 2020-12).

### 3.1 `index` entries (the run picker)

`name`, `created_at` (ISO UTC), `config_file`, `paths`, `monthly_budget_today`, `annual_return`,
`conservative_success_rate`, `conservative_standard_error`, `first_target_probability`,
`first_target_maximum_monthly_budget_today`.

### 3.2 One run's `results.json`, section by section

| Section | What it holds | Use it for |
|---|---|---|
| `schema_version` | `"1.0"` | Refuse politely if it is not a version the page knows |
| `run` | name, created_at, sbretire_version, config_file, config_sha256, seed `{value (string), source}`, as_of_date, horizon_years, last_month, paths, monthly_budget_today, annual_return, options `{end_reserve_months, spend_at_least_income}` | Header, run picker, badges for the options |
| `people` | two `{id, name}`; `people[0]` is "person 1" in the annual columns | Legend labels on survival charts |
| `inputs` | every setting: `{section, item, label, value, unit}` | Inputs panel, grouped by `section` |
| `summary` | n_paths, n_successful, n_failed, n_unresolved, n_completed, conservative_success_rate, conservative_standard_error, completed_success_rate (nullable), completed_standard_error (nullable), unresolved_share | Headline |
| `reserve_summary` | same fields under the end-of-life reserve test; `null` when the reserve is off | Headline (second figure) |
| `budgets` | one row per target (e.g. 90/95/99 %): target_probability, maximum_monthly_budget_today (nullable), maximum_annual_budget_today, estimated_success_probability, standard_error, unresolved_fraction, budget_tolerance, converged, iterations, note | Maximum sustainable budget table/chart |
| `reserve_budgets` | the same rows for leaving the reserve; empty when off | Reserve table/chart |
| `returns` | one row per target: target_probability, monthly_budget_today, required_annual_return (nullable), success_probability_at_required_return, standard_error_at_required_return, unresolved_fraction_at_required_return, return_tolerance, converged, iterations, note | Required return table, compared with `run.annual_return` |
| `annual` | one row per calendar year (first and last can be partial; `months`): survival probabilities, budget and income medians, portfolio percentiles p05/p25/median/p75/p95, probability_not_depleted_yet, estimated_lifetime_success_rate, completed/unresolved counts | Charts over time and the year table |
| `columns` | `{file: {column: {unit, meaning}}}` for every CSV column | Tooltips / "what does this mean?" notes |

Money is GBP. Fields ending `_today` are in today's money; `annual` money fields are nominal (future pounds).
Probabilities are shares from 0 to 1. `null` means "not applicable" (for example an infeasible target); show a dash
plus the row's `note`, never `0`.

## 4. Page parts

1. **Header and run picker.** Choose a run from `index` (name, date, budget, return, success rate). Show the run's
   as-of date, horizon, number of simulated futures and option badges ("12-month reserve", "spends at least
   income").
2. **Compare mode.** Pick a second run; the page shows both side by side (or overlaid in charts) and highlights the
   differences in budget, return and options. With one run, compare is simply unavailable.
3. **Headline.** At your budget: the **conservative success rate** (successful ÷ all futures) with its ± standard
   error, the successful / failed / unresolved counts, and the completed-path rate as secondary context. If a
   reserve is set, the success rate leaving the reserve beside it.
4. **Maximum sustainable budget.** For each target (90/95/99 %): the most they can spend per month and per year in
   today's money, the success rate at that budget, and convergence. A bar or dot chart against their current
   budget works well.
5. **Leaving an end-of-life reserve** (only when `reserve_budgets` is not empty): the same table for "and still
   leave N months of budget at the second death", next to part 4 so the cost of the reserve is visible.
6. **Required return.** For each target, the lowest fixed annual return that still meets it at their budget,
   compared with the return they assumed (`run.annual_return`): the gap is their margin.
7. **Portfolio over time: fan chart.** Year on the x-axis; bands p05–p95 and p25–p75 with the median line, in
   nominal pounds. Do not convert them to today's money: the data does not support it.
8. **Survival and money lasting.** Lines per year for person 1 alive, person 2 alive, both alive (names from
   `people`) and `probability_not_depleted_yet`.
9. **Year-by-year table.** The `annual` rows (collapsible; long horizons have up to ~100 rows).
10. **Inputs.** Every input grouped by section, with units: what produced these numbers.
11. **Column notes.** Every figure's meaning available from `columns` (tooltip, info icon or glossary), so no
    number is unexplained.

Suggested order: header, headline, budgets (+ reserve), required return, charts, year table, inputs. Mobile: one
column in the same order.

## 5. Wording and number rules

- "Success" means the money paid every month's spending until **both** people had died. **Unresolved** futures
  (someone still alive at the end of the horizon) never count as successes.
- A "95 % target" means "95 % of simulated futures succeed". The `±` figure is one Monte Carlo standard error
  (simulation noise only). It is **not a confidence interval**; say so in a note near the headline.
- Say "simulated futures" or "paths", "maximum sustainable budget", "required return". Do **not** use: "safe
  withdrawal rate", "probability funded", "guarantee", "retirement income" (say "household income"), or any
  advice wording ("you should …").
- Budgets are already rounded **down** and required returns **up** (so a shown number always meets its target):
  display budgets as whole pounds with separators (`£8,911`), never rounded up; returns to 2 dp (`4.66%`), never
  rounded down; rates 2 dp (`99.98%`); standard errors 3 dp (`±0.004%`).
- Every result is pre-tax, with a fixed return (no market crashes). Keep a short, always-visible "About these
  numbers" note with the main assumptions and limitations; it is not financial advice.

## 6. Edge cases to design for

- A target with `maximum_monthly_budget_today: null` (infeasible) or `required_annual_return: null` (no solution
  within −50 % … +50 %): dash plus the `note`.
- `completed_success_rate: null` (no future completed within the horizon).
- `converged: false` (search reached its cap or lower bound): mark the row.
- Reserve off: hide part 5 and the reserve headline entirely.
- 100 % success with ± 0.000 %: still meaningful; avoid a broken-looking chart.
- Compared runs with different targets or horizons: align by target value and by year, leaving gaps.
- Long run names (up to 64 characters), up to dozens of runs in the picker.

## 7. Common CSS theme

**Requirement:** the viewer is the first of several SBRetire pages (for example a future HTML results guide).
Every SBRetire page will share **one common CSS theme**, so that pages look like one product and a change of
colour or font is made in one place.

- The theme is a single stylesheet, **`theme.css`**, made only of **CSS custom properties** (design tokens) on
  `:root`, plus nothing page-specific.
- Page CSS (`viewer.css` or `<style>`) uses **only** `var(--…)` for colours, fonts, sizes, spacing, radii, shadows
  and chart colours: **no hard-coded colour** values (no hex, `rgb()`, `hsl()` or named colours) outside
  `theme.css`.
- **Light and dark:** both token sets live in `theme.css`. Dark follows the system setting
  (`@media (prefers-color-scheme: dark)`) and can be forced with `:root[data-theme="dark"]` (and light with
  `data-theme="light"`), so a toggle can be added.
- **The theme itself is to be determined.** Please propose it: palette, typography, spacing and so on, with your
  reasoning. We will record the chosen theme as a decision (`docs/decisions/viewer.md` §1) before the page is
  built. If you see two strong directions, show both.
- Token groups to propose (names are suggestions; propose better ones if you like):
  - **colour:** page background, surfaces and raised surfaces, borders, primary text, muted text, accent, focus
    ring, and status colours for success, warning and failure (used for success rates and infeasible rows);
  - **chart:** series colours for at least two runs in compare mode, plus person 1, person 2 and "both", and fan
    band colours (outer p05–p95, inner p25–p75, median line), gridlines and axis text;
  - **typography:** font families (system fonts or fonts we can store locally; no web-font downloads), sizes for
    headline figure, headings, body, table and small print, weights, line heights, tabular numerals for figures;
  - **spacing:** a spacing scale;
  - **radius** and **shadow** scales;
  - **motion:** durations (respecting `prefers-reduced-motion`).
- Contrast: text and essential chart marks meet WCAG AA in both light and dark.

## 8. Layout and accessibility

- Works from 360 px phones to wide desktops; no horizontal page scroll (tables may scroll inside their own box).
- Keyboard-usable picker and toggles, visible focus, semantic headings and tables, charts with a text alternative
  (a caption or the matching table).
- Colour is never the only signal (pair with labels, patterns or icons).
- Printing a run gives a clean light-mode page.

## 9. Privacy

Real runs contain the household's names, dates of birth and amounts. Design only with the sample above. The page
must never send data anywhere: no analytics, no external fonts, scripts or images.

## 10. What happens next

1. You return the page, `theme.css` and the note on tokens.
2. We choose the theme and record it (F-022.2).
3. We build the page into the repo, test it against the sample in a browser, and point it at real runs (F-022.3).
