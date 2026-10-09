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
exits 2; an unreadable file exits 1. Add `--require-data-files` to also check that `mortality.data_file` exists.

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

## Preview (deterministic illustration)

`sbretire preview --config config/model.yaml --death-ages 88,92` runs **one** household future and prints a
year-by-year table, then writes `output/preview.csv` (`--output-dir` to change). It is a **deterministic
illustration, not a sustainability estimate**: there is no randomness and no probability of success.

- `--death-ages A,B` — age at death for each person, in the config's `people` order; each person is dead from the
  start of the month of that birthday. Ages at or below someone's current age are rejected.
- Inflation is constant at `inflation.annual_mean`, stepping once a year on as-of anniversaries; the return is the
  fixed `portfolio.annual_return`.
- One row per calendar year (the first and last may be partial): `income`, `spending`, `investment_return`,
  `net_withdrawal` (spending − income) and `balance_end` in nominal GBP, `balance_end_today` deflated to today's
  GBP, and the `price_index`. In the month money runs out, `spending` shows what was needed; the unpaid part is the
  shortfall in the summary.

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
