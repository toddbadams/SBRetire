# SBRetire — Retirement Sustainability Model

Monte Carlo model that estimates the **maximum sustainable household spending** (in today's GBP)
for two people's joint remaining lifetimes, at a target probability of never running out of money.

The authoritative specification is [docs/SPEC.md](docs/SPEC.md). The model is for planning and
research only — it is **not financial advice**, does not forecast investment returns, and does not
guarantee future solvency.

> Status: project scaffold. The simulation engine is being built feature-by-feature from the
> spec; see [docs/epics/roadmap.md](docs/epics/roadmap.md) for the plan and progress.

## Install

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
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
`model.random_seed`, so the same seed, config and data give identical results. The run prints a summary and writes
`output/run_metadata.json`. 100,000 paths take a few seconds.

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
- Expect about 25 engine runs, under a minute for 100,000 paths.

These figures are model estimates from your assumptions (fixed return, no tax, simulated inflation and lifetimes).
They are not financial advice and not a guarantee.

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
| `annual_results.csv` | Year-by-year survival, spending, income and portfolio percentiles (SPEC §12) |
| `sustainability_results.csv` | Success probabilities and required-return search per budget/target (SPEC §13) |
| `lifestyle_results.csv` | Maximum sustainable budget per confidence level (SPEC §14) |
| `run_metadata.json` | Seed, version, config hash, data-file versions/hashes (SPEC §10.3) |

## Development

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

## Assumptions and limitations

See SPEC §2 (V1 boundaries). Notably excluded from V1: tax, stochastic returns, fees, housing,
long-term-care costs, and more than two people.
