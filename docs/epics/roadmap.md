# SBRetire V1 Roadmap

**Last updated**: 2026-10-09 — V1.1 enhancements planned (F-016 done).

Features in build order. Status: `proposed` → `briefed` → `in-progress` → `done` (or `superseded`). Briefs live in `docs/backlog/`; tasks are inside each brief.

| # | Feature | Epic | depends_on | Status |
|---|---|---|---|---|
| F-001 | Scenario Config Loading and Validation | [foundations](foundations.md) | — | done |
| F-002 | Deterministic Portfolio Engine (Walking Skeleton) | [simulation-engine](simulation-engine.md) | F-001 | done |
| F-003 | Income Streams | [household-cash-flows](household-cash-flows.md) | F-002 | done |
| F-004 | Spending with Survivor Budget Factor | [household-cash-flows](household-cash-flows.md) | F-002 | done |
| F-015 | Deterministic Preview Run | [reporting-release](reporting-release.md) | F-003, F-004 | done |
| F-016 | VS Code Test Setup | [v1-1-enhancements](v1-1-enhancements.md) | F-014 | done |
| F-017 | Inputs Display and inputs.csv | [v1-1-enhancements](v1-1-enhancements.md) | F-013 | done |
| F-018 | Results Guide (columns, calculations, assumptions) | [v1-1-enhancements](v1-1-enhancements.md) | F-017 | done |
| F-019 | End-of-Life Reserve Target | [v1-1-enhancements](v1-1-enhancements.md) | F-013 | done |
| F-020 | Spend-At-Least-Income Option | [v1-1-enhancements](v1-1-enhancements.md) | F-013 | in-progress |
| F-005 | Random Streams and Run Metadata | [foundations](foundations.md) | F-001 | done |
| F-006 | Stochastic Inflation Process and CPI Calibration | [stochastic-inputs](stochastic-inputs.md) | F-003, F-004, F-005 | done |
| F-007 | ONS Mortality Data Ingest and Mapping | [stochastic-inputs](stochastic-inputs.md) | F-001 | done |
| F-008 | Monthly Mortality Sampling | [stochastic-inputs](stochastic-inputs.md) | F-002, F-005, F-007 | done |
| F-009 | Monte Carlo Path Outcomes, Censoring and Success Metrics | [simulation-engine](simulation-engine.md) | F-006, F-008 | done |
| F-010 | Maximum Sustainable Budget Optimization | [analysis-optimization](analysis-optimization.md) | F-009 | done |
| F-011 | Return Search | [analysis-optimization](analysis-optimization.md) | F-010 | done |
| F-012 | Annual Results CSV | [reporting-release](reporting-release.md) | F-009 | done |
| F-013 | Sustainability and Lifestyle CSVs and End-to-End CLI | [reporting-release](reporting-release.md) | F-010, F-011, F-012 | done |
| F-014 | V1 Release: README, Acceptance and Reproducibility Sweep | [reporting-release](reporting-release.md) | F-013 | done |

**Parallel lanes**: after F-001, the F-007 mortality data work (highest data-availability risk) can proceed alongside F-002…F-005. F-012 can proceed alongside F-010/F-011.

## SPEC §18 decisions → owning feature

| §18 decision | Feature | Decision doc |
|---|---|---|
| Exact ONS file/table and age/period mapping | F-007 | `docs/decisions/data-and-calibration.md` |
| Valuation date and first simulated month | F-001 | `docs/decisions/simulation-conventions.md` |
| Exact inflation stochastic process and calibration dataset | F-006 | `docs/decisions/data-and-calibration.md` |
| Within-month cash-flow ordering and death timing | F-002 | `docs/decisions/simulation-conventions.md` |
| Behaviour of each income stream after recipient death | F-003 | `docs/decisions/configuration.md` |
| Treatment of household-level income and survivor benefits | F-003 | `docs/decisions/configuration.md` |
| Whether any income is indexed to a measure other than CPI | F-006 | `docs/decisions/data-and-calibration.md` |
| Horizon-censoring policy and conservative denominator | F-009 | `docs/decisions/simulation-conventions.md` |
| Budget and return optimization bounds and tolerances | F-010, F-011 | `docs/decisions/optimization.md` |
| Definition of annual portfolio percentiles and funded probabilities | F-012 | `docs/decisions/simulation-conventions.md` |
| (extra) Unknown-key strictness | F-001 | `docs/decisions/configuration.md` |
| (extra) Survivor budget factor precedence | F-004 | `docs/decisions/configuration.md` |
| (extra) Mortality tail beyond table coverage | F-007 | `docs/decisions/data-and-calibration.md` |

## SPEC coverage

| SPEC § | Requirement | Kind | Covered by |
|---|---|---|---|
| §1.1 | Maximum budget at target probability | capability | F-010 |
| §1.2 | Probability funded per year; portfolio distribution over time | capability | F-012 |
| §1.2 | Required return for a budget | capability | F-011 |
| §1.2 | Budget at 90/95/99% | capability | F-010, F-013 |
| §1.2 | "Confidence" = simulated proportion | constraint | THESAURUS; F-012/F-013 column naming |
| §2 | V1 inclusions / exclusions | constraint | CLAUDE.md hard constraints; checked in F-014 |
| §3 | Python, YAML, CSV, NumPy/pandas; module layout | constraint | Tooling decision tooling-and-process §1 (done) |
| §4 | All assumptions in YAML, none hard-coded | constraint | F-001; checked in F-014 |
| §4.1 | Precise inflation process selected and documented | decision | F-006 |
| §4.2 model | currency, simulation_count, confidence_levels, frequency, horizon_years, random_seed | capability | F-001 (seed=null recording: F-005) |
| §4.2 portfolio | starting_balance ≥ 0, annual_return > −100% | capability | F-001 |
| §4.2 budget | monthly_amount_today, survivor_budget_factor, precedence | capability / decision | F-001 (schema), F-004 (precedence) |
| §4.2 inflation | source, period, parameters, process, units, annual draws | capability | F-001 (schema), F-006 |
| §4.2 mortality | source, geography, projection, file, version/retrieval date, mapping | capability | F-001 (schema), F-007 |
| §4.2 people | id, name, DOB, sex category (no silent mapping), optional factor | capability | F-001 (schema), F-007 (sex-category match) |
| §4.2 income | fields; survivor % range; recipient death; household-level streams; end_date | capability / decision | F-001 (schema), F-003 |
| §4.3 | Fail-fast validation incl. data coverage/invalid values; strictness setting | capability | F-001; F-006 (inflation data); F-007 (mortality data) |
| §5 | Nominal internally; today's-GBP fields; monthly step; ordering; as_of_date; death timing; real reporting via same path | constraint / decision | F-001 (as_of), F-002 (ordering, timing), F-012 (real deflation) |
| §6 | Annual inflation draw held 12 months; I_y; 1+π > 0; S_t = B_m·I_t·F_t; linked income uses CPI path | capability | F-006, F-004, F-003 |
| §7.1 | ONS 2024-based cohort data; verified file/table/coverage | capability / decision | F-007 |
| §7.2 | Independent per-person sampling; q_m conversion; dead stays dead | capability | F-008 |
| §7.2 | Horizon is a cap; censored paths reported, not successes | capability / decision | F-009 |
| §8 | Income per month; start/end; recipient/survivor rules; linking; annual ÷ 12 | capability / decision | F-003 |
| §9 | r_m conversion; P_{t+1}; failure before spending; zero floor; shortfall | capability / decision | F-002 |
| §10.1–10.2 | Per-path process steps 1–10 | capability | F-002 (deterministic), F-009 (Monte Carlo) |
| §10.3 | Fixed seed reproducibility; metadata; separate streams; CRN | capability / constraint | F-005; CRN in F-010/F-011 |
| §10.4 | Memory-conscious aggregation | constraint | F-009, F-012 |
| §11 | Completed/success/failed/censored counts; both rates; conservative target; MC standard error | capability | F-009 |
| §12 | Annual rows and columns; percentile and funded-probability definitions | capability / decision | F-012 |
| §13 | Required-return search with bounds, tolerance, no-solution behaviour, monotonicity check | capability / decision | F-011 |
| §14 | Budget bisection; bounds, expansion, tolerance, convergence, CRN, MC uncertainty | capability / decision | F-010 |
| §15.1 | annual_results.csv | capability | F-012 |
| §15.2 | sustainability_results.csv | capability | F-013 |
| §15.3 | lifestyle_results.csv | capability | F-013 |
| §15 | CSV conventions; run metadata file | capability / constraint | F-012, F-013 |
| §16 | Tax excluded from core; future interface boundary | constraint | CLAUDE.md; checked in F-014 |
| §17.1 | YAML loads/validates; invalid inputs rejected | test | F-001 |
| §17.1 | Annual→monthly return conversion | test | F-002 |
| §17.1 | Zero inflation keeps index constant | test | F-006 |
| §17.1 | Inflation-linked income tracks index; non-linked constant; start/end dates; survivor % condition | test | F-003 |
| §17.1 | Spending changes after first death | test | F-004 |
| §17.1 | Dead never alive again; monthly mortality conversion | test | F-008 |
| §17.1 | Cash-flow ordering; failure at first month; no negative compounding | test | F-002 |
| §17.1 | Fixed seed reproduces outputs | test | F-005 |
| §17.1 | CRN reused across budgets and returns | test | F-010, F-011 |
| §17.2 | Zero spending no depletion; no capital/no income fails | test | F-002 |
| §17.2 | Large portfolio + zero spending solvent | test | F-009 |
| §17.2 | Deterministic mortality fixture | test | F-008 |
| §17.2 | Deterministic inflation fixture | test | F-006 |
| §17.2 | CSV schemas and units | test | F-012, F-013 |
| §17.2 | Censored paths reported, not successes | test | F-009 |
| §17.2 | Budget optimization feasible within tolerance | test | F-010 |
| §17.2 | Return optimization converges or reports no solution | test | F-011 |
| §17.3 | Acceptance criteria 1–9 | test | F-014 |
| §18 | All implementation decisions documented | decision | see table above; confirmed in F-014 |
| §19 | Official sources; exact downloaded data with versions; source notes | constraint | F-006, F-007 (`data/README.md`) |

Unmapped requirements: **none**.

## Change Log

- 2026-10-09 — F-019 done: `budget.end_reserve_months` adds a reserve success line, a second maximum-budget table and `lifestyle_reserve_results.csv`; V1 outputs and config hashes unchanged at the default; 391 tests.
- 2026-10-09 — F-020 briefed: design brief + tasks F-020.1…F-020.2 (Required Spending = max(budget-based, income) when on; configuration §9).
- 2026-10-09 — F-019 briefed: design brief + tasks F-019.1…F-019.3 (reserve = R × Budget × I at Household End; short-of-reserve counts as Failed; opt-in; optimization §3).
- 2026-10-09 — F-018 done: `results_guide.md` written by every run (results, calculations with the run's numbers, assumptions, limitations, column guide tied to the code, inputs); 380 tests.
- 2026-10-09 — F-017 done: Inputs block printed first by `run` and `inputs.csv` (every validated Scenario field + derived seed, ages, last month); 375 tests.
- 2026-10-09 — F-018 briefed: design brief + tasks F-018.1…F-018.2 (generated Markdown guide; column guide tied to the code).

- 2026-10-09 — F-017 briefed: design brief + tasks F-017.1…F-017.2 (every Scenario field as a row; inputs.csv + console block).
- 2026-10-09 — Added epic v1-1-enhancements: F-016 VS Code test setup (done, tooling-and-process §5); F-017 inputs display; F-018 results guide (Markdown); F-019 end-of-life reserve = 12 × monthly Budget; F-020 spend-at-least-income option (opt-in). Decisions from the user.
- 2026-10-09 — F-014 done: V1 acceptance guards, SPEC §17 acceptance map, README for V1, version 1.0.0 + CHANGELOG, local tag v1.0.0 (367 tests). All 15 features done; all epics delivered. Post-release B-014.1 (guard hardening, README column coverage) verified (369 tests).
- 2026-10-09 — F-014 briefed: design brief + tasks F-014.1…F-014.3 (release = 1.0.0 + CHANGELOG + local tag).
- 2026-10-09 — F-013 done: `sustainability_results.csv` and `lifestyle_results.csv` (conservative rounding), `sbretire run` writes all three CSVs + metadata, fails cleanly on unwritable output; F-013.1–F-013.2 verified (361 tests).
- 2026-10-09 — F-012 done: `annual_results.csv` (streaming calendar-year aggregation, SPEC §12 columns) written by `sbretire run`; F-012.1–F-012.2 verified (356 tests).
- 2026-10-09 — F-013 briefed: design brief + tasks F-013.1…F-013.2 (sustainability rows at the configured Budget).
- 2026-10-09 — F-012 briefed: design brief + tasks F-012.1…F-012.2; decision simulation-conventions §8 (annual definitions) — last SPEC §18 item resolved.
- 2026-10-09 — F-011 done: required fixed return per confidence level at the configured Budget by per-path threshold bisection (±50 %, 0.01 pp, monotonicity verified), shown by `sbretire run`; B-011.1 conservative display rounding (budgets down, returns up); F-011.1–F-011.3 + B-011.1 verified (351 tests). Analysis & Optimization epic complete.
- 2026-10-09 — F-011 briefed: design brief + tasks F-011.1…F-011.3; decision optimization §2 (per-path return search, ±50 % bounds, 0.01 pp tolerance).
- 2026-10-09 — F-010 done: Maximum Sustainable Budget per confidence level by per-path threshold bisection (CRN, £1 tolerance, confirming run), shown by `sbretire run`; F-010.1–F-010.3 verified (335 tests).
- 2026-10-09 — F-010 briefed: design brief + tasks F-010.1…F-010.3; decision optimization §1 (per-path threshold bisection, bounds, £1 tolerance).
- 2026-10-09 — F-009 done: `sbretire run` — random inputs drawn once (CRN), full Monte Carlo, Successful/Failed/Unresolved classification, conservative and completed-path rates with SEs, run_metadata.json; F-009.1–F-009.3 verified (322 tests). Simulation Engine epic complete.
- 2026-10-09 — F-009 briefed: design brief + tasks F-009.1…F-009.3; decision simulation-conventions §7 (path classification, conservative denominator).
- 2026-10-09 — F-008 done: monthly death probabilities, survival curves and inverse-CDF Death Month sampling from the mortality stream; deterministic fixture through the engine; F-008.1–F-008.3 verified (311 tests). Stochastic Inputs epic complete.
- 2026-10-09 — F-008 briefed: design brief + tasks F-008.1…F-008.3; decision simulation-conventions §6 (inverse-CDF death-month sampling).
- 2026-10-09 — F-006 done: `data/uk_cpi.csv` from ONS D7G7 (checked against D7BT), AR(1) lognormal inflation calibrated 1989–2025 (μ 0.0277, φ 0.618, σ 0.0154), monthly-compounding `StochasticPriceIndex`, new `inflation:` config schema, preview at the median rate; F-006.1–F-006.4 verified (299 tests).
- 2026-10-09 — F-006 briefed: design brief + tasks F-006.1…F-006.4; ONS CPI D7G7/D7BT downloaded to `data/raw/`; decisions data-and-calibration §2 (AR(1) lognormal, CPI calibration) and §3 (no non-CPI indexing), simulation-conventions §5 (monthly compounding; supersedes §3).
- 2026-10-09 — F-007 done: `data/ons_mortality.csv` built from ONS `ukppp24qx.xlsx` (29,088 cohort rows), `mortality.py` loader/lookup with age-100 tail, coverage checks in `validate --require-data-files`; F-007.1–F-007.3 verified (264 tests).
- 2026-10-09 — F-007 briefed: design brief + tasks F-007.1…F-007.3; ONS `ukppp24qx.xlsx` downloaded to `data/raw/`; decision data-and-calibration §1 (dataset, q(x, b + x) mapping, cohort extension after 2074, age-100 tail).
- 2026-10-09 — F-005 done: Random Streams (`randomness.py`), Config Hash and Run Metadata (`metadata.py`, `run_metadata.json`); F-005.1–F-005.3 verified (235 tests).
- 2026-10-09 — F-005 briefed: design brief + tasks F-005.1…F-005.3; decisions configuration §7–§8 (Config Hash, generated seed), simulation-conventions §4 (Random Streams, CRN); thesaurus Config Hash, Run Metadata.
- 2026-10-09 — F-015 done: `sbretire preview` (deterministic year-by-year illustration + preview.csv); F-015.1–F-015.3 verified (211 tests).
- 2026-10-09 — F-015 briefed: design brief + tasks F-015.1…F-015.3; provisional decision simulation-conventions §3 (inflation steps on As-Of anniversaries).
- 2026-10-09 — F-004 done: `ScenarioSpending` (survivor's own factor) and `ScenarioCashFlows`; a Scenario now drives the engine end to end; F-004.1–F-004.2 verified (185 tests).
- 2026-10-09 — F-004 briefed: design brief + tasks F-004.1…F-004.2; decision configuration §6 (survivor factor precedence).
- 2026-10-09 — F-003 done: `ScenarioIncome`, `PriceIndex` seam, `month_index`, `recipient: household`; F-003.1–F-003.4 verified (178 tests).
- 2026-10-09 — Added F-015 Deterministic Preview Run (after F-004, before F-005) so a year-by-year projection is visible after F-003 + F-004 instead of after F-013. Not a SPEC requirement; development visibility and a sanity check of cash flows on real inputs.
- 2026-10-09 — F-003 briefed: design brief + tasks F-003.1…F-003.4; decisions configuration §4–§5; thesaurus Household Stream.
- 2026-10-09 — F-002 done: deterministic path-vectorised portfolio engine (`portfolio.py`, `simulation.py`); F-002.1–F-002.3 verified (157 tests).
- 2026-10-09 — F-002 briefed: design brief + tasks F-002.1…F-002.3; decision simulation-conventions §2; thesaurus Death Month, Household End.
- 2026-10-09 — F-001 done: scenario config loading/validation and `sbretire validate`; F-001.1–F-001.4 verified (124 tests).
- 2026-10-09 — Backlog.md dropped; markdown-only backlog (`docs/decisions/tooling-and-process.md` §4).
- 2026-10-09 — F-001 briefed: design brief + tasks F-001.1…F-001.4; decisions simulation-conventions §1, configuration §1–3.
- 2026-10-09 — Initial plan: 6 epics, 14 features (F-001…F-014) from SPEC v1.0.
