---
id: F-030
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 8
created: 2026-10-18
updated: 2026-10-18
---
# F-030 Portfolio Page in the Viewer

## 1. Purpose

Bring every portfolio analysis together on **one offline page** beside the results viewer.

`sbretire portfolio report`:
- runs valuation (F-025), returns (F-026), performance (F-027), look-through (F-028) and the frontier (F-029);
- adds three extras the hand-off asks for: correlation and risk contribution; income and fees for the last 12
  months; a monthly-returns calendar with the worst drawdowns;
- writes one versioned document, `output/portfolio/portfolio.json`, plus `portfolio/portfolio.js`, which sets
  `window.SBRETIRE_PORTFOLIO`;
- copies a **Portfolio page** (`portfolio.html`) into the output folder, next to the results viewer's
  `index.html`, with links between the two.

Any analysis that cannot run yet is marked unavailable with a plain reason, and the page says so. Examples: no
price files yet, or no factsheets. Nothing ever stops the page appearing.

The page follows the Claude Design hand-off (`docs/design/portfolio-design-handoff.md`): its sections, charts,
wording, print rules, accessibility and privacy. It uses the Paper theme. It is built here rather than by Claude
Design (user, 2026-10-18); a later design pass can restyle it without changing `portfolio.json`.

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Who designs | Built in this feature from the hand-off, in the Paper theme, reusing the results viewer's `viewer.css` (masthead, sections, cards, tables, chart classes, print rules) plus a small `portfolio-view.css`; no new theme tokens (charts use `--chart-run-a/b`, grid and axis tokens, with shapes and dash patterns for greyscale) | Consistent look; Claude Design can restyle later | user 2026-10-18 |
| 2 | Files | Page: `src/sbretire/web/portfolio/portfolio.html`, `portfolio-view.css`, `portfolio-view.js`. `sbretire portfolio report` copies them, `viewer.css` and `theme.css` into `<output-dir>/` and writes `<output-dir>/portfolio/portfolio.json` and `portfolio.js` (`window.SBRETIRE_PORTFOLIO = …;`). The results viewer gets a "Portfolio" link and the page a "Results" link | Mirrors the results viewer (viewer.md §2); works from `file://` | viewer §2 |
| 3 | Document | `portfolio.json`, `schema_version` "1.0", schema `schemas/portfolio.schema.json`; sections `settings`, `total`, `accounts`, `holdings`, `exposure`, `performance`, `frontier`, `risk`, `rebalance`, `income`, `warnings`, `data_files`. Every analysis section has `available` (true/false) and `reason` when false. Money in GBP, shares 0–1, months `YYYY-MM` | One contract for the page and later tools | hand-off §3 |
| 4 | Extras | **Risk:** correlation matrix of the priced sleeve (from the frontier's covariance) and each series' share of the sleeve volatility `wᵢ(Σw)ᵢ / wᵀΣw` beside its weight. **Income and fees:** per month for the 12 complete months before the newest export folder, from the ledger: dividends, interest, fees and tax withheld, in GBP (USD at the valuation rate). **Calendar:** the back-test's monthly returns as years × months with each year's compounded total. **Drawdowns:** the five worst non-overlapping episodes of the back-test (peak, trough, recovery or none, depth, months to trough and to recover) | Hand-off sections the earlier features did not produce | user 2026-10-18 |
| 5 | Not yet | Time- and money-weighted account returns (F-031) and a benchmark line are not in 1.0; the page leaves them out without placeholders | Not built yet | F-027 |
| 6 | Graceful | Each analysis runs only if its inputs exist: performance needs a risk-free rate; frontier and risk need ≥ 2 fully priced series; look-through needs `securities.yaml`. Otherwise the section is `{"available": false, "reason": "…"}`. Invalid configuration (bad YAML, bad factsheet) still exits 2 | The page must work from the first export | this brief |
| 7 | Page sections | Headline (total, by person and account, `starting_balance` line with a Copy button, key back-test figures) → Allocation (accounts, asset class, region, sector, currency bars, top look-through) → Efficient frontier (scatter: frontier curve, each series alone, today, minimum variance, max Sharpe, target, capital market line; table alternative) → Re-weighting (dumbbell today→target, within-account trades with costs, household trades marked analysis only) → Performance (growth of £1, underwater chart, calendar heatmap, rolling 12 months, worst drawdowns) → Risk (correlation heatmap, risk vs weight bars) → Income and fees (grouped bars, fees below zero) → Holdings table → Data and caveats | Hand-off §4 order | hand-off §4 |
| 8 | Wording and safety | Hand-off §5 number rules and banned phrases; every data string inserted through `esc()`; no network, fonts or scripts beyond the two local files; only `var(--…)` colours | Same checks as the results viewer | hand-off §5, §8 |
| 9 | Print | Save as PDF as on the results page: A4, black and white tokens, cards/charts/rows never split, headings kept with content, screen-only controls hidden | viewer.md §3 | viewer §3 |
| 10 | Command | `sbretire portfolio report` takes the options of `exposure` and `frontier` (`--root`, `--accounts`, `--prices`, `--factsheets`, `--output-dir`, `--months`, `--usd-gbp`, `--risk-free`, `--max-weight`, `--covariance`, `--target`, `--min-trade`) and prints which sections are available. Exit 0 written, 1 unreadable, 2 invalid configuration | One command for the page | this brief |
| 11 | Design sample | `scripts/build_portfolio_design_sample.py` now builds the sample by running the report on synthetic fixtures (invented holdings and seeded prices) into `docs/design/sample/portfolio/`, schema 1.0, `"synthetic": true` | One generator; the sample always matches the schema | hand-off §3 |

## 3. Context

- **Analysis APIs:**
  - `today_values` and `build_returns` (F-026);
  - `build_performance` and `drawdowns` (F-027);
  - `build_exposure` (F-028);
  - `build_frontier`, `Estimates` and `Mix` (F-029);
  - `build_ledger` (F-024);
  - `value_holdings` (F-025).
- **Results viewer patterns:**
  - `src/sbretire/web/viewer/` provides `esc`, the `F` formatters, SVG charts, `wrapForPrint` / `unwrapAfterPrint`,
    `printPdf` and the theme toggle;
  - `copy_viewer` and `VIEWER_FILES` live in `results_json.py`.
- **Static page tests:** `tests/unit/test_viewer.py` checks tokens only, no network, escaping and print rules. The
  portfolio page gets the same checks.
- **Design sample:** `docs/design/sample/portfolio/` holds the 0.1-draft sample, now replaced.
  `tests/unit/test_design_handoff.py` may check it.

## 4. Touch-points

**New:**
- `src/sbretire/ledger/report.py` additions: `drawdown_episodes`, `calendar`, `risk_contribution`,
  `correlation`, `income_by_month`.
- `src/sbretire/ledger/document.py`: `build_portfolio_document`, `write_portfolio_files`, `copy_portfolio_page`.
- `schemas/portfolio.schema.json`.
- `src/sbretire/web/portfolio/{portfolio.html,portfolio-view.css,portfolio-view.js}`.
- Tests `tests/unit/test_portfolio_*.py`.

**Modified:**
- `src/sbretire/__main__.py`: `portfolio report`.
- `src/sbretire/web/viewer/index.html`: the Portfolio link.
- `scripts/build_portfolio_design_sample.py` and `docs/design/sample/portfolio/*`.
- `tests/unit/test_design_handoff.py`, if it pins 0.1.
- `README.md`.
- `docs/decisions/viewer.md`: §4 Portfolio page.
- `docs/decisions/portfolio-data.md`: §25 portfolio.json.

## 5. Interfaces

```python
# sbretire/ledger/report.py (extras)
def drawdown_episodes(
    months: Sequence[dt.date], returns: Sequence[float], top: int = 5
) -> list[dict[str, object]]: ...
def calendar(months: Sequence[dt.date], returns: Sequence[float]) -> list[dict[str, object]]: ...
def correlation(cov: NDArray[np.float64]) -> NDArray[np.float64]: ...
def risk_contribution(weights: NDArray[np.float64], cov: NDArray[np.float64]) -> NDArray[np.float64]: ...
def income_by_month(
    rows: Sequence[LedgerRow], first: dt.date, last: dt.date, usd_gbp: float | None
) -> list[dict[str, object]]: ...


# sbretire/ledger/document.py
def build_portfolio_document(
    options: ReportOptions, accounts: Sequence[AccountConfig]
) -> dict[str, object]: ...
def write_portfolio_files(
    document: Mapping[str, object], output_dir: Path
) -> list[Path]: ...  # json, js and page
```

## 6. Plan of Work

1. Extras: drawdown episodes, calendar, correlation, risk contribution, income by month.
2. `portfolio.json` with its schema, `sbretire portfolio report`, files and page copy (a skeleton page first).
3. The Portfolio page: HTML, CSS and JS for every section, print, and the theme toggle.
4. The design sample regenerated, the nav link, docs, and a real run.

## 7. Validation

- **T1:** extras on hand-built series; the document validates against the schema for the full synthetic case and
  for the "nothing priced" case; static page checks (tokens, network, escaping, print, sections).
- **T2:** `sbretire portfolio report` on the synthetic fixtures writes the files. The page is opened in a browser
  on the design sample (light and dark) with no console errors, and every section renders.
- **T3:** the real exports: the page renders with the valuation, the look-through placeholders and unavailable
  analyses (`check:`).

## 8. Decision Log

- 2026-10-18 — §2 #1 (build the page here) and #4 (all three extras) come from the user's answers; the rest are
  mine, following the hand-off.

## 9. Surprises

## 10. Tasks

### F-030.1 Extras for the page
- **Status**: Verification
- **Depends on**: —

`drawdown_episodes`, `calendar`, `correlation`, `risk_contribution`, `income_by_month`. §2 #4.

**Acceptance criteria**
- [x] Known answers: two separate falls give two episodes ordered by depth with peak, trough, recovery (or none) and month counts; the calendar puts returns in the right year and month with each year's compounded total; correlation of a hand-built covariance; risk shares sum to 1 and equal weights for uncorrelated equal-variance series; income groups dividends, interest, fees and tax withheld by month in GBP with USD converted — `test_portfolio_extras_known_answers`

**Notes**
2026-10-18 ledger/extras.py (not report.py, which holds the ledger summary): drawdown_episodes, calendar, correlation, risk_contribution, income_by_month; tests/unit/test_portfolio_extras.py.

### F-030.2 portfolio.json and `sbretire portfolio report`
- **Status**: Verification
- **Depends on**: F-030.1

`ledger/document.py`, `schemas/portfolio.schema.json`, the command, `portfolio.json` and `portfolio.js`, and the
page copy (a skeleton page). §2 #2, #3, #5, #6, #10.

**Acceptance criteria**
- [x] On the F-029 synthetic setup with factsheets and a risk-free rate, every section is available and the document validates against the schema; with no `securities.yaml` and no rate, the valuation sections are present and the others are unavailable with reasons, still valid — `test_portfolio_document_full_and_empty`
- [x] `sbretire portfolio report` writes `portfolio/portfolio.json`, `portfolio/portfolio.js` (`window.SBRETIRE_PORTFOLIO = …`) and the page files next to them, prints the available sections, and exits 2 on an invalid factsheet — `test_cli_portfolio_report`

**Notes**
2026-10-18 ledger/document.py (ReportOptions, build_portfolio_document: valuation always, each analysis or {available: false, reason}; write_portfolio_files: json, js with </ escaped, page files), schemas/portfolio.schema.json 1.0, skeleton src/sbretire/web/portfolio/*, `sbretire portfolio report` (options shared with exposure/frontier); tests/unit/test_portfolio_document.py (2; one assertion rewritten for typing only).

### F-030.3 The Portfolio page
- **Status**: To Do
- **Depends on**: F-030.2

`portfolio.html`, `portfolio-view.css` and `portfolio-view.js` for every section in §2 #7, plus the theme toggle,
Save as PDF and print rules. §2 #1, #7–#9.

**Acceptance criteria**
- [ ] The page uses only theme tokens and no network, loads `portfolio/portfolio.js`, escapes every data string, has a section for each of §2 #7 with an unavailable state, the analysis-not-advice and wrapper caveats, a Save as PDF button and print rules like the results viewer, and avoids the banned phrases — `test_portfolio_page_static`
- [ ] Opened from disk on the design sample in a browser, every section renders without console errors in light and dark — `check: browser on docs/design/sample (render + console)`

### F-030.4 Design sample, nav, docs and a real run
- **Status**: To Do
- **Depends on**: F-030.3

What to build:
- The sample generator and a regenerated sample.
- The Results ↔ Portfolio links.
- README.
- `docs/decisions/viewer.md` §4 and `portfolio-data.md` §25.
- A real run.

**Acceptance criteria**
- [ ] The design sample is regenerated by the script, is synthetic, schema 1.0 and valid; the results viewer links to `portfolio.html` and back — `test_portfolio_design_sample_and_links`
- [ ] README documents `portfolio report` and the page; decisions recorded — `check: grep -n "portfolio report" README.md docs/decisions/viewer.md docs/decisions/portfolio-data.md`
- [ ] On the real exports the report writes the page and the browser shows the valuation with the other sections marked unavailable (run locally; never committed) — `check: uv run sbretire portfolio report --usd-gbp 0.7503 --risk-free 0.04`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Extras — `test_portfolio_extras_known_answers`
2. Document — `test_portfolio_document_full_and_empty`
3. CLI — `test_cli_portfolio_report`
4. Page static — `test_portfolio_page_static`
5. Page in a browser — `check: browser on docs/design/sample (render + console)`
6. Sample and links — `test_portfolio_design_sample_and_links`
7. Docs — `check: grep -n "portfolio report" README.md docs/decisions/viewer.md docs/decisions/portfolio-data.md`
8. Real run — `check: uv run sbretire portfolio report --usd-gbp 0.7503 --risk-free 0.04`
