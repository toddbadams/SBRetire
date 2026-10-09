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
uv run sbretire --config config/model.yaml --output-dir output
```

`config/model.yaml` is git-ignored so personal inputs stay out of version control.

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
