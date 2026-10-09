---
id: F-009
type: feature
parent: simulation-engine
status: done
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-009 Monte Carlo Path Outcomes, Censoring and Success Metrics

## 1. Purpose

Turn the engine into the full Monte Carlo (SPEC §10) and answer the primary question for a fixed Budget (SPEC §1.1,
§11): draw every random input once from the seeded Random Streams (Death Months from F-008, inflation index from
F-006), run all Paths through `simulate_paths` (F-002) with the Scenario's cash flows (F-003/F-004), classify each Path
as **Successful**, **Failed** or **Unresolved (Censored)**, and report SPEC §11's metrics with Monte Carlo standard
errors. `sbretire run` prints the result and writes `run_metadata.json` (F-005).

Resolves SPEC §18 "Horizon-censoring policy and conservative sustainability denominator" (simulation-conventions §7).
Makes passable SPEC §17.1 "A fixed seed reproduces outputs" (end to end) and "Common random numbers are reused across
candidate budgets" (budget half; returns in F-011), and §17.2 "zero-spending scenario does not fail", "no starting
capital and no income fails when positive spending is due", "a sufficiently large portfolio with zero spending
remains solvent for all completed paths", "censored paths are reported and do not silently count as successes".

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Classification | **Failed** = depleted at any month (including while someone would have reached the horizon). **Successful** = never depleted and both died within the horizon. **Unresolved** = never depleted and someone alive at the horizon. **Completed** = Successful + Failed | Depletion is a known lifetime failure; only genuinely unknown outcomes are unresolved | Interview Q1; simulation-conventions §7 |
| 2 | Rates | Conservative Success Rate = N_success / N_all (the V1 target); Completed-Path Success Rate = N_success / N_completed, `None` when N_completed = 0. Unresolved share = N_unresolved / N_all always reported | SPEC §11; thesaurus | SPEC §11 |
| 3 | Standard errors | SE = √(p̂ (1 − p̂) / N) with N = the rate's own denominator, stated in output; `None` with its rate | SPEC §11 binomial SE | SPEC §11 |
| 4 | CRN shape | `draw_random_inputs(scenario, table, seed) -> RandomInputs(death_months, price_index, seed)` draws once from `RandomStreams.from_seed`; `run_monte_carlo(scenario, inputs)` never draws, so F-010/F-011 reuse one `RandomInputs` across candidates | SPEC §10.3; simulation-conventions §4 | simulation-conventions §4 |
| 5 | Run output | Console summary (ASCII) + `output/run_metadata.json` (seed, seed source, config hash, mortality + inflation `DataFileRecord`s); CSVs stay F-012/F-013 | Interview Q2 | Interview Q2 |
| 6 | Data files | `run` loads the scenario with `require_data_files=True`, loads/checks the mortality table and CPI coverage as `validate --require-data-files` does; any problem → exit 2 | SPEC §4.3 fail fast | F-006/F-007 |
| 7 | Memory | Only `PathOutcomes` per path (5 arrays) plus the inputs; no month × path history (F-012 adds what reporting needs) | SPEC §10.4 | SPEC §10.4 |
| 8 | Placement | `sbretire/metrics.py` (classification + metrics), `sbretire/monte_carlo.py` (inputs + run), `__main__.py` (`run`) | SPEC §3 | SPEC §3 |

## 3. Context

- `simulate_paths(...) -> PathOutcomes(depletion_month (−1 if never), shortfall, household_end_month (−1 if
  censored), censored (someone alive at horizon), final_balance)`.
- `ScenarioCashFlows(scenario, price_index, n_paths)`; `build_price_index(scenario, rng, n_paths)`;
  `sample_death_months(scenario, table, rng, n_paths)`; `RandomStreams.from_seed`, `resolve_seed`;
  `build_run_metadata`, `write_run_metadata`; `MortalityTable.data_file_record`, `inflation_data_file_record`.
- `sbretire run` currently validates then exits 1 "engine not implemented".
- The user's personal `config/model.yaml` (git-ignored) is the first real input; never print or commit its values
  outside the user's own terminal.

## 4. Touch-points

**New**: `src/sbretire/metrics.py`, `src/sbretire/monte_carlo.py`, `tests/unit/test_metrics.py`,
`tests/integration/test_monte_carlo.py`, `tests/unit/test_cli_run.py`.

**Modified**: `src/sbretire/__main__.py` (`run`), `tests/unit/test_cli.py` (the "engine pending" test is replaced),
`README.md`, `docs/THESAURUS.md` (Censored/Completed/Failed/Successful Path),
`docs/decisions/simulation-conventions.md` (§7, with this brief).

## 5. Interfaces

```python
# sbretire/metrics.py
class PathClass(IntEnum):
    SUCCESSFUL = 0
    FAILED = 1
    UNRESOLVED = 2


def classify_paths(outcomes: PathOutcomes) -> NDArray[np.int8]: ...  # (n_paths,) PathClass values


@dataclass(frozen=True)
class SuccessMetrics:
    n_paths: int
    n_successful: int
    n_failed: int
    n_unresolved: int
    n_completed: int
    conservative_success_rate: float  # n_successful / n_paths
    conservative_standard_error: float  # denominator n_paths
    completed_success_rate: float | None  # n_successful / n_completed
    completed_standard_error: float | None  # denominator n_completed
    unresolved_share: float  # n_unresolved / n_paths

    @classmethod
    def from_outcomes(cls, outcomes: PathOutcomes) -> SuccessMetrics: ...


# sbretire/monte_carlo.py
@dataclass(frozen=True)
class RandomInputs:
    seed: ResolvedSeed
    death_months: NDArray[np.int64]  # (2, n_paths)
    price_index: StochasticPriceIndex


def draw_random_inputs(scenario: Scenario, table: MortalityTable, seed: ResolvedSeed) -> RandomInputs: ...


@dataclass(frozen=True)
class MonteCarloResult:
    outcomes: PathOutcomes
    metrics: SuccessMetrics


def run_monte_carlo(scenario: Scenario, inputs: RandomInputs) -> MonteCarloResult: ...
```

CLI: `sbretire run --config PATH [--output-dir output]` → exit 0 with summary + `run_metadata.json`; exit 2 invalid
config/data; exit 1 unreadable config.

## 6. Plan of Work

1. Classification and metrics (pure, on `PathOutcomes`).
2. Random inputs + `run_monte_carlo`; SPEC §17.2 integration scenarios; seeded snapshot.
3. CLI `run`, metadata, docs, decision, timing.

## 7. Validation

- **T1**: unit tests for classification/metrics on hand-built `PathOutcomes`; ruff; mypy.
- **T2**: seeded end-to-end runs on the fixture (reproducibility, CRN, §17.2 scenarios).
- **T3**: regression snapshot of the example scenario's metrics at a pinned seed and path count; measured runtime for
  100k paths × 60 years.

## 8. Decision Log

- 2026-10-09 — Depleted paths are Failed even if someone would reach the horizon (Interview Q1; simulation-conventions
  §7).
- 2026-10-09 — `run` prints a summary and writes `run_metadata.json` in F-009 (Interview Q2).

## 9. Surprises

- 2026-10-09 — F-009.2: the example config at its own budget succeeds on all 2,000 paths (100-year horizon, nothing unresolved), which made a weak regression snapshot; the snapshot now uses budget 11,000 and a 30-year horizon so successful, failed and unresolved paths all occur (725 / 203 / 1,072), plus the total final balance.
- 2026-10-09 — F-009.3: SE printed to 2 dp showed '+/- 0.00%' for a 99.98 % rate over 100,000 paths (true SE ≈ 0.004 %); SEs now print to 3 dp.

## 10. Tasks

### F-009.1 Path classification and success metrics
- **Status**: Done
- **Depends on**: —

`PathClass`, `classify_paths`, `SuccessMetrics` in `src/sbretire/metrics.py` (§2 #1–#3). Tests in
`tests/unit/test_metrics.py` on hand-built `PathOutcomes`.

**Acceptance criteria**
- [x] Classification table: never depleted + both died → SUCCESSFUL; depleted + both died → FAILED; depleted + someone alive at the horizon → FAILED; never depleted + someone alive at the horizon → UNRESOLVED — `test_classify_paths_table`
- [x] A censored (unresolved) path is never counted as a success, and a set of only unresolved paths gives conservative rate 0 and completed rate `None` (§17.2) — `test_censored_paths_never_count_as_success`
- [x] Counts, both rates and both SEs match hand-computed values (e.g. 10 paths: 6 successful, 2 failed, 2 unresolved → 0.6 ± √(0.24/10), 0.75 ± √(0.1875/8), unresolved 0.2) — `test_success_metrics_hand_computed`

**Notes**
- 2026-10-09 Added `src/sbretire/metrics.py`: `PathClass`, `classify_paths` (depletion ≥ 0 → FAILED, else censored → UNRESOLVED, else SUCCESSFUL), `SuccessMetrics.from_outcomes` (bincount; conservative and completed rates with binomial SEs on their own denominators; None when nothing completed). Tests `tests/unit/test_metrics.py` (3). The red commit carried an unused variable flagged by ruff; removed here.
- 2026-10-09 /verify PASS:
  - metrics tests: 3 passed; concrete class lists, counts, rates and SEs
  - independent probe, 1,000 random outcomes: counts 523/295/182, both rates and SEs on their own denominators match; all 74 depleted+censored paths FAILED; empty completed → None
  - classification reads only depletion_month and censored (garbage in other fields changes nothing); ruff + mypy clean

### F-009.2 Random inputs and the Monte Carlo run
- **Status**: Done
- **Depends on**: F-009.1

`RandomInputs`, `draw_random_inputs`, `MonteCarloResult`, `run_monte_carlo` in `src/sbretire/monte_carlo.py`
(§2 #4, #7). Tests in `tests/integration/test_monte_carlo.py` on the fixture scenario + real data files.

**Acceptance criteria**
- [x] Same scenario and seed (pinned 7, 2,000 paths): two independent draw + run sequences give identical outcomes arrays and metrics (§17.1) — `test_monte_carlo_fixed_seed_reproduces_outputs`
- [x] One `RandomInputs` run with budgets 3,000 and 4,000: inputs are unchanged by the runs (death months and index levels identical before/after), and success never increases with the higher budget path by path (CRN, §17.1) — `test_monte_carlo_reuses_inputs_across_budgets`
- [x] Zero spending: no path fails; with a 10 M balance and zero spending every completed path is successful (§17.2) — `test_monte_carlo_zero_spending_never_fails`
- [x] Zero starting balance, no income, positive budget: every path fails in month 0 (§17.2) — `test_monte_carlo_no_capital_no_income_fails`
- [x] Example scenario, seed 42, 2,000 paths: metrics equal a pinned snapshot (regression) — `test_monte_carlo_example_snapshot`

**Notes**
- 2026-10-09 Added `src/sbretire/monte_carlo.py`: `RandomInputs` (seed, read-only death months, price index; `n_paths`), `draw_random_inputs` (`RandomStreams.from_seed` → `sample_death_months` + `build_price_index`, `simulation_count` paths), `MonteCarloResult`, `run_monte_carlo` (`ScenarioCashFlows` + `simulate_paths` + `SuccessMetrics`; never draws). Tests `tests/integration/test_monte_carlo.py` (5). Snapshot pinned after green from the code itself (regression, not an independent answer).
- 2026-10-09 /verify PASS:
  - Monte Carlo tests: 5 passed; snapshot is a regression pin with a mix of outcomes (725 / 203 / 1,072)
  - hand-wired streams → sample_death_months + build_price_index + simulate_paths gives identical outcomes to run_monte_carlo (seed 3, 500 paths)
  - CRN: budgets 2,000 / 3,000 / 5,000 on one RandomInputs — success monotone per path; death months read-only; run_monte_carlo makes no rng calls
  - plausibility: deaths by month 240 0.5982 vs 1 − S 0.5977 (z 0.15); median index at month 120 1.2875 vs 1.2895 expected; no month × path history; ruff + mypy clean

### F-009.3 `sbretire run`
- **Status**: Done
- **Depends on**: F-009.2

`run` in `src/sbretire/__main__.py` (§2 #5–#6); README "Running the model" and "Reading the results"; THESAURUS path
terms; decision §7 already recorded with the brief. Tests in `tests/unit/test_cli_run.py`.

**Acceptance criteria**
- [x] `run` on the fixture exits 0, prints ASCII lines with paths, successful/failed/unresolved counts, the conservative rate and completed-path rate each with SE and its denominator, the budget in today's GBP and the seed — `test_cli_run_prints_summary`
- [x] `run_metadata.json` is written to `--output-dir` with seed, seed source, config hash and two data-file records (mortality, inflation) with versions; with `random_seed: null` the seed is generated and flagged — `test_cli_run_writes_metadata`
- [x] Missing or invalid data files exit 2 with the issue location; nothing is written — `test_cli_run_rejects_bad_data`
- [x] The example config (100,000 paths × 100 years) completes; elapsed time recorded in Notes and under 120 s — `check: time uv run sbretire run --config config/model.example.yaml --output-dir <tmp>`
- [x] README documents running and reading the results (both rates, unresolved paths, SE, not a confidence interval) — `check: grep -n "Conservative" README.md`

**Notes**
- 2026-10-09 `sbretire run` implemented in `src/sbretire/__main__.py`: forces `require_data_files` (so the F-006/F-007 coverage checks run), loads the table, resolves the seed, draws once, runs, writes `run_metadata.json` with mortality + inflation records, prints `format_run_summary` (ASCII; rates to 2 dp, SEs to 3 dp so small SEs aren't shown as 0.00%). Tests `tests/unit/test_cli_run.py` (3); F-001's 'engine pending' check in `tests/unit/test_cli.py` replaced by `test_cli_run_rejects_invalid_config`. README 'Running the model' + 'Reading the results'; THESAURUS Censored/Completed/Depletion entries per §7. Timing: example config (100,000 paths, 100-year horizon) 3.4 s end to end; a 60-year-horizon personal config also 3.4 s (well under the 120 s budget).
- 2026-10-09 /verify PASS:
  - CLI tests: 12 passed
  - example run: exit 0 in 3.44 s, ASCII; metadata seed/source, config hash and both data-file sha256s and versions match
  - stress config (budget 11,000, 5,000 paths, 30 y): 1,838 / 471 / 2,691; conservative 36.76 % ± 0.682 % and completed 79.60 % ± 0.839 % match own recomputation; reruns identical apart from 'Wrote' line and created_at
  - missing data → exit 2, nothing written; null seed → generated, printed seed = metadata seed; README sections and THESAURUS match §7; full gate 322 passed

## 11. Open Questions

- Whether F-012's annual percentiles need per-month aggregates collected through the engine's observer (likely) —
  decided in F-012.

## 12. Acceptance Criteria

1. Classification table — `test_classify_paths_table`
2. Censored never success — `test_censored_paths_never_count_as_success`
3. Metrics hand-computed — `test_success_metrics_hand_computed`
4. Fixed seed reproduces — `test_monte_carlo_fixed_seed_reproduces_outputs`
5. CRN across budgets — `test_monte_carlo_reuses_inputs_across_budgets`
6. Zero spending never fails — `test_monte_carlo_zero_spending_never_fails`
7. No capital, no income fails — `test_monte_carlo_no_capital_no_income_fails`
8. Example snapshot — `test_monte_carlo_example_snapshot`
9. CLI summary — `test_cli_run_prints_summary`
10. CLI metadata — `test_cli_run_writes_metadata`
11. CLI bad data — `test_cli_run_rejects_bad_data`
12. Runtime — `check: time sbretire run on the example`
13. README — `check: grep -n "Conservative" README.md`
