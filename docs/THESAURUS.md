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

### Account
- **Definition**: One holding of investments and cash at one provider, owned by one person in one Wrapper, listed in `config/accounts.yaml` with the file patterns of its exports (portfolio-data §1).
- **NOT**: The provider (one provider can hold several accounts) or the Wrapper.
- **Synonyms to AVOID**: pot, plan, portfolio (the model's `portfolio` is the whole investable balance)
- **Related terms**: Wrapper, Ledger

### As-Of Date
- **Definition**: The model valuation date; "today" in every *today's GBP* amount, and the first simulated month is derived from it deterministically (SPEC §5).
- **Synonyms to AVOID**: start date (collides with Income Stream `start_date`), run date
- **Related terms**: Today's GBP, Simulation Month

### Back-test
- **Definition**: Today's portfolio mix (each Price Series' share of today's value, plus cash at the risk-free rate) applied to past Monthly Returns, month by month, re-weighted over the series that have a return each month (portfolio-data §16).
- **NOT**: The household's actual past performance (that needs past holdings: F-031), or a forecast.
- **Synonyms to AVOID**: simulation (the model's Monte Carlo is the simulation), track record
- **Related terms**: Monthly Return, Drawdown, Sharpe Ratio

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

### Completed-Path Success Rate
- **Definition**: N_success / N_completed — reported alongside, never optimized against in V1.
- **Related terms**: Conservative Success Rate

### Confidence Level
- **Definition**: A target simulated success proportion (e.g. 0.95), *not* a statistical confidence interval (SPEC §1.2).
- **Synonyms to AVOID**: confidence interval, certainty, guarantee
- **Related terms**: Target Probability, Conservative Success Rate

### Config Hash
- **Definition**: SHA-256 of the validated Scenario in canonical JSON, excluding the data-file path; unchanged by comments, key order or formatting, changed by any value (configuration §7).
- **Synonyms to AVOID**: file hash, checksum of the YAML
- **Related terms**: Run Metadata, Scenario

### Conservative Success Rate
- **Definition**: N_success / N_all — successful completed paths over *all* paths, treating censored paths as non-successes. The V1 optimization target (SPEC §11).
- **NOT**: *Completed-Path Success Rate* (N_success / N_completed).
- **Synonyms to AVOID**: success rate (unqualified), probability of success (unqualified)
- **Related terms**: Completed-Path Success Rate, Censored Path, Monte Carlo Standard Error

### Death Month
- **Definition**: For one person on one Path, the first month index in which they are dead. They are alive — with full income and spending — through the month before; supplied up front as `death_month[person, path]`, a value ≥ the Horizon meaning alive at the Horizon (simulation-conventions §2). Sampled once per run from the mortality Random Stream by inverse CDF over the person's monthly survival curve (simulation-conventions §6).
- **NOT**: The month they were last alive; a calendar date of death.
- **Synonyms to AVOID**: date of death, mortality month, death date
- **Related terms**: Household End, Path, Censored Path

### Depletion (Failed Path)
- **Definition**: The first month in which balance after return and income is less than *Required Spending*; the path fails, balance is set to zero and the *Shortfall* recorded. No negative balance compounds (SPEC §9). A depleted path is a Failed Path whatever happens later (simulation-conventions §7).
- **Synonyms to AVOID**: bankruptcy, ruin, negative balance, going broke
- **Related terms**: Shortfall, Probability Not Depleted Yet

### Drawdown
- **Definition**: The fall of the Back-test's wealth index below its previous peak, as a fraction; the maximum drawdown is the largest, with its peak, trough and recovery months (portfolio-data §15).
- **NOT**: Depletion (the model running out of money) or a pension drawdown (income drawdown from a SIPP).
- **Synonyms to AVOID**: loss (ambiguous), crash
- **Related terms**: Back-test

### Efficient Frontier
- **Definition**: The lowest-volatility long-only mixes of the Priced Sleeve for each level of historical return, with every weight ≤ `max_weight`, estimated from past Monthly Returns (portfolio-data §22).
- **NOT**: A forecast; the household's actual possible returns.
- **Synonyms to AVOID**: optimal portfolio (implies advice), Markowitz bullet
- **Related terms**: Priced Sleeve, Target Mix, Sharpe Ratio

### End-of-Life Reserve (Required End Balance)
- **Definition**: An opt-in stricter success test (`budget.end_reserve_months`, R months). A Path meets it when it is Successful and its balance at *Household End* is at least the **Required End Balance** R × *Budget* × I_d — the Budget in today's GBP inflated to the Household End month d. A Path that ends below it counts as Failed for the reserve metrics (optimization §3).
- **NOT**: R months of the survivor's reduced spending; a buffer held during life.
- **Synonyms to AVOID**: legacy, bequest, safety margin
- **Related terms**: Maximum Sustainable Budget, Household End, Budget

### External Flow
- **Definition**: Money entering or leaving the household's accounts: bank transfers, contributions, tax relief, transfers from or to another provider. Ledger rows with `flow: external`; returns leave them out (portfolio-data §4).
- **NOT**: Dividends, interest or fees (`flow: none`), or an Internal Transfer.
- **Synonyms to AVOID**: deposit (for every kind), cash flow (ambiguous)
- **Related terms**: Internal Transfer, Ledger

### Factsheet
- **Definition**: A fund's published breakdown, copied into `data/factsheets/<file>.yaml`: its asset-class, sector, region and (optionally) currency weights as shares of the whole fund, its date and its largest holdings (portfolio-data §18).
- **NOT**: A price file, or the fund's own marketing document (the YAML holds only the weights).
- **Synonyms to AVOID**: fund profile, KIID
- **Related terms**: Look-Through, Price Series

### Holding
- **Definition**: One security or cash line of an Account's holdings export at its Valuation Date: quantity, price and value in the account's currency (`output/portfolio/holdings.csv`, portfolio-data §7). Cash is a holding of kind `cash`.
- **NOT**: A Ledger row (a transaction), or the model's `portfolio` (the whole household balance).
- **Synonyms to AVOID**: position (fine in prose for securities), asset
- **Related terms**: Account, Valuation Date, Ledger

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

### Internal Transfer
- **Definition**: A move of money between parts of one Account (e.g. an HL SIPP's income account to its capital account); `type: internal_transfer`, `flow: internal`. Nets away within the account (portfolio-data §4).
- **NOT**: An External Flow, or a transfer between two of the household's accounts at different providers (that is an External Flow out of one and into the other).
- **Synonyms to AVOID**: sweep, journal
- **Related terms**: External Flow, Account

### Ledger
- **Definition**: The normalised list of every Account's transaction legs, merged from all monthly export folders without duplicates and written to `output/portfolio/ledger.csv` by `sbretire portfolio import` (portfolio-data §3–§4). Quantities and cash are signed from the account's side.
- **NOT**: A holdings valuation (positions at a date) or a provider's raw export.
- **Synonyms to AVOID**: transaction history, statement
- **Related terms**: Account, External Flow, Internal Transfer

### Look-Through
- **Definition**: Today's household value broken down by asset class, sector, region and currency by applying each fund's Factsheet weights to its GBP value and each stock's own sector and region, with cash and Unclassified lines so every table adds to the household total (portfolio-data §19).
- **NOT**: The Vanguard holdings export's "Asset Sector" column (coarse and sometimes misleading), or a forecast of returns.
- **Synonyms to AVOID**: allocation (ambiguous with target weights), x-ray
- **Related terms**: Factsheet, Holding

### Maximum Sustainable Budget
- **Definition**: The largest *Budget* B* with Conservative Success Rate ≥ target, found by bisection with CRN to a stated currency tolerance (SPEC §14).
- **Synonyms to AVOID**: safe withdrawal rate, max spend
- **Related terms**: Budget, Confidence Level, Common Random Numbers

### Money-Weighted Return
- **Definition**: An Account's (or the household's) internal rate of return since the first export: the rate at which the starting value plus every External Flow grows to today's value (portfolio-data §28). Shown for the period, and a year when the period is at least a year.
- **NOT**: The Time-Weighted Return; a forecast.
- **Synonyms to AVOID**: IRR in prose (fine as the method), personal return (vague)
- **Related terms**: Time-Weighted Return, External Flow, Ledger

### Monte Carlo Standard Error
- **Definition**: sqrt(p(1−p)/N) for a reported proportion, with its denominator stated (SPEC §11).
- **Related terms**: Conservative Success Rate

### Monthly Return
- **Definition**: A Price Series' total return in GBP for one calendar month: `(P_t + D_t) × X_t / (P_{t-1} × X_{t-1}) − 1` from month-end prices `P` (pounds; GBX ÷ 100), dividends `D` paid in the month and the GBP rate `X` of the quote currency (portfolio-data §12). Unknown when either month has no price.
- **NOT**: The model's fixed `portfolio.annual_return`, or a forecast.
- **Synonyms to AVOID**: performance (too broad), yield
- **Related terms**: Price Series, Holding

### Path
- **Definition**: One simulated household future: a mortality outcome per person plus an inflation path, stepped monthly.
- **Synonyms to AVOID**: scenario (a scenario is a *config*), trial, run (a run is one invocation over N paths)
- **Related terms**: Completed Path, Censored Path

### Price Series
- **Definition**: One security's price history from a user-supplied file in `data/prices/`, listed in `data/prices/securities.yaml` with its quote currency and the Holdings it prices (portfolio-data §11). One series can price the same security held in several Accounts.
- **NOT**: A Holding (a position at one date), or the model's Inflation Index.
- **Synonyms to AVOID**: ticker (the series may have none), feed
- **Related terms**: Monthly Return, Holding

### Priced Sleeve
- **Definition**: The Price Series with a Monthly Return in every month of the window and a value today; the part of the household the Efficient Frontier re-weights. Cash and other holdings stay at today's values (portfolio-data §21).
- **NOT**: The whole portfolio.
- **Synonyms to AVOID**: core, universe (ambiguous)
- **Related terms**: Efficient Frontier, Price Series

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
- **Definition**: Nominal spending due in a month, S_t = B_m × I_t × F_t. With `budget.spend_at_least_income: true` it is max(S_t, that month's household income), so surplus income is spent rather than saved (configuration §9).
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

### Sharpe Ratio
- **Definition**: Annualised mean excess Monthly Return over the monthly risk-free rate divided by annualised volatility: `12 × mean(r − r_f) / (√12 × sd(r))` (portfolio-data §15). Undefined when volatility is zero.
- **NOT**: A measure of future performance.
- **Synonyms to AVOID**: risk-adjusted return (too vague)
- **Related terms**: Back-test, Monthly Return

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

### Target Mix
- **Definition**: The frontier mix the re-weighting trades move towards: by default the highest past return at today's volatility; optionally the maximum-Sharpe or minimum-variance mix (portfolio-data §22).
- **NOT**: A recommendation; within-account trades only approximate it.
- **Synonyms to AVOID**: optimal mix, model portfolio
- **Related terms**: Efficient Frontier, Priced Sleeve

### Time-Weighted Return
- **Definition**: An Account's return since the first export with the effect of External Flows removed: monthly Modified Dietz returns on month-end values rebuilt from the Ledger, chained (portfolio-data §28).
- **NOT**: The Back-test (today's mix applied to the past) or the Money-Weighted Return.
- **Synonyms to AVOID**: performance (too broad), TWRR
- **Related terms**: Money-Weighted Return, Back-test, Ledger

### Today's GBP
- **Definition**: Purchasing-power terms at the As-Of Date; fields suffixed `_today` are in this unit. Internally the engine computes nominal GBP.
- **Synonyms to AVOID**: real pounds (ambiguous), constant pounds
- **Related terms**: Inflation Index, As-Of Date

### Valuation Date
- **Definition**: The date an Account's holdings export values it at, read from the export (Schwab title, HL "Spreadsheet created at", Vanguard `Valuation Date`); for an export that states none (ii) the newest date the other exports in the folder state, marked assumed (portfolio-data §8).
- **NOT**: The model's As-Of Date (the scenario's "today"), though the two are usually close.
- **Synonyms to AVOID**: as-of date (taken), statement date
- **Related terms**: Holding, As-Of Date

### Wrapper
- **Definition**: The tax treatment an Account sits in: `taxable`, `isa`, `pension` or `sipp` (portfolio-data §1). Recorded as a label only; the model has no tax logic (SPEC §16).
- **Synonyms to AVOID**: account type, tax wrapper (fine in prose, not as a field name)
- **Related terms**: Account

## Unresolved

_None yet._ Add `[WHITE-SPOT]` entries here when a concept cannot be named confidently.
