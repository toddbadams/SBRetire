> Theme tokens as returned by Claude Design on 2026-10-09 (kept for reference). Decision: direction **A · Paper** was
> chosen (`docs/decisions/viewer.md` §1); direction B, the review switch and `theme-instrument.css` were dropped.

# SBRetire viewer — theme tokens and layout notes

Files: `index.html`, `theme.css` (Direction A, Paper), `theme-instrument.css` (Direction B, same token names),
`viewer.css`, `viewer.js`, `runs/runs.js` (sample). Opens from `file://`; no fetch, no network, no fonts downloaded.
`viewer.css`/`viewer.js` use only `var(--…)`; every colour lives in the theme file.

## Two directions
- **A · Paper** — warm off-white, ink text, one deep green accent; serif (Iowan/Charter/Georgia) for headings and
  the big figures, system sans for body. Reads like a printed statement: calm, a little personal, prints well.
- **B · Instrument** — cool neutral greys, blue accent, system sans throughout, tighter radii, flatter shadows.
  Reads like a measuring tool: neutral, denser.
Switch them with the dashed "Design review" control in the footer (remove before shipping).
Light/dark: dark follows the system on screen; `:root[data-theme="dark"|"light"]` forces; print always gets light
(dark blocks are inside `@media screen`). Reduced motion zeroes the durations.

## Tokens (A light → A dark)
Colour
- `--color-bg` oklch(.972 .008 85) → oklch(.20 .008 75)
- `--color-surface` .99 → .235 · `--color-surface-raised` .998 → .27 · `--color-surface-sunken` .948 → .18
- `--color-border` .875 → .34 · `--color-border-strong` .74 → .48
- `--color-text` oklch(.24 .015 70) → oklch(.93 .01 85) · `--color-text-muted` .46 → .74 (≥ 6:1 on bg both modes)
- `--color-accent` oklch(.44 .08 165) → oklch(.78 .09 165) · `--color-accent-soft` · `--color-on-accent`
- `--color-focus` oklch(.52 .16 255) → oklch(.75 .13 255)
- `--color-success|warning|failure` (+ `-soft` backgrounds): green 155 / amber 65 / brick 30, L .46–.50 light, .75–.80 dark
- `--color-tooltip-bg`, `--color-tooltip-text` (inverted)

Chart
- `--chart-run-a` (green, = accent family) · `--chart-run-b` (terracotta 45)
- `--chart-person-1` (blue 255) · `--chart-person-2` (plum 330) · `--chart-both` (ink)
- `--chart-fan-outer` (accent @ 18 %) · `--chart-fan-inner` (accent @ 32 %) · `--chart-fan-median`
- `--chart-grid`, `--chart-axis`, `--chart-axis-text`, `--chart-zero`, `--chart-hover`

Type: `--font-display`, `--font-body`, `--font-figures`, `--font-mono`, `--numeric` (tabular lining);
`--text-figure` clamp(2.75→4.25rem), `--text-figure-sm`, `--text-h1` 1.5rem, `--text-h2` clamp(1.3→1.6rem),
`--text-h3` 1.0625rem, `--text-body` 1rem, `--text-table` .875rem, `--text-small` .8125rem, `--text-chart` 12px;
`--weight-regular|medium|semibold|bold`, `--leading-tight|snug|body`, `--tracking-caps`.
Space: `--space-0…9` = 0, 4, 8, 12, 16, 24, 32, 48, 64, 96 px.
Shape: `--radius-sm|md|lg|pill` (4/8/14 px in A; 3/6/8 in B), `--border-width`, `--focus-width`;
`--shadow-sm|md|lg` (deeper in dark). Layout: `--layout-max`, `--layout-gutter`.
Motion: `--duration-fast|base|slow` (120/200/320 ms; 0 under reduced motion), `--ease-standard`.

## Layout and behaviour decisions
- Order: header (pickers, as-of/horizon/paths/option badges, provenance) → compare differences → headline →
  "About these numbers" (always visible) → budgets + reserve → required return → fan → survival → year table
  (collapsed) → inputs → glossary. One column under ~900 px.
- Run picker is a disclosure with radio rows (name, date, budget, return, success); filter box appears past 6 runs.
  Arrow keys preview, Enter/click closes. Selection is kept in the URL hash (`#run=…&compare=…`).
- Compare: run A = filled **circle**, run B = filled **square** in every chart and table, so colour is never the only cue.
  Tables align rows by target value; charts align by year and leave gaps.
- Budgets chart: dot per target, hollow marker = with reserve, joined by a line so the reserve's cost is visible;
  dashed line = current budget. Reserve table adds "Cost of reserve" (difference of the rounded-down budgets).
- Required return: margin bar between required and assumed (solid green = margin, dashed amber = shortfall),
  plus a "✓ +x pts" / "! x pts short" tag in the table. Negative returns shown with a true minus.
- Fan and survival charts default to "Main span" (until < 0.1 % of futures still unresolved), with an "All years"
  toggle; hover or arrow keys read any year. Compare overlays B as dashed outlines over A's bands.
- Status colour on the headline compares the rate with the run's own targets ("Meets the 90 % target, not 95 %").
- Rounding: budgets floor to £1; required returns ceil to 2 dp; success rates floor to 2 dp (never overstate);
  SE 3 dp. `null` → dash + the row's note; `converged: false` → "! Not converged" tag.
- Column notes: every table header that maps to a CSV column carries an (i) button with meaning and unit; the
  glossary lists all columns.
