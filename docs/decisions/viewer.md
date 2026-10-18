# Viewer Decisions

Scope: the HTML results viewer and every other SBRetire web page: the common CSS theme, where pages live and how they
reach run data.

## 1. Common CSS theme: Direction A "Paper", one `theme.css` of custom properties shared by every SBRetire page

Every SBRetire web page takes all colours, fonts, sizes, spacing, radii, shadows, layout widths, motion and chart
colours from one stylesheet, `src/sbretire/web/theme.css`, which contains only CSS custom properties. Page CSS and
script use them through `var(--…)` and never contain colour literals. The theme is Claude Design's Direction A
"Paper": a warm off-white background, ink-coloured text and one deep green accent. It uses a serif stack
(Iowan Old Style, Charter, Georgia) for headings and headline figures, a system sans stack for body text, and tabular
lining numerals. Fonts are local system stacks only, never downloaded. Colours are `oklch()`.

Token groups (full list and values in `theme.css` and `docs/design/theme-notes.md`):

- **colour:** `--color-bg`, `--color-surface`, `--color-surface-raised`, `--color-surface-sunken`, `--color-border`,
  `--color-border-strong`, `--color-text`, `--color-text-muted`, `--color-accent`, `--color-accent-soft`,
  `--color-on-accent`, `--color-focus`, `--color-tooltip-bg`, `--color-tooltip-text`,
  `--color-success|warning|failure` and their `-soft` variants;
- **chart:** `--chart-run-a`, `--chart-run-b`, `--chart-person-1`, `--chart-person-2`, `--chart-both`,
  `--chart-fan-outer`, `--chart-fan-inner`, `--chart-fan-median`, `--chart-grid`, `--chart-axis`,
  `--chart-axis-text`, `--chart-zero`, `--chart-hover`;
- **type:** `--font-display`, `--font-body`, `--font-figures`, `--font-mono`, `--numeric`, `--text-*` sizes,
  `--weight-*`, `--leading-*`, `--tracking-caps`;
- **space, shape, layout, motion:** `--space-0…9` (4 px base), `--radius-sm|md|lg|pill`, `--border-width`,
  `--focus-width`, `--shadow-sm|md|lg`, `--layout-max`, `--layout-gutter`, `--duration-fast|base|slow`,
  `--ease-standard`.

Dark mode follows the system on screen (`@media screen and (prefers-color-scheme: dark)` on
`:root:not([data-theme="light"])`), and `:root[data-theme="dark"]` or `"light"` forces a mode. Print always uses the
light tokens. Reduced motion sets the durations to zero. Text tokens meet WCAG AA (checked by a test). Direction B,
"Instrument" (cool greys, blue accent, all sans), was not chosen. (F-022)

**Why**: the user asked for one common theme, to be determined with Claude Design, so that every page looks like one
product and a colour or font changes in one place. After viewing both directions in the browser, the user chose A
because it reads like a calm printed statement. A theme made only of custom properties lets a future page (for
example an HTML results guide) reuse it by linking one file.

## 2. Pages ship inside the package and a named run copies them next to its data

The viewer's source is `src/sbretire/web/viewer/` (`index.html`, `viewer.css`, `viewer.js`) plus the common
`src/sbretire/web/theme.css`. After each named run, `sbretire run` copies these four files into `<output-dir>/`
next to `runs/` (overwriting older copies), so `<output-dir>/index.html` opened from disk loads `runs/runs.js` with a
`<script>` tag. Unnamed runs do not copy the page. (F-022)

**Why**: the user chose this over opening a page in the repo that reads `../output`, because it works with any
`--output-dir` and from `file://` without a server, and the copied page always matches the installed version that
wrote the data.

## 3. Save as PDF uses the browser's print dialog, always black and white, A4, with nothing split

The viewer's **Save as PDF** button sets the page title to `SBRetire <run> [vs <run>] <created date>` (the browser's
default PDF file name) and calls `window.print()`; the household chooses "Save as PDF" in the dialog. Printing is
always black and white: `theme.css` has a print-only token set in which every colour and chart token is a neutral
grey (chroma 0), so page CSS stays token-only and charts stay readable through their dash patterns, hatching and
markers. Pages are A4 portrait with `@page` margin boxes: "SBRetire results" top left, the run names top right and
"Page X of Y" bottom right. Cards, figures and table rows never break; before printing, each section's heading block
and intro are wrapped with its first card so a heading is never stranded at a page foot, and every fold is opened;
everything is restored after printing. The 18-column year table prints as two tables of ten columns, adding the
budget in today's money so every annual column appears, with the year in both. `scripts/render_viewer_pdf.py` renders the example sample with headless Edge or Chrome for review. (F-023)

**Why**: the user asked for a button that makes a black-and-white PDF in which cards and tables do not cross pages.
The browser's own print engine gives searchable vector text, needs no dependency and works offline; JavaScript PDF
libraries rasterise the page, and a page cannot choose the PDF destination itself. Grey tokens rather than a
greyscale filter keep the text sharp. An investigation on 2026-10-09 showed `break-after: avoid` alone did not keep
headings with their content in Edge, and that the 18-column table does not fit even landscape A4.

## 4. The Portfolio page is built in the Paper theme and reads one portfolio.json

The Portfolio page (`src/sbretire/web/portfolio/`: `portfolio.html`, `portfolio-view.css`, `portfolio-view.js`)
reuses `viewer.css` for the masthead, sections, cards, tables and chart classes, and adds only layout in
`portfolio-view.css`. It uses no new theme tokens: charts use `--chart-run-a/b` and the grid and axis tokens, and
each mix has its own marker shape (square, triangle, diamond and circle), so the page reads in greyscale print.
Heatmaps print every value and tint cells with `color-mix()` of chart tokens. `sbretire portfolio report` copies
the page, `viewer.css` and `theme.css` into the output folder and writes `portfolio/portfolio.js`
(`window.SBRETIRE_PORTFOLIO`), so `output/portfolio.html` works from disk. The results viewer links to it
("Portfolio") and it links back ("Results"). The page follows `docs/design/portfolio-design-handoff.md` for:
- section order and chart choices;
- wording: "analysis, not advice", no "you should";
- print: Save as PDF, A4, black and white, nothing split, its own "SBRetire portfolio" page header;
- privacy: no network.

A section whose analysis did not run shows its plain reason. (F-030)

**Why**: the user chose to have the page built here rather than wait for a Claude Design pass (2026-10-18).
Keeping to the theme's tokens and the results viewer's classes lets a later design pass restyle it without
changing `portfolio.json`.

