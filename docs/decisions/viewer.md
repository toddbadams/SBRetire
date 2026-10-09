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
