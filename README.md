# SBRetire — Retirement Sustainability Model

Monte Carlo model that estimates the **maximum sustainable household spending** (in today's GBP)
for two people's joint remaining lifetimes, at a target probability of never running out of money.

The authoritative specification is [docs/SPEC.md](docs/SPEC.md). The model is for planning and
research only — it is **not financial advice**, does not forecast investment returns, and does not
guarantee future solvency.

> Status: **V1 (1.0.0)**. Every SPEC §17 test and acceptance criterion is evidenced in
> [docs/acceptance.md](docs/acceptance.md). The build history is in [docs/epics/roadmap.md](docs/epics/roadmap.md)
> and [CHANGELOG.md](CHANGELOG.md).

## Install

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

On Windows (PowerShell), from the project folder:

```powershell
uv sync
Copy-Item config\model.example.yaml config\model.yaml   # first time only, then edit it
uv run sbretire run --config config\model.yaml --output-dir output
```

## Run

```bash
cp config/model.example.yaml config/model.yaml   # then edit your own assumptions
uv run sbretire validate --config config/model.yaml
uv run sbretire preview --config config/model.yaml --death-ages 88,92
uv run sbretire run --config config/model.yaml --output-dir output
```

`config/model.yaml` is git-ignored so personal inputs stay out of version control.

`validate` checks the scenario without running the model: it prints a one-line summary and exits 0, or lists
every problem with its YAML location (e.g. `income[2].survivor_percentage: must be less than or equal to 1`) and
exits 2; an unreadable file exits 1. Add `--require-data-files` to also load `mortality.data_file` and check it
covers both people (see Mortality below).

## Configuration

The scenario is one YAML file; start from `config/model.example.yaml`. Every key is required unless marked
optional. Amounts are GBP, and "today" means prices at `model.as_of_date`.

| Section | Key | Meaning |
|---|---|---|
| `model` | `currency` | `GBP` (V1) |
| | `as_of_date` | Valuation date and first simulated month; the 1st of a month, e.g. `"2026-10-01"` |
| | `simulation_count` | Number of simulated futures (paths), e.g. 100000 |
| | `confidence_levels` | Target success probabilities, each strictly between 0 and 1, e.g. `[0.90, 0.95, 0.99]` |
| | `frequency` | `monthly` (V1) |
| | `horizon_years` | Computational cap on the simulation; someone alive at the end leaves the path unresolved |
| | `random_seed` | Integer seed, or `null` to generate one and record it in `run_metadata.json` |
| | `unknown_keys` | Optional: `error` (default) or `warn` |
| `portfolio` | `starting_balance` | Investable savings today (GBP) |
| | `annual_return` | Fixed nominal annual effective return after fees, e.g. `0.04`; must be > −1 |
| `budget` | `monthly_amount_today` | Household spending per month in today's GBP while both are alive |
| | `survivor_budget_factor` | Share of the budget the survivor needs after the first death, e.g. `0.70` |
| | `end_reserve_months` | Optional, default `0` (off): months of budget that must remain at the second death for the extra reserve table, e.g. `12` |
| | `spend_at_least_income` | Optional, default `false`: when `true`, each month's spending is at least that month's income, so surplus income is spent rather than saved |
| `inflation` | `source`, `source_period` | Calibration source and years, e.g. `UK_CPI`, `"1989-2025"` |
| | `data_file` | CPI file, relative to the config file, e.g. `../data/uk_cpi.csv` |
| | `model`, `parameter_units` | `ar1_lognormal`, `log_annual` |
| | `log_mean`, `ar1_coefficient`, `innovation_sd`, `initial_rate` | AR(1) parameters of log(1 + annual inflation), and last year's rate (see Inflation below) |
| `mortality` | `source`, `geography`, `projection` | Must match the data file's sidecar, e.g. `ONS_2024_BASED`, `UK`, `principal` |
| | `data_file` | Mortality table, relative to the config file, e.g. `../data/ons_mortality.csv` |
| `people` (exactly two) | `id`, `name` | Unique id (not `household`) and display name |
| | `date_of_birth` | ISO date; only the year and month matter |
| | `sex` | `male` or `female` (the ONS table's categories) |
| | `survivor_budget_factor` | Optional: this person's own factor when they are the survivor (overrides the household one) |
| `income` (optional list) | `id`, `name` | Unique id and display name |
| | `start_date`, `end_date` | 1st of a month; `end_date` is optional and exclusive |
| | `annual_amount_today` | Annual amount in today's GBP |
| | `inflation_linked` | `true`: grows with simulated CPI; `false`: fixed nominal |
| | `survivor_percentage` | Share (0–1) that continues after the recipient dies while the other person lives |
| | `recipient` | A person `id`, or `household` for jointly owned income |

Configuration rules worth knowing (full list in `docs/decisions/configuration.md`):

- `model.as_of_date` and every income `start_date` / `end_date` must be the 1st of a month; `end_date` is exclusive.
- Relative paths (e.g. `mortality.data_file`) are resolved from the config file's own directory.
- Unknown or duplicated keys are errors; set `model.unknown_keys: warn` to report unknown keys as warnings instead.
- Numbers, booleans and dates are not coerced from strings: write `0.05`, `true`, `"2026-10-01"`.

Budget (full rules in `docs/decisions/configuration.md` §6):

- `budget.monthly_amount_today` is the household's monthly spending in today's GBP while both people are alive;
  it grows with inflation.
- After the first death spending becomes the budget × the survivor's own `people[].survivor_budget_factor` (the
  share of the joint budget that person needs living alone); if the survivor has none, the household
  `budget.survivor_budget_factor` applies.
- `budget.end_reserve_months` (optional, default 0) asks for an extra answer: the most you can spend and still leave
  that many months of budget in savings when the second person dies (see below).
- `budget.spend_at_least_income: true` (optional, default `false`) makes each month's spending the larger of the
  budget-based spending and that month's household income. V1 saves any income above the budget; with this option
  the household spends it instead, which can only lower (never raise) the success rates and budgets
  (`docs/decisions/configuration.md` §9). `annual_budget_nominal_median` then includes the top-up.

Income streams (full rules in `docs/decisions/configuration.md` §4–§5):

- `annual_amount_today` is in today's GBP. An `inflation_linked: true` stream grows with inflation from the
  as-of date, so a pension starting in 2029 begins at its inflated amount; a non-linked stream pays the same
  nominal amount for its whole life.
- `survivor_percentage` is what continues after the `recipient` dies while the other person is alive: `0` for
  income that dies with its owner (e.g. UK State Pension), `0.5` for a typical spouse's pension. It also applies
  from `start_date` if the recipient died before the stream started.
- `recipient: household` marks income owned by the household (e.g. rent, a joint annuity): paid in full while both
  are alive and × `survivor_percentage` once one has died. `household` cannot be used as a person `id`.

Inflation (full rules in `docs/decisions/data-and-calibration.md` §2–§3 and `simulation-conventions.md` §5):

- `model: ar1_lognormal`: each simulated year draws one rate π per path, with
  log(1 + π_y) = `log_mean` + `ar1_coefficient` × (log(1 + π_{y−1}) − `log_mean`) + `innovation_sd` × ε. So
  high-inflation years tend to cluster, as in the 1990s and 2022–23, and 1 + π is always positive.
- `parameter_units: log_annual`: every parameter describes log(1 + annual rate), not the arithmetic mean or standard
  deviation of π. The median rate is e^`log_mean` − 1 (about 2.81 % for UK CPI 1989–2025); `initial_rate` is the year
  before the as-of date (2025: 3.4 %).
- Years start at the as-of month and the year's rate compounds monthly: prices are I_t = I_{12k} × (1 + π_k)^(m/12)
  m months into year k, with I = 1 in the as-of month.
- The parameters are calibrated from `inflation.data_file` (ONS CPI series D7G7, provenance in `data/README.md`) over
  `source_period`. To recalibrate after updating the data, run
  `uv run python scripts/calibrate_inflation.py --config config/model.yaml` and paste the block. You may also edit
  them to stress-test, for example with a higher `log_mean`.
- Every `inflation_linked: true` income follows this one UK CPI path. Income that really rises with another measure,
  such as US Social Security's COLA paid in dollars, is approximated by UK CPI at your planning exchange rate.

Mortality (full rules in `docs/decisions/data-and-calibration.md` §1; provenance in `data/README.md`):

- `mortality.data_file` points at `data/ons_mortality.csv`: ONS 2024-based UK cohort death rates, principal
  projection, built from the exact ONS workbook in `data/raw/`. Its sidecar `data/ons_mortality.meta.json` must match
  the config's `mortality.source`, `geography` and `projection`.
- A person aged x (completed years, counted from their birth month) uses q(x, b + x), where b is their birth year:
  the chance of dying before their next birthday, for the cohort they were born into. Above age 100 the cohort's
  age-100 rate is held, so very long lives stay possible.
- `sbretire validate --require-data-files` loads the table and checks it covers both people from their current age to
  100; any gap or invalid row is reported with its location and exits 2.
- Each simulated month a living person dies with probability q_m = 1 − (1 − q)^(1/12): the annual rate for their
  age spread evenly over the twelve months of that year of age. The two people are independent.
- The model draws one random number per person per path and reads their death month off their survival curve.
  This is statistically the same as a month-by-month draw, and lengthening the horizon never changes a death that
  falls inside the shorter one (`docs/decisions/simulation-conventions.md` §6).
- A person who dies during a month has that month's full income and spending and is gone from the next month. Anyone
  alive at the end of the horizon leaves the path unresolved (censored): it is never counted as a success.

## Running the model

```bash
uv run sbretire run --config config/model.yaml --output-dir output
```

`run` validates the scenario, loads and checks both data files, then simulates `model.simulation_count` futures
(Paths) of your household from the as-of month. Each future has its own random death months for both people and its
own inflation path, while your fixed `portfolio.annual_return` stays the same. Every random draw comes from
`model.random_seed`, so the same seed, config and data give identical results. The run first prints an **Inputs**
block listing every setting it is about to use (also written to `output/inputs.csv`), then a summary, and writes
`output/run_metadata.json`. A full run of 100,000 paths takes about 1½ minutes.

### Reading the results

Each Path ends as exactly one of:

- **Successful**: the money paid every month's spending until both of you had died.
- **Failed**: in some month the money (after that month's return and income) could not cover the spending.
- **Unresolved**: the money never ran out, but someone is still alive at the end of the horizon, so the outcome is
  unknown. These are never counted as successes.

Two rates are reported:

- **Conservative success rate** = successful ÷ all paths, with unresolved paths counted as non-successes. This is
  the number to plan with, and what budget optimisation will target.
- **Completed-path success rate** = successful ÷ (successful + failed), shown alongside for context.

The `+/-` figure is one Monte Carlo standard error: √(p(1−p)/N), with the denominator printed beside it. It
measures simulation noise only, so more paths shrink it. It is **not** a confidence interval and says nothing about
whether the assumptions are right. A "95 % confidence level" in this model means "95 % of simulated paths succeed".

### Maximum sustainable budget

After the summary, `run` prints one row per `model.confidence_levels` target. Each row gives the **Maximum
sustainable budget**: the largest monthly budget in today's GBP (rising with inflation each month) at which at
least that share of simulated paths succeeds, using the conservative rate.

- Every candidate budget is tested against the same simulated futures (common random numbers), so the results
  differ only because the budget differs.
- The search finds each path's own break-even budget to within £1/month (`docs/decisions/optimization.md` §1).
  The reported budget is the feasible end of that range, and it is re-checked with one run at that exact budget.
  The success rate and its standard error come from that check.
- If too many paths still have someone alive at the horizon, a target can be **infeasible**: even spending nothing
  can't reach it. The row says so instead of showing a number. A row whose search reached the £1,000,000/month
  cap is marked as not converged.
- Expect about 25 engine runs.

### Leaving an end-of-life reserve

Set `budget.end_reserve_months` (for example `12`) to also ask: how much can we spend and still leave R months of
budget in savings when the second of us dies? A path then meets the target only if it is Successful **and** its
balance in the month of the second death is at least R × the monthly budget, inflated to that month along that
path's own inflation. The full budget is used, not the survivor's reduced one. A path that ends with less counts as
failed; unresolved paths still never count (`docs/decisions/optimization.md` §3).

`run` then adds a line with the success rate leaving the reserve at your budget, a second table **Maximum
sustainable budget leaving an R-month reserve** after the first, and `lifestyle_reserve_results.csv`. The search is
the same per-path bisection: a higher budget never leaves more money and needs a bigger reserve. With the default
`0` nothing changes, and V1 configs keep their config hash.

These figures are model estimates from your assumptions (fixed return, no tax, simulated inflation and lifetimes).
They are not financial advice and not a guarantee.

### Required return

Last, `run` prints the **Required return** for your configured `budget.monthly_amount_today`. That is the lowest
fixed annual return (nominal, after fees, earned every year) at which each confidence level is still met.

- It is a stress test of the return you assumed. If your `portfolio.annual_return` is well above the required
  return for your chosen confidence level, the plan has a margin. If it is below, it doesn't.
- The search runs from −50 % to +50 % a year, to within 0.01 percentage points, against the same simulated
  futures (`docs/decisions/optimization.md` §2). A test confirms that success never falls as the return rises.
- If a target can't be met even at +50 % a year, the row says **no solution within bounds**. A plan that meets the
  target even at −50 % shows "at or below −50 %" and is marked not converged.
- The rate shown comes from one confirming run at the required return.
- Displayed figures round in the cautious direction: budgets **down** to whole pounds, required returns **up** to
  0.01 %. The number you read off therefore always meets its target.

Required returns are model outputs under a fixed-return assumption. They are not forecasts of what markets will
deliver. The return search adds about 16 engine runs.

## Named runs and results.json

Give a run a name to keep it alongside others, for example to compare return assumptions:

```bash
uv run sbretire run --config config/model.yaml --name base-4pct
uv run sbretire run --config config/model-3pct.yaml --name stress-3pct
```

- A named run writes all its files to `output/runs/<name>/` instead of `output/`. Names are 1–64 letters, digits,
  `-` or `_`, starting with a letter or digit, and not a Windows device name such as `CON` or `NUL`.
- Re-using a name is refused (exit 2) before anything is computed. Add `--overwrite` to replace that run; its old
  files are removed only once the new results are ready, so a failed rerun leaves the old run in place.
- Every run, named or not, also writes **`results.json`**: all of the run's results in one file (inputs, summary,
  budget, reserve and return tables, annual rows and column notes). Its structure is fixed by
  `schemas/results.schema.json` (`schema_version` `"1.0"`), and its numbers match the CSVs, including their
  cautious rounding. In `returns`, the success figures at the required return are named
  `*_at_required_return`, so they can't be confused with the configured-return columns of
  `sustainability_results.csv`.
- After each named run, `output/runs/index.json` (one line per run: name, date, headline figures) and
  `output/runs/runs.js` are rebuilt from every run folder on disk. `runs.js` sets `window.SBRETIRE_RUNS`, so a
  web page opened straight from disk (`file://`) can load every run with a `<script>` tag. Delete a run's folder to
  drop it at the next named run.
- `results.json` holds names, dates of birth and amounts from your config. `output/` is git-ignored; keep it that
  way. `docs/design/sample/runs/` holds a sample built only from `config/model.example.yaml`
  (`uv run python scripts/build_design_sample.py`).

### Viewing runs in a browser

Each named run also copies the results viewer (`index.html`, `theme.css`, `viewer.css`, `viewer.js`) into the
output folder, next to `runs/`. Double-click **`output/index.html`** (no server, works offline) to:

- pick a run, or a second run to compare side by side;
- read the success rate, the maximum sustainable budget (and the end-of-life reserve, if set), and the required
  return;
- see the portfolio fan chart, the survival curves and the year-by-year table, every input, and what each
  figure means.

**Save as PDF** (top right) opens the browser's print dialog. Choose "Save as PDF" (or "Microsoft Print to PDF")
as the printer; the suggested file name is the run name and date. The PDF is black and white on A4: each section's
heading stays with its first card, no card, chart or table row is split across pages, the year-by-year table prints
as two tables that fit the page, and every page carries the run name and "Page X of Y". Printing from the browser
menu (Ctrl+P) gives the same pages, but only the button sets the file name. To review the layout without
clicking, `uv run python scripts/render_viewer_pdf.py`
prints the example sample with headless Edge or Chrome into `output/pdf-check/`.

The page reads only `runs/runs.js` and sends nothing anywhere. Its look comes from the common SBRetire theme
(`src/sbretire/web/theme.css`, `docs/decisions/viewer.md` §1); "Theme" at the top switches between auto, light and
dark.

## Preview (deterministic illustration)

`sbretire preview --config config/model.yaml --death-ages 88,92` runs **one** household future and prints a
year-by-year table, then writes `output/preview.csv` (`--output-dir` to change). It is a **deterministic
illustration, not a sustainability estimate**: there is no randomness and no probability of success.

- `--death-ages A,B` — age at death for each person, in the config's `people` order; each person is dead from the
  start of the month of that birthday. Ages at or below someone's current age are rejected.
- Inflation is constant at the median rate e^`log_mean` − 1, compounding monthly from the as-of month; the return
  is the fixed `portfolio.annual_return`.
- One row per calendar year (the first and last may be partial): `income`, `spending`, `investment_return`,
  `net_withdrawal` (spending − income) and `balance_end` in nominal GBP, `balance_end_today` deflated to today's
  GBP, and the `price_index`. In the month money runs out, `spending` shows what was needed; the unpaid part is the
  shortfall in the summary.

## Reproducibility and `run_metadata.json`

Every Monte Carlo run draws from one root seed (`model.random_seed`). Mortality and inflation each get their own
Random Stream from that seed, so the same seed, inputs and data files give identical results, and changing one
component never shifts the other's draws. Rules in `docs/decisions/simulation-conventions.md` §4 and
`docs/decisions/configuration.md` §7–§8.

- `random_seed: null` generates a fresh 128-bit seed and records it in `run_metadata.json` with
  `"seed_source": "generated"`. To repeat that run, paste the `seed` value into `model.random_seed`. It is a JSON
  integer; read it with Python or a text editor, since JavaScript tools round numbers that large.
- `config_sha256` is a hash of the validated scenario: comments, key order and formatting don't change it, any value
  does. The mortality file's location is left out (it differs between machines); its content is hashed under
  `data_files`.
- `run_metadata.json` also records the software, Python, NumPy and platform versions, `simulation_count`,
  `horizon_years`, the config path and `created_at` (UTC). `created_at` is the only field that should differ between
  two runs of the same inputs and seed.

## Outputs (V1)

| File | Contents |
|---|---|
| `inputs.csv` | Every setting the run used, one row per config field, plus the seed used and ages at the as-of date |
| `annual_results.csv` | Year-by-year survival, spending, income and portfolio percentiles (SPEC §12) |
| `sustainability_results.csv` | Success probabilities and required-return search per budget/target (SPEC §13) |
| `lifestyle_results.csv` | Maximum sustainable budget per confidence level (SPEC §14) |
| `lifestyle_reserve_results.csv` | Only with `budget.end_reserve_months` > 0: the same, leaving the end-of-life reserve |
| `run_metadata.json` | Seed, version, config hash, data-file versions/hashes (SPEC §10.3) |
| `results.json` | Every result of the run in one JSON file for web pages (`schemas/results.schema.json`) |
| `index.html` + `theme.css`, `viewer.css`, `viewer.js` | Named runs only: the results viewer for every run in `runs/` |
| `results_guide.md` | A plain-English guide to this run: your results, how each figure was calculated (with your numbers), the assumptions and limitations, every column of every file, and the inputs |

All CSVs share the same format:

- UTF-8, with a header row and `\n` line endings.
- `.` as the decimal point, and no thousands separators or currency symbols.
- Money in GBP to 2 dp. Probabilities as decimals from 0 to 1, to 6 dp.
- An empty cell where a statistic has nothing to average over.

### `inputs.csv`

One row per field of your validated config (every person and income stream included, unset optional fields
empty), then a few derived rows: the seed actually used, each person's age at the as-of date and the last simulated
month. Data files appear by file name only.

| Column | Unit | Meaning |
|---|---|---|
| `section` | text | `model`, `portfolio`, `budget`, `inflation`, `mortality`, `people`, `income` or `derived` |
| `item` | text | Where the value lives in the config, e.g. `budget.monthly_amount_today` or `people[person_1].date_of_birth` |
| `label` | text | Plain-English name |
| `value` | as written | The exact value used (numbers unrounded, dates ISO, lists separated by `;`) |
| `unit` | text | The value's unit; for `run.seed`, whether the seed came from the config or was generated |

### `annual_results.csv`

One row per calendar year at your configured budget, from the as-of year to the last year anyone is alive in any
simulated future (at most the horizon). "Year end" means the row's last simulated month, so the first and last rows
can be partial years. Definitions are in `docs/decisions/simulation-conventions.md` §8.

| Column | Unit | Meaning |
|---|---|---|
| `year`, `months` | year, count | Calendar year and the number of simulated months it covers |
| `probability_both_alive`, `probability_person_1_alive`, `probability_person_2_alive` | share of all paths | Alive at year end (person 1/2 = first/second entry under `people`) |
| `monthly_budget_today` | GBP/month, today's money | Your configured budget |
| `monthly_budget_nominal_median` | GBP/month, nominal | Median over paths of budget × inflation index at year end |
| `annual_budget_nominal_median` | GBP/year, nominal | Median required household spending in the year (survivor factor applied), over paths still running in the year |
| `annual_income_median` | GBP/year, nominal | Median income received in the year, same paths |
| `annual_net_withdrawal_median` | GBP/year, nominal | Median of spending − income, same paths |
| `portfolio_p05`, `portfolio_p25`, `portfolio_median`, `portfolio_p75`, `portfolio_p95` | GBP, nominal | 5th, 25th, 50th, 75th and 95th percentiles of the year-end balance over paths where someone is alive; paths that ran out count as 0 |
| `probability_not_depleted_yet` | share of all paths | Money has not run out by year end |
| `estimated_lifetime_success_rate` | share | Of the paths not yet out of money at year end, the share that turn out Successful (unresolved paths count as not successful) |
| `completed_paths`, `unresolved_paths` | count | Paths whose outcome is settled by year end (money ran out, or both have died), and the rest |

### `lifestyle_results.csv`

One row per `model.confidence_levels` target, holding the maximum sustainable budget (SPEC §14, §15.3;
`docs/decisions/optimization.md` §1).

| Column | Unit | Meaning |
|---|---|---|
| `target_probability` | share | Target conservative success rate |
| `maximum_monthly_budget_today`, `maximum_annual_budget_today` | GBP, today's money | Largest budget meeting the target, rounded **down** to 0.01. Empty if the target is infeasible |
| `estimated_success_probability`, `standard_error` | share | Conservative success rate at that budget, from a confirming run, and its Monte Carlo SE (denominator: all paths) |
| `unresolved_fraction` | share | Paths with someone alive at the horizon that never ran out, at that budget |
| `budget_tolerance` | GBP/month | Search precision (1.00) |
| `converged`, `iterations` | true/false, count | Whether the search settled within its bounds, and how many engine runs it took |
| `note` | text | Why a row is infeasible or capped, otherwise empty |

### `lifestyle_reserve_results.csv`

Written only when `budget.end_reserve_months` is above 0. Same rows and columns as `lifestyle_results.csv`, for the
stricter test of leaving the end-of-life reserve, with one extra first column.

| Column | Unit | Meaning |
|---|---|---|
| `end_reserve_months` | months | The reserve R: R × the budget, inflated, must remain at the second death |
| `target_probability`, `maximum_monthly_budget_today`, `maximum_annual_budget_today` | as in `lifestyle_results.csv` | Target and the largest budget meeting it while leaving the reserve (rounded **down**) |
| `estimated_success_probability`, `standard_error`, `unresolved_fraction` | share | Rate meeting the reserve target at that budget, its SE, and the unresolved share |
| `budget_tolerance`, `converged`, `iterations`, `note` | as in `lifestyle_results.csv` | Search precision, convergence, engine runs, notes |

### `sustainability_results.csv`

One row per target at your configured budget (SPEC §13, §15.2; `docs/decisions/optimization.md` §2).

| Column | Unit | Meaning |
|---|---|---|
| `monthly_budget_today`, `annual_return` | GBP/month today's money; annual effective rate | The configured budget and return behind the success columns |
| `target_probability` | share | Target conservative success rate |
| `estimated_success_probability` | share | Completed-path success rate: successful ÷ (successful + failed) |
| `conservative_success_probability`, `standard_error` | share | Conservative success rate (unresolved paths count as non-successes) and its SE over all paths |
| `unresolved_fraction` | share | Unresolved paths ÷ all paths |
| `required_annual_return` | annual effective rate (0.04 = 4 %) | Lowest fixed return meeting the target at this budget, rounded **up** to 1e-6. Empty if there's no solution in −50 % … +50 % |
| `return_tolerance`, `converged`, `iterations`, `note` | rate, true/false, count, text | Search precision (0.0001), convergence, engine runs, and the reason for any no-solution or lower-bound row |

Running `run` twice on the same config and seed gives byte-identical CSVs. Only `created_at` in
`run_metadata.json` differs.

There is no `probability_funded` column, because SPEC §12 calls that name ambiguous. Use
`probability_not_depleted_yet` or `estimated_lifetime_success_rate`.

## Portfolio import (account exports → ledger)

`sbretire portfolio import` reads the household's account transaction exports into one **Ledger**,
`output/portfolio/ledger.csv`. It is separate from the retirement model and reads nothing from the scenario.

1. Copy `config/accounts.example.yaml` to `config/accounts.yaml` (git-ignored) and list each account: `id`,
   `name`, `provider` (`schwab`, `hl`, `vanguard` or `ii`), `owner` (a person id from your model config),
   `wrapper` (`taxable`, `isa`, `pension` or `sipp`), `currency`, and file-name patterns for its `transactions`
   and `holdings` exports. For one export holding several accounts, `filter` keeps the rows whose `Account`
   column equals it.
2. Each month, save every provider's year-to-date export into a folder named `<mon>-<yy>` under
   `data/transactions/` (git-ignored), e.g. `data/transactions/oct-26/`. Keep earlier folders; overlapping rows
   are merged once (the newest folder's copy wins).
3. Run:

```bash
uv run sbretire portfolio import
```

Options: `--root` (default `data/transactions`), `--accounts` (default `config/accounts.yaml`), `--output-dir`
(default `output`). For each account it prints the rows, date range, counts by type, External Flows in and out
(native currency), and whether the cash agrees with the export's running balance (Vanguard and ii state one).

- Exit 0: imported and reconciled. Exit 1: an unreadable file, or a cash break (the ledger is still written so you
  can look). Exit 2: an invalid accounts file, or a transaction the importer does not know, named by folder, file
  and row; nothing is guessed. Add it to that provider's map in
  `src/sbretire/ledger/parsers/`.
- Rows keep their own currency (Schwab in USD). Columns, signs and flows: `docs/decisions/portfolio-data.md` §4.

### Valuing the holdings: `starting_balance`

Each month, also save every account's holdings (positions) export into the same `<mon>-<yy>` folder; the
`holdings` patterns in `config/accounts.yaml` find them. For Vanguard's one holdings file covering both wrappers,
`holdings_filter` (`Stocks & Shares ISA` or `Personal Pension`) gives each account its own rows. Then:

```bash
uv run sbretire portfolio value --usd-gbp 0.7450
```

- It values the **newest** month folder only. `--usd-gbp` is GBP per US dollar and is required while any account
  is in USD; HL's export states its own rate (printed for comparison, with a warning if yours differs by more than
  2%).
- Each account is valued at its export's own date; ii's file has no date, so it takes the newest date the other
  exports state and is shown "(assumed)". A warning appears if the dates span more than 7 days.
- Cash is included: Schwab's cash line, HL's "Total cash", Vanguard's "GBP Cash" rows, and for ii the latest
  running balance in its transactions export.
- Each export is checked against its own totals (Schwab "Positions Total"; HL "Stock value", the Totals row and
  "Total value"); a mismatch stops with exit 2.
- It prints a table by account, totals by person and for the household, and the line to paste into
  `config/model.yaml` (it never edits the file):

```yaml
portfolio:
  starting_balance: 1234567  # sbretire portfolio value: oct-26, 2026-10-17 to 2026-10-18
```

  It also writes `output/portfolio/holdings.csv`: one row per holding or cash line with its value in the account's
  currency, the rate used and the GBP value. Exit 0: valued; 1: a file cannot be read; 2: a missing export, a
  missing `--usd-gbp`, or totals that do not add up.

### Price history and monthly returns

Performance and the efficient frontier need each holding's price history, which you download yourself (runs never
go online):

1. For each security, download its history into `data/prices/` (git-ignored). Yahoo Finance → the security →
   **Historical data** → frequency **Monthly** (or daily) → **Download** gives `Date,Open,High,Low,Close,Adj Close,
   Volume`; its `Adj Close` already includes dividends. London listings end in `.L` (often priced in pence, GBX).
   Download **GBP=X** as well: pounds per US dollar. For a fund Yahoo does not cover (Vanguard's own funds),
   type a file with `Date,Close` and, for income units, a `Dividend` column (cash per unit paid on that date).
2. Copy `config/securities.example.yaml` to `data/prices/securities.yaml` and list one series per security:
   `id`, `name`, `file`, `quote` (`GBP`, `GBX` or `USD`) and `holdings` as `<account id>:<security key>`. The
   keys are the `account` and `security_key` columns of `output/portfolio/holdings.csv`; one series can price
   the same ETF in several accounts.
3. Run:

```bash
uv run sbretire portfolio returns
```

It works out the last `--months` (default 60) monthly total returns in GBP, ending with the month before the
newest export folder (`oct-26` → October 2021 to September 2026), and prints a coverage report:

- **full**: a return for every month; **short**: history starts later (its first month is shown);
  **gaps**: months missing inside the history; **missing**: no price file, or the holding is in no series.
- **share**: each line's share of the invested (non-cash) value of the newest holdings, so you can see what the
  gaps affect. USD converts at the GBP=X file's latest month-end, or `--usd-gbp`.
- **basis**: `adjusted` (Adj Close), `dividends` (Close plus the Dividend column) or `price` (Close only: may
  understate the return of income units).

Missing files never stop it (exit 0); add them a few at a time. It writes `output/portfolio/returns.csv`
(`month`, `series`, `value_gbp`, `dividend_gbp`, `return_gbp`, `basis`) and `returns_metadata.json` (the window
and each price file's SHA-256 and dates). Exit 2: an invalid `securities.yaml` (with the YAML location) or a
price file without a `Date` and `Close`/`Adj Close` column.

### Performance and drawdown of today's mix

Add the risk-free rate (UK Bank Rate, as a fraction) to the top of `data/prices/securities.yaml`:

```yaml
risk_free_rate: 0.04
```

then run:

```bash
uv run sbretire portfolio performance
```

It applies **today's weights** (each series' share of today's value, plus cash) to the last `--months` (default 60)
monthly returns: a back-test of the current mix, **not a forecast or advice**. Each month uses the series that
have a return that month, rescaled with the cash to 100%; cash earns the risk-free rate, and the report says how
much of today's value each month covered. It prints:

- **annual return** (the months compounded), **annual volatility** (monthly standard deviation × √12) and the
  **Sharpe ratio** (annual excess return over the risk-free rate ÷ volatility);
- the **maximum drawdown**: the largest fall from a previous high, with the months it peaked, bottomed and
  recovered;
- the same figures for each price series (volatility and Sharpe only with at least 12 months).

`--risk-free 0.045` overrides the file for one run; with neither it stops (exit 2). It writes
`output/portfolio/performance.csv` (`month`, `portfolio_return`, `wealth_index`, `drawdown`, `covered_share`,
`rolling_12m_return`, `rolling_12m_volatility`) and `performance_series.csv` (`series`, `name`, `weight`, `months`,
`annual_return`, `annual_volatility`, `sharpe`, `max_drawdown`). Until price files exist the back-test is all cash.

### Look-through: sectors, regions and currencies

`sbretire portfolio exposure` shows what today's money is invested in, looking through funds to what they hold:
asset class, sector, region and currency, each in GBP and as a share of the household total, plus the largest
underlying holdings across all funds and stocks.

- **Funds:** for each fund or ETF, copy `config/factsheet.example.yaml` to `data/factsheets/<file>.yaml`
  (git-ignored), fill in the weights from the fund's latest published factsheet (percentages or fractions of the
  whole fund) and add `factsheet: <file>.yaml` to its series in `data/prices/securities.yaml`. Leave out what the
  factsheet does not give; `top_holdings` are optional.
- **Single stocks:** add `sector:` and `region:` to the stock's series (optionally `asset_class:`, default equity,
  and `currency:`, default from the region).
- **Names** come from fixed lists, so different factsheets line up: the 11 GICS sectors or Other; regions UK,
  North America, Europe ex UK, Japan, Asia Pacific ex Japan, Emerging Markets, Other; asset classes equity, bond,
  cash, property, other; currencies GBP, USD, EUR, JPY, Other. Common wording such as "Technology",
  "Healthcare", "United States" or "Fixed Income" is accepted; any other name stops the command (exit 2) with
  the file and the line.

```bash
uv run sbretire portfolio exposure
```

Cash is shown as its own line. Anything without data is **Unclassified**, so every table adds to 100%. A fund's
currencies come from its factsheet, or else from its regions (UK → GBP, North America → USD, Europe ex UK → EUR,
Japan → JPY), and the share taken from regions is shown. A factsheet more than a year older than the valuation
gets a warning. It writes `output/portfolio/exposure.csv` (`dimension`, `label`, `value_gbp`, `share`; the top
holdings come last as `top_holding`).

### Efficient frontier and re-weighting (analysis, not advice)

```bash
uv run sbretire portfolio frontier
```

It works on the **priced sleeve**: the series with a return in every month of the window. Cash and every other
holding stay as they are today. Then it:

- estimates each series' return (12 × the mean monthly return) and risk (a Ledoit–Wolf shrunk covariance, which is
  steadier than the raw estimate with this much data; `--covariance sample` for the raw one);
- draws the long-only frontier with each series capped at `max_weight` (in `securities.yaml`, default 0.25;
  `--max-weight` overrides);
- shows today's mix, the minimum-variance and maximum-Sharpe mixes, and the **target**: the mix with today's risk
  and the highest past return (`--target max-sharpe` or `min-variance` instead);
- lists the trades:
  - **within each account**: re-splitting the money already there across the series it holds, so it can be done
    without moving money between wrappers;
  - **for the household as one portfolio**: analysis only, as this would need moves between pension, ISA and
    taxable accounts.
- estimates each trade's cost from `trading: {fee_per_trade, cost_rate}` on the account in `accounts.yaml`;
  trades under `--min-trade` (default 50 GBP) are skipped;
- re-estimates the target on each half of the window and reports the **turnover** between the two. A high
  turnover means the "better" mix depends heavily on which years you look at.

It needs the risk-free rate (as `portfolio performance`) and at least two fully priced series (exit 2
otherwise). It writes:

- `output/portfolio/frontier.csv`: 21 frontier points, then today's mix, minimum variance, maximum Sharpe, the
  target and the within-account mix;
- `frontier_weights.csv`;
- `trades.csv`: `scope`, `account`, `series`, `current_gbp`, `target_gbp`, `trade_gbp`, `cost_gbp`.

These are calculations from past prices under the stated assumptions, not a recommendation to trade.

## Development

**VS Code:** open the `C:\sb\SBRetire` folder and accept the recommended extensions (Python, Ruff, Mypy). The
committed `.vscode/settings.json` selects `.venv` and enables pytest. Tests then appear in the **Testing** panel,
where you can run or debug them one at a time. If they don't appear: run `uv sync`, then use **Python: Select
Interpreter → .venv** and **Testing → Refresh Tests**. `launch.json` also has debug configurations for
`sbretire run`.

```bash
uv run python scripts/check.py          # full gate: ruff, format, mypy --strict, pytest
uv run python scripts/check.py --fast   # skip slow tests
uv run python scripts/check.py --fix    # auto-fix lint + format first
```

Work is tracked in plain markdown: [docs/epics/roadmap.md](docs/epics/roadmap.md) lists features, and each
feature's design brief in `docs/backlog/` holds its tasks (`uv run python scripts/backlog_check.py --next`
shows what's next; format in [docs/project-sdlc.md](docs/project-sdlc.md)). Design decisions live in
`docs/decisions/` (topic-grouped decision records) and the
domain glossary in [docs/THESAURUS.md](docs/THESAURUS.md).

## Data

Mortality and inflation inputs are local files under `data/` with provenance recorded in
[data/README.md](data/README.md). The model never downloads data during a run.

## Assumptions

The model rests on these choices (details in `docs/decisions/`):

- **Returns:** one fixed nominal annual return, after fees, earned every year. There is no market volatility or
  sequence-of-returns risk.
- **Inflation:** an AR(1) lognormal process calibrated to ONS CPI from 1989 to 2025, with high-inflation years
  clustering. Spending and every inflation-linked income follow the same simulated UK CPI path.
- **Mortality:** ONS 2024-based UK cohort rates (principal projection), spread evenly over the months of each year
  of age. Above age 100 the age-100 rate is held. The two people's lifetimes are independent.
- **Money flows each month in a fixed order:** the return on the opening balance, then income, then spending. The
  money runs out the first time it can't cover a month's spending, and then stays at zero.
- **Success** means the money paid every month's spending until both people had died. Paths that reach the horizon
  with someone alive are unresolved, and the conservative rate never counts them as successes.

## Limitations

- **No tax.** Every figure is pre-tax (SPEC §16). Spending, income and returns should be entered on a basis you
  have thought through.
- **No market risk.** The fixed return hides crashes and sequence risk. Use the required-return table, and lower
  `annual_return` values, to stress-test.
- **Foreign income** (e.g. US Social Security) is converted at a fixed planning exchange rate and linked to UK CPI
  rather than its own cost-of-living adjustment. There is no exchange-rate risk.
- **Not covered:** housing, long-term care, fees beyond those in the return, one-off expenses, and more than two
  people. A one-off lump sum can be approximated as a one-month income stream.
- **Parameter uncertainty is not modelled.** Results are only as good as your inputs: State Pension forecasts,
  pension survivor terms, budget, return and data. The `+/-` figures measure simulation noise only.
- **It is not financial advice** and not a forecast or guarantee of future solvency.
