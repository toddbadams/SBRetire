---
id: F-006
type: feature
parent: stochastic-inputs
status: in-progress
complexity: 6
created: 2026-10-09
updated: 2026-10-09
---
# F-006 Stochastic Inflation Process and CPI Calibration

## 1. Purpose

Replace placeholder inflation with one precisely defined stochastic process (SPEC §6): an AR(1) process in
log(1 + π) with explicit log-space parameters, one annual rate per **Path** per simulated year, drawn from the
inflation **Random Stream** (F-005), compounding monthly into the **Inflation Index** I_t that income and spending
already read through the `PriceIndex` seam. Parameters are calibrated from a local, versioned UK CPI file whose
provenance is recorded (SPEC §4.2 Inflation, §19) and whose hash goes into Run Metadata (SPEC §10.3).

Resolves SPEC §18 "Exact inflation stochastic process and calibration dataset" (data-and-calibration §2) and
"Whether any income is indexed to a measure other than CPI" (data-and-calibration §3); replaces the provisional
simulation-conventions §3 with §5. Makes passable SPEC §17.1 "Zero inflation keeps the price index constant" and
§17.2 "A deterministic inflation fixture produces expected nominal spending".

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Calibration data | ONS MM23 series **D7G7** "CPI annual rate 00: all items 2015=100" (release 2026-09-16, retrieved 2026-10-09), annual values 1989–2025; **D7BT** (CPI index) kept as a cross-check. Raw CSVs in `data/raw/` unmodified; `scripts/build_uk_cpi.py` → `data/uk_cpi.csv` (`year,annual_rate`, decimal) + `data/uk_cpi.meta.json` | Official UK CPI; the config already names `UK_CPI 1989-2025`; annual-average rates match annual draws | SPEC §4.2, §19 |
| 2 | Process | **AR(1) lognormal**: x_y = log(1 + π_y); x_y = μ + φ (x_{y−1} − μ) + σ ε_y, ε ~ N(0, 1) iid. 1 + π = exp(x) > 0 always | UK inflation is persistent (φ ≈ 0.62); with a fixed nominal portfolio return, runs of high inflation are the main inflation risk and iid draws would halve long-run price-level dispersion | Interview Q1; data-and-calibration §2 |
| 3 | Parameter meaning | All parameters are **log-space** (`parameter_units: log_annual`): `log_mean` μ, `ar1_coefficient` φ ∈ (−1, 1), `innovation_sd` σ ≥ 0. Implied median rate e^μ − 1; stationary log SD σ/√(1−φ²) — documented, never silently converted from arithmetic moments | SPEC §6 forbids silently equating arithmetic moments with lognormal parameters | SPEC §6 |
| 4 | Estimator | μ = mean of x over the calibration years; φ = Σ(x_{t−1}−μ)(x_t−μ) / Σ(x_{t−1}−μ)²; σ = √(Σ e² / (m − 2)) over the m = n − 1 residuals e_t = (x_t−μ) − φ(x_{t−1}−μ) (two fitted parameters). 1989–2025 → μ 0.027742, φ 0.617897, σ 0.015365 (stationary SD 0.01954, median rate 2.81 %) | Simple, reproducible, documented | Brief author |
| 5 | Start state | x_{−1} = log(1 + `initial_rate`); `initial_rate` defaults in the example to the last observed year (2025: 0.034) | Year 1 reflects current conditions, reverting at ≈ 38 %/yr | Interview Q2 |
| 6 | Config | `inflation: {source, source_period "YYYY-YYYY", data_file, model: ar1_lognormal, parameter_units: log_annual, log_mean, ar1_coefficient, innovation_sd, initial_rate}`; `annual_mean` / `annual_standard_deviation` removed. `scripts/calibrate_inflation.py` prints the calibrated block | Explicit, editable for stress tests; one source of truth per run | Interview Q3 |
| 7 | Within-year timing | Simulated years run from the As-Of month. I_0 = 1; for 12k ≤ t ≤ 12(k+1): I_t = I_{12k} · (1 + π_k)^((t − 12k)/12). At anniversaries I_{12k} = ∏_{j<k}(1 + π_j) = SPEC's I_y | SPEC §6 "apply it to each of the twelve monthly steps"; replaces the provisional annual step | Interview Q4; simulation-conventions §5 |
| 8 | Non-CPI indexing | None in V1: every `inflation_linked` stream follows the single simulated UK CPI path (US Social Security COLA and FX approximated by it); a per-stream `escalation_rule` is a possible later feature | Keeps one index; a COLA alone would be unrealistic without FX | Interview Q5; data-and-calibration §3 |
| 9 | Randomness / CRN | Draw ε as `rng.standard_normal((n_years, n_paths))` from `RandomStreams.inflation`, year-major, once per run; rates materialised and reused across candidates | CRN (simulation-conventions §4); year-major means a shorter horizon reuses the same early-year draws | SPEC §10.3 |
| 10 | Memory | Store log growth g = x (n_years, n_paths) and cumulative log level L (n_years + 1, n_paths), float64 — 100k paths × 60 y ≈ 96 MB; `level(t)` computed on demand | SPEC §10.4 | SPEC §10.4 |
| 11 | Preview | Deterministic preview uses the same compounding index with every π = e^μ − 1 (median rate); `AnnualStepPriceIndex` removed | One timing convention everywhere | simulation-conventions §5 |
| 12 | Placement | `sbretire/inflation.py` (params, fit, draws, `StochasticPriceIndex`, `build_price_index`); `scripts/build_uk_cpi.py`, `scripts/calibrate_inflation.py` | SPEC §3 | SPEC §3 |

## 3. Context

- `PriceIndex` protocol (`level(month) -> (n_paths,)`), `FlatPriceIndex`, `AnnualStepPriceIndex` (F-003/F-015);
  `ScenarioIncome`/`ScenarioSpending`/`ScenarioCashFlows` read the index; preview builds an `AnnualStepPriceIndex`
  from `inflation.annual_mean`.
- `InflationAssumptions(source, source_period, annual_mean, annual_standard_deviation, model, parameter_units)` (F-001).
- `RandomStreams.inflation` (F-005); `DataFileRecord` / `file_sha256` (F-005); mortality sidecar pattern (F-007).
- Raw data inspected 2026-10-09: D7G7 annual 1989–2025 (37 values, 0.0 %–9.1 %); D7BT annual 1988–2025; D7G7 vs
  D7BT-derived annual change differ by ≤ 0.1 pp (index rounding).
- Breaking config change: `config/model.example.yaml`, test fixtures and the user's git-ignored `config/model.yaml`
  must move to the new keys.

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `data/raw/ons_cpi_d7g7.csv`, `data/raw/ons_cpi_d7bt.csv` | Exact ONS downloads (committed with this brief) |
| `scripts/build_uk_cpi.py` | Raw → `data/uk_cpi.csv` + `data/uk_cpi.meta.json` |
| `scripts/calibrate_inflation.py` | Prints the calibrated YAML block |
| `tests/tooling/test_build_uk_cpi.py`, `tests/unit/test_inflation_process.py`, `tests/integration/test_inflation_end_to_end.py` | Tests |

**Modified**

| File | Change |
|---|---|
| `src/sbretire/config.py` | `InflationAssumptions` new schema; `inflation.data_file` resolved / required-file check |
| `src/sbretire/inflation.py` | `Ar1LognormalParams`, `fit_ar1_lognormal`, `draw_annual_rates`, `StochasticPriceIndex`, `build_price_index`, `load_cpi_series`; remove `AnnualStepPriceIndex` |
| `src/sbretire/preview.py`, `src/sbretire/__main__.py` | Preview index; validate data-file checks |
| `config/model.example.yaml`, `tests/fixtures/scenarios/*.yaml`, test helpers | New inflation keys |
| `tests/unit/test_inflation.py`, `test_preview.py`, `test_cli_preview.py`, config tests | Updated for the new schema and timing |
| `data/README.md`, `README.md`, `docs/THESAURUS.md` | Provenance, config docs, Inflation Index wording |

## 5. Interfaces

```python
# sbretire/inflation.py
@dataclass(frozen=True)
class Ar1LognormalParams:
    log_mean: float  # μ, log(1 + annual rate)
    ar1_coefficient: float  # φ, -1 < φ < 1
    innovation_sd: float  # σ >= 0
    initial_rate: float  # π_{-1}, annual rate (> -1)


def fit_ar1_lognormal(
    annual_rates: Sequence[float], initial_rate: float | None = None
) -> Ar1LognormalParams: ...
def draw_annual_rates(
    rng: np.random.Generator, params: Ar1LognormalParams, n_paths: int, n_years: int
) -> NDArray[np.float64]: ...  # (n_years, n_paths) annual rates π


class StochasticPriceIndex:  # PriceIndex
    def __init__(self, annual_rates: NDArray[np.float64]) -> None: ...  # (n_years, n_paths), each > -1
    @classmethod
    def constant(cls, n_paths: int, n_years: int, annual_rate: float) -> StochasticPriceIndex: ...
    def level(self, month: int) -> FloatArray: ...  # 0 <= month <= 12 * n_years


def build_price_index(scenario: Scenario, rng: np.random.Generator, n_paths: int) -> StochasticPriceIndex: ...
def load_cpi_series(path: Path) -> dict[int, float]: ...  # year -> annual rate (decimal)
```

`data/uk_cpi.csv`: `year,annual_rate` (decimal, e.g. `2022,0.091`). Sidecar keys: `source` (`UK_CPI`), `series`
(`D7G7`), `dataset` (`MM23`), `release_date`, `retrieved`, `source_url`, `raw_file`, `raw_sha256`, `units`
(`annual_rate_decimal`), `edition`.

Config:

```yaml
inflation:
  source: UK_CPI
  source_period: "1989-2025"
  data_file: ../data/uk_cpi.csv
  model: ar1_lognormal
  parameter_units: log_annual  # parameters of log(1 + annual rate)
  log_mean: 0.0277
  ar1_coefficient: 0.6179
  innovation_sd: 0.0154
  initial_rate: 0.034  # last observed year (2025)
```

## 6. Plan of Work

1. CPI build script, processed file, provenance.
2. AR(1) fit, calibration script, new config schema; migrate configs/fixtures.
3. Draws and `StochasticPriceIndex`.
4. `build_price_index`, preview switch, metadata record, validate checks, end-to-end test, docs and decisions.

## 7. Validation

- **T1**: unit tests; ruff; mypy.
- **T2**: seeded end-to-end — deterministic inflation fixture (σ = 0) through `ScenarioCashFlows` gives hand-computed
  nominal spending; seed-42 known answer for draws.
- **T3**: statistical — 100k paths × 60 years: sample μ, φ, σ of the drawn log rates within tolerance of the
  parameters (seeded, `@pytest.mark.slow` if > 2 s).

## 8. Decision Log

- 2026-10-09 — AR(1) lognormal process, log-space parameters (Interview Q1; data-and-calibration §2).
- 2026-10-09 — Start from the last observed rate via `initial_rate` (Interview Q2).
- 2026-10-09 — Explicit parameters in YAML + calibration script; old keys removed (Interview Q3).
- 2026-10-09 — Monthly compounding within As-Of-anchored years; replaces provisional simulation-conventions §3
  (Interview Q4; simulation-conventions §5).
- 2026-10-09 — No non-CPI indexing in V1 (Interview Q5; data-and-calibration §3).
- 2026-10-09 — F-006.2 AC for the fit reworded (see §9): exact on a hand-computed series, tolerance on a long synthetic one.

## 9. Surprises

- 2026-10-09 — F-006.2: an AR(1) path with σ = 0 decays towards μ, so its sample mean is not μ and the fit cannot "recover μ and φ exactly" from it; the AC now uses a hand-computed short series (exact) plus a long seeded synthetic series (tolerance).
- 2026-10-09 — F-006.2: the brief's σ formula said n − 2 (n = observations) while its pinned value 0.015365 used m − 2 over the m = n − 1 residuals (34 for 1989–2025). The pinned value and example config were right; formula text, code and the hand-computed test now all use m − 2.
- 2026-10-09 — F-006.2: `inflation.data_file` resolves to an absolute path and leaked into the Config Hash; it is now excluded like `mortality.data_file` (configuration §7 amended).

## 10. Tasks

### F-006.1 CPI data build and provenance
- **Status**: Verification
- **Depends on**: —

`scripts/build_uk_cpi.py`: read `data/raw/ons_cpi_d7g7.csv` (annual `"YYYY","r.r"` rows), write
`data/uk_cpi.csv` and `data/uk_cpi.meta.json` (§5); cross-check each year against the D7BT annual index; fill
`data/README.md`. Tests in `tests/tooling/test_build_uk_cpi.py`.

**Acceptance criteria**
- [x] Rebuilding into a temp dir reproduces the committed CSV and sidecar byte-for-byte — `test_build_uk_cpi_reproduces_committed_files`
- [x] Known values: 1989 = 0.052, 2015 = 0.0, 2022 = 0.091, 2025 = 0.034; years 1989–2025 contiguous, header `year,annual_rate` — `test_uk_cpi_known_values`
- [x] Every D7G7 rate is within 0.0015 of the D7BT annual-average index change for that year — `test_uk_cpi_agrees_with_index`
- [x] `data/README.md` and the sidecar record both raw SHA-256s, the series, release and retrieval dates — `check: grep ff87e9f1cc2412d1688a35b21c67243be6902b463ccbd9df19387109978fdcae data/README.md data/uk_cpi.meta.json`

**Notes**
- 2026-10-09 Added `scripts/build_uk_cpi.py` (CDID checks, contiguous years, Decimal % → decimal, D7BT cross-check ≤ 0.0015 else fail); built and committed `data/uk_cpi.csv` (1989–2025) and `data/uk_cpi.meta.json`; `data/README.md` rows + Inflation section. Tests `tests/tooling/test_build_uk_cpi.py` (4, incl. sidecar provenance).

### F-006.2 AR(1) calibration and inflation config schema
- **Status**: Verification
- **Depends on**: F-006.1

`fit_ar1_lognormal` and `load_cpi_series` in `src/sbretire/inflation.py`; `scripts/calibrate_inflation.py`; new
`InflationAssumptions` (§2 #3, #6) with `data_file` resolved like `mortality.data_file`; migrate
`config/model.example.yaml`, fixtures and tests.

**Acceptance criteria**
- [x] A short hand-computed series gives exactly the §2 #4 formulas; a long seeded synthetic AR(1) series is recovered within tolerance; on real data the fit gives μ 0.027742, φ 0.617897, σ 0.015365 (to 6 dp) and `initial_rate` = the last year's rate — `test_fit_ar1_lognormal_known_answers`
- [x] `config/model.example.yaml` inflation parameters equal the calibration of its `source_period` from its `data_file`, rounded to 4 dp — `test_example_config_matches_calibration`
- [x] Invalid inflation config is rejected with its YAML location: `ar1_coefficient` ±1 or beyond, negative `innovation_sd`, `initial_rate` ≤ −1, `model`/`parameter_units` other than `ar1_lognormal`/`log_annual`, malformed `source_period`, and the removed `annual_mean` key — `test_inflation_config_rejects_invalid_values`
- [x] `scripts/calibrate_inflation.py --config config/model.example.yaml` prints a YAML block whose values match the fit — `test_calibrate_inflation_script_prints_block`

**Notes**
- 2026-10-09 `InflationAssumptions` reshaped (`source_period` YYYY-YYYY with `first_year`/`last_year`, `data_file` resolved like mortality and checked by `--require-data-files`, `model: ar1_lognormal`, `parameter_units: log_annual`, `log_mean`, `ar1_coefficient` ∈ (−1, 1), `innovation_sd` ≥ 0, `initial_rate` > −1; old keys now unknown). `Ar1LognormalParams`, `fit_ar1_lognormal`, `load_cpi_series`, `calibrate_inflation` in `src/sbretire/inflation.py`; `scripts/calibrate_inflation.py` prints the block (incl. relative `data_file`). Config Hash excludes `inflation.data_file`. Migrated example config, fixture, preview (constant median rate e^μ − 1, still annual step until F-006.4) and tests (config fields/loading, preview, mortality CLI). Personal `config/model.yaml` migrated locally (git-ignored) and validates. Tests: `tests/unit/test_inflation_calibration.py` (4), `tests/tooling/test_calibrate_inflation.py` (1), +14 config cases.

### F-006.3 AR(1) draws and StochasticPriceIndex
- **Status**: Verification
- **Depends on**: F-006.2

`draw_annual_rates` and `StochasticPriceIndex` (§2 #2, #7, #9, #10) in `src/sbretire/inflation.py`. Tests in
`tests/unit/test_inflation_process.py`.

**Acceptance criteria**
- [x] Zero inflation (μ = 0, σ = 0, `initial_rate` 0) gives I_t = 1 for every month and path — `test_stochastic_price_index_zero_inflation_constant`
- [x] At each anniversary I_{12k} equals ∏_{j<k}(1 + π_j) per path; within year k, I_t = I_{12k}(1 + π_k)^((t−12k)/12); month 0 is 1 — `test_stochastic_price_index_monthly_compounding`
- [x] For any parameters (hypothesis), every drawn 1 + π > 0 and every I_t > 0 and finite — `test_draw_annual_rates_positive_growth`
- [x] Seed 42 (inflation stream) gives pinned first-year rates for 3 paths; a 10-year draw equals the first 10 years of a 60-year draw — `test_draw_annual_rates_seed_42_known_answer_and_prefix`
- [x] With σ = 0 the rates follow π_y = exp(μ + φ^{y+1}(x_{−1} − μ)) − 1 exactly — `test_draw_annual_rates_deterministic_path`
- [x] 100,000 paths × 60 years (seed 7): the sample mean of x, lag-1 regression φ and residual SD are within 0.001, 0.01 and 0.0005 of μ, φ, σ — `test_draw_annual_rates_statistics_match_parameters`
- [x] `level` rejects months outside 0…12·n_years and rate arrays with any π ≤ −1 — `test_stochastic_price_index_rejects_bad_input`

**Notes**
- 2026-10-09 Added `draw_annual_rates` (one `standard_normal((n_years, n_paths))` call, year recursion vectorised over paths, returns π = expm1(x)) and `StochasticPriceIndex` (validates 2-D/finite/> −1; stores log growth + cumulative log level; `level` interpolates within the year; `constant`, `n_years`) in `src/sbretire/inflation.py`. Tests `tests/unit/test_inflation_process.py` (7; seed-42 known answers computed independently from `SeedSequence(42, spawn_key=(1,))`; 100k × 60 statistics run in < 1 s, so not marked slow).

### F-006.4 Wiring, preview, metadata and docs
- **Status**: To Do
- **Depends on**: F-006.3

`build_price_index(scenario, rng, n_paths)`; preview uses `StochasticPriceIndex.constant(…, e^μ − 1)`; remove
`AnnualStepPriceIndex` and update its tests; inflation `DataFileRecord` (sidecar version/retrieved); `validate
--require-data-files` loads `uk_cpi.csv` and checks `source_period` years are present; integration test; README,
data/README, THESAURUS; decisions already recorded with the brief.

**Acceptance criteria**
- [ ] `build_price_index` draws from the given generator: same seed → identical index; horizon from the scenario — `test_build_price_index_uses_inflation_stream`
- [ ] Deterministic inflation fixture (σ = 0, μ = log 1.03, φ = 0, initial 0.03) through `ScenarioCashFlows` gives hand-computed nominal spending in months 0, 6, 12 and 30 (§17.2) — `test_deterministic_inflation_fixture_expected_nominal_spending`
- [ ] Preview compounds monthly at the median rate; its year rows and CSV match hand-computed values for the fixture — `test_preview_uses_monthly_compounding`
- [ ] `inflation_data_file_record` gives role `inflation`, the CSV SHA-256, version `D7G7 (released 2026-09-16)` and retrieved `2026-10-09` — `test_inflation_data_file_record`
- [ ] `validate --require-data-files` exits 2 naming `inflation.source_period` when the file lacks a year in the period, 0 for the example — `test_cli_validate_reports_inflation_coverage`
- [ ] README documents the process, log-space parameters, calibration command and the UK-CPI-for-all-linked-income approximation — `check: grep -n "ar1_lognormal" README.md`

## 11. Open Questions

- A per-stream `escalation_rule` (fixed %, US COLA with FX) — later feature, not V1.
- Whether to model correlation between inflation and returns — out of V1 (fixed returns, SPEC §2).

## 12. Acceptance Criteria

1. Build reproduces committed files — `test_build_uk_cpi_reproduces_committed_files`
2. Known CPI values — `test_uk_cpi_known_values`
3. Agrees with index — `test_uk_cpi_agrees_with_index`
4. Provenance — `check: grep raw SHA-256 in data/README.md and the sidecar`
5. Fit known answers — `test_fit_ar1_lognormal_known_answers`
6. Example config matches calibration — `test_example_config_matches_calibration`
7. Invalid inflation config rejected — `test_inflation_config_rejects_invalid_values`
8. Calibration script — `test_calibrate_inflation_script_prints_block`
9. Zero inflation constant — `test_stochastic_price_index_zero_inflation_constant`
10. Monthly compounding — `test_stochastic_price_index_monthly_compounding`
11. Positive growth — `test_draw_annual_rates_positive_growth`
12. Seed 42 + prefix — `test_draw_annual_rates_seed_42_known_answer_and_prefix`
13. Deterministic path — `test_draw_annual_rates_deterministic_path`
14. Statistics — `test_draw_annual_rates_statistics_match_parameters`
15. Bad input rejected — `test_stochastic_price_index_rejects_bad_input`
16. Uses inflation stream — `test_build_price_index_uses_inflation_stream`
17. Deterministic fixture spending — `test_deterministic_inflation_fixture_expected_nominal_spending`
18. Preview compounding — `test_preview_uses_monthly_compounding`
19. Data-file record — `test_inflation_data_file_record`
20. Validate coverage — `test_cli_validate_reports_inflation_coverage`
21. README — `check: grep -n "ar1_lognormal" README.md`
