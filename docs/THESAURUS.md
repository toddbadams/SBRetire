# SBRetire Thesaurus

The ubiquitous language for the Retirement Sustainability Model. Maintained by the
`/ubiquitous-language` skill; consulted by `/grill-with-docs`, `/design-brief` and code review.
Source of truth for meaning is `docs/SPEC.md`; this file pins down the *words*.

Alphabetized. Flat list — no bounded contexts yet (introduce only if polysemy in Unresolved is confirmed).

## Forbidden Lexicon

Do not use in code or docs: `Manager`, `Helper`/`Util`, `Info`/`Data` suffix on types, `Object`/`Obj`
suffix, bare unqualified `Service`, `confidence interval` (for success probability — see *Confidence Level*),
`retirement income` (ambiguous — say *Income Stream* or *Household Income*), `safe withdrawal rate`.

## Terms

### As-Of Date
- **Definition**: The model valuation date; "today" in every *today's GBP* amount, and the first simulated month is derived from it deterministically (SPEC §5).
- **Synonyms to AVOID**: start date (collides with Income Stream `start_date`), run date
- **Related terms**: Today's GBP, Simulation Month

### Budget (Monthly Budget)
- **Definition**: The base household spending per month expressed in *today's GBP* (`budget.monthly_amount_today`, symbol B_m). Nominal spending each month is B_m × I_t × F_t.
- **NOT**: The nominal amount spent in a given month (that is *Required Spending*).
- **Synonyms to AVOID**: spend, withdrawal, lifestyle (except in the `lifestyle_results.csv` file name)
- **Related terms**: Required Spending, Survivor Budget Factor, Maximum Sustainable Budget

### Censored Path (Unresolved Path)
- **Definition**: A path that never ran out of money and reaches the horizon with at least one person still alive; its lifetime outcome is unknown. Never counted as a success (SPEC §7.2, §11; simulation-conventions §7). A path that ran out of money is Failed even if someone would have outlived the horizon.
- **Synonyms to AVOID**: survivor path, timeout, incomplete
- **Related terms**: Completed Path, Conservative Success Rate, Horizon

### Common Random Numbers (CRN)
- **Definition**: Reuse of the identical mortality and inflation draws across every candidate budget or return in a search, so candidates differ only by the parameter under test (SPEC §10.3).
- **Synonyms to AVOID**: fixed seed (a seed is necessary but not sufficient), shared randomness
- **Related terms**: Random Stream, Budget Optimization, Return Search

### Completed Path
- **Definition**: A path whose lifetime outcome is known: Successful (never depleted, both died within the horizon) or Failed (depleted at any month) — simulation-conventions §7.
- **Related terms**: Censored Path, Successful Path, Failed Path

### Confidence Level
- **Definition**: A target simulated success proportion (e.g. 0.95), *not* a statistical confidence interval (SPEC §1.2).
- **Synonyms to AVOID**: confidence interval, certainty, guarantee
- **Related terms**: Target Probability, Conservative Success Rate

### Conservative Success Rate
- **Definition**: N_success / N_all — successful completed paths over *all* paths, treating censored paths as non-successes. The V1 optimization target (SPEC §11).
- **NOT**: *Completed-Path Success Rate* (N_success / N_completed).
- **Synonyms to AVOID**: success rate (unqualified), probability of success (unqualified)
- **Related terms**: Completed-Path Success Rate, Censored Path, Monte Carlo Standard Error

### Completed-Path Success Rate
- **Definition**: N_success / N_completed — reported alongside, never optimized against in V1.
- **Related terms**: Conservative Success Rate

### Config Hash
- **Definition**: SHA-256 of the validated Scenario in canonical JSON, excluding the data-file path; unchanged by comments, key order or formatting, changed by any value (configuration §7).
- **Synonyms to AVOID**: file hash, checksum of the YAML
- **Related terms**: Run Metadata, Scenario

### Death Month
- **Definition**: For one person on one Path, the first month index in which they are dead. They are alive — with full income and spending — through the month before; supplied up front as `death_month[person, path]`, a value ≥ the Horizon meaning alive at the Horizon (simulation-conventions §2). Sampled once per run from the mortality Random Stream by inverse CDF over the person's monthly survival curve (simulation-conventions §6).
- **NOT**: The month they were last alive; a calendar date of death.
- **Synonyms to AVOID**: date of death, mortality month, death date
- **Related terms**: Household End, Path, Censored Path

### Depletion (Failed Path)
- **Definition**: The first month in which balance after return and income is less than *Required Spending*; the path fails, balance is set to zero and the *Shortfall* recorded. No negative balance compounds (SPEC §9). A depleted path is a Failed Path whatever happens later (simulation-conventions §7).
- **Synonyms to AVOID**: bankruptcy, ruin, negative balance, going broke
- **Related terms**: Shortfall, Probability Not Depleted Yet

### Horizon
- **Definition**: `model.horizon_years` — a computational cap on simulated months, not an assumed age of death.
- **Related terms**: Censored Path

### Household End
- **Definition**: The first month in which both people are dead; the Path stops before that month's cash flows (`PathOutcomes.household_end_month`).
- **NOT**: The first death (that triggers the Survivor Budget Factor, not the end).
- **Synonyms to AVOID**: second death date, joint death, end of plan
- **Related terms**: Death Month, Completed Path, Censored Path

### Household Stream
- **Definition**: An Income Stream with `recipient: household` — owned jointly, paid in full while both are alive and × its Survivor Percentage while exactly one is alive (configuration §5).
- **NOT**: Household income (the total of all streams in a month).
- **Synonyms to AVOID**: joint stream, shared income, household-level pension
- **Related terms**: Income Stream, Recipient, Survivor Percentage

### Income Stream
- **Definition**: One configured inflow (`income[]`) with a start date, annual amount in today's GBP, inflation-linking flag, recipient and survivor percentage. Monthly amount is annual / 12.
- **Synonyms to AVOID**: pension (unless it is one), benefit, payout
- **Related terms**: Recipient, Survivor Percentage, Inflation Index

### Inflation Index (Price Level)
- **Definition**: Cumulative price level, I = 1 in the As-Of month; one annual rate π_k per path per simulated year (AR(1) lognormal), compounding monthly within the year so I_{12k} = ∏_{j<k}(1+π_j) at anniversaries (SPEC §6; simulation-conventions §5).
- **Synonyms to AVOID**: CPI (CPI is the calibration *source*, not the simulated index), deflator
- **Related terms**: Today's GBP, Random Stream

### Maximum Sustainable Budget
- **Definition**: The largest *Budget* B* with Conservative Success Rate ≥ target, found by bisection with CRN to a stated currency tolerance (SPEC §14).
- **Synonyms to AVOID**: safe withdrawal rate, max spend
- **Related terms**: Budget, Confidence Level, Common Random Numbers

### Monte Carlo Standard Error
- **Definition**: sqrt(p(1−p)/N) for a reported proportion, with its denominator stated (SPEC §11).
- **Related terms**: Conservative Success Rate

### Path
- **Definition**: One simulated household future: a mortality outcome per person plus an inflation path, stepped monthly.
- **Synonyms to AVOID**: scenario (a scenario is a *config*), trial, run (a run is one invocation over N paths)
- **Related terms**: Completed Path, Censored Path

### Probability Not Depleted Yet
- **Definition**: Per reporting year, the share of all paths that have not experienced *Depletion* by that date (SPEC §12).
- **NOT**: *Estimated Lifetime Success Rate*.
- **Synonyms to AVOID**: probability funded (ambiguous — banned by SPEC §12)

### Random Stream
- **Definition**: An independent seeded generator dedicated to one stochastic component (mortality, inflation) so changes to one never perturb the other's draws (SPEC §10.3).
- **Related terms**: Common Random Numbers

### Recipient
- **Definition**: Who an Income Stream belongs to: a person `id`, or `household` for a Household Stream; drives survivor treatment when that person (or the first of the two) dies (configuration §4–§5).
- **Related terms**: Income Stream, Household Stream, Survivor Percentage

### Required Spending
- **Definition**: Nominal spending due in a month, S_t = B_m × I_t × F_t.
- **Related terms**: Budget, Survivor Budget Factor, Depletion

### Return Search
- **Definition**: Bracketed root-find for the minimum fixed annual effective return reaching a target Conservative Success Rate at a fixed Budget (SPEC §13).
- **Synonyms to AVOID**: required yield, hurdle rate
- **Related terms**: Common Random Numbers, Maximum Sustainable Budget

### Run Metadata
- **Definition**: The record written as `run_metadata.json` that makes a run reproducible and auditable: seed and its source, software version, Config Hash, data-file hashes and versions, environment versions, `created_at` (SPEC §10.3).
- **Synonyms to AVOID**: run info, run log
- **Related terms**: Config Hash, Random Stream

### Scenario
- **Definition**: One validated YAML configuration — the full set of assumptions for a run.
- **Synonyms to AVOID**: case, profile, path
- **Related terms**: Path

### Shortfall
- **Definition**: Unmet Required Spending in the month of Depletion.
- **Related terms**: Depletion

### Survivor Budget Factor
- **Definition**: Multiplier F_t applied to the Budget while exactly one person is alive: the survivor's own `people[].survivor_budget_factor` if set, otherwise `budget.survivor_budget_factor` (configuration §6). F_t = 1 while both are alive.
- **Synonyms to AVOID**: widow factor, single-life adjustment
- **Related terms**: Budget, Required Spending

### Survivor Percentage
- **Definition**: Proportion (0–1) of an Income Stream that continues when its Recipient has died and the other person is alive (SPEC §8).
- **Synonyms to AVOID**: survivor benefit (that is the resulting amount), reversion
- **Related terms**: Income Stream, Recipient

### Today's GBP
- **Definition**: Purchasing-power terms at the As-Of Date; fields suffixed `_today` are in this unit. Internally the engine computes nominal GBP.
- **Synonyms to AVOID**: real pounds (ambiguous), constant pounds
- **Related terms**: Inflation Index, As-Of Date

## Unresolved

_None yet._ Add `[WHITE-SPOT]` entries here when a concept cannot be named confidently.
