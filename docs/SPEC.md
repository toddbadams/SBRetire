# Retirement Sustainability Model — Formal Specification

**Document:** `SPEC.md`  
**Version:** 1.0  
**Status:** Initial implementation specification  
**Date:** 2026-10-09

## 1. Purpose and scope

The Retirement Sustainability Model estimates the maximum sustainable household spending level, expressed in today's GBP, subject to a target probability that the household can meet its spending needs for the joint remaining lifetimes of two people.

The model uses Monte Carlo simulation with:
- monthly cash-flow and portfolio accounting;
- stochastic inflation;
- deterministic annual investment return in V1;
- mortality sampled from a configured UK cohort-mortality table;
- independently configured income streams and survivor benefits;
- a survivor spending adjustment;
- CSV outputs for annual outcomes, sustainability analysis, and budget optimization.

The model is for planning and research. It is not financial advice, does not forecast investment returns, and does not guarantee future solvency.

### 1.1 Primary question

Given starting capital, income streams, inflation assumptions, a fixed investment return, and mortality assumptions, what is the maximum monthly household budget (in today's pounds) that achieves a specified probability of portfolio solvency throughout the household's simulated joint lifetime?

### 1.2 Secondary questions

- What is the probability the portfolio remains able to fund spending in each future year?
- What is the portfolio distribution over time?
- What fixed annual return is required to meet a specified sustainability probability for a given budget?
- What budget is sustainable at 90%, 95%, and 99% confidence?

In this specification, “confidence” means the simulated proportion of paths that remain solvent; it is not a guarantee or a statistical confidence interval.

## 2. V1 boundaries

### Included
- Two people, each with a date of birth and mortality-table sex category.
- Monthly simulation steps.
- Configurable initial portfolio value.
- Fixed annual nominal investment return, compounded monthly.
- Stochastic inflation, with a documented parameter source.
- Multiple income streams with start dates, inflation-linking rules, and survivor percentages.
- Household spending that changes after the first death.
- ONS 2024-based UK cohort mortality data, subject to data availability and documented mapping.
- Monte Carlo sustainability estimation and budget optimization.
- Deterministic reproducibility through a configured random seed.
- CSV reporting.

### Excluded from V1
- Tax, tax relief, and tax-efficient withdrawal sequencing.
- Stochastic investment returns, volatility, asset allocation, and sequence-of-returns risk.
- Fees, transaction costs, and investment platform charges unless represented explicitly as a reduction to the configured return.
- Housing transactions, bequests, long-term-care costs, and one-off expenditure shocks.
- More than two people.
- Detailed benefit eligibility rules or legal pension-survivor rules not explicitly represented in configuration.
- Automatic live data downloads during simulation.

Tax must be implemented later as a separate module so it can be introduced without rewriting the simulation engine.

## 3. Technology and project layout

- Language: Python 3.x.
- Configuration: YAML.
- Outputs: CSV.
- Numerical engine: NumPy-oriented; pandas may be used for output handling.
- Suggested dependencies: `numpy`, `pandas`, `pyyaml`, `scipy`, plus a test framework such as `pytest`.

Suggested layout:

```text
retirement_model/
├── config/
│   └── model.yaml
├── data/
│   ├── ons_mortality.csv
│   └── uk_cpi.csv
├── src/
│   ├── config.py
│   ├── inflation.py
│   ├── mortality.py
│   ├── income.py
│   ├── spending.py
│   ├── portfolio.py
│   ├── simulation.py
│   ├── optimization.py
│   └── output.py
├── tests/
├── run.py
├── requirements.txt
├── README.md
└── SPEC.md
```

The implementation may use a different internal layout if module responsibilities and interfaces remain clear.

## 4. Configuration

All scenario assumptions must be externalized in YAML. The simulation must not depend on hard-coded personal assumptions.

### 4.1 Illustrative YAML

The values below are examples only and must not be treated as verified personal financial inputs.

```yaml
model:
  currency: GBP
  simulation_count: 100000
  confidence_levels: [0.90, 0.95, 0.99]
  frequency: monthly
  horizon_years: 100
  random_seed: 42

portfolio:
  starting_balance: 1500000
  annual_return: 0.05

budget:
  monthly_amount_today: 6667
  survivor_budget_factor: 0.70

inflation:
  source: UK_CPI
  source_period: "1989-2025"
  annual_mean: 0.025
  annual_standard_deviation: 0.015
  model: annual_lognormal_or_normal
  parameter_units: annual_rate

mortality:
  source: ONS_2024_BASED
  geography: UK
  projection: principal
  data_file: data/ons_mortality.csv

people:
  - id: person_1
    name: Person 1
    date_of_birth: "1960-09-14"
    sex: male
    survivor_budget_factor: 0.70

  - id: person_2
    name: Person 2
    date_of_birth: "1969-05-01"
    sex: female
    survivor_budget_factor: 0.70

income:
  - id: social_security
    name: Social Security
    start_date: "2027-09-01"
    annual_amount_today: 20000
    inflation_linked: true
    survivor_percentage: 1.0
    recipient: person_1

  - id: state_pension
    name: UK State Pension
    start_date: "2028-09-01"
    annual_amount_today: 20000
    inflation_linked: true
    survivor_percentage: 1.0
    recipient: person_2

  - id: nhs_pension
    name: NHS Pension
    start_date: "2029-01-01"
    annual_amount_today: 31000
    inflation_linked: true
    survivor_percentage: 0.50
    recipient: person_2
```

`model.inflation.model` is illustrative: the implementation must select and document one precise process before release. A normal distribution for inflation can generate values below -100% in unconstrained tails, so a bounded or lognormal process is generally safer. The selected process and its parameter interpretation must be consistent with calibration data.

### 4.2 Required configuration fields

**Model**
- `currency`: `GBP` in V1.
- `simulation_count`: positive integer.
- `confidence_levels`: list of probabilities strictly between 0 and 1.
- `frequency`: `monthly` in V1.
- `horizon_years`: positive integer.
- `random_seed`: integer or `null`; if `null`, record the generated seed in output metadata.

**Portfolio**
- `starting_balance`: non-negative amount in GBP.
- `annual_return`: fixed annual nominal effective return; must be greater than -100%.

**Budget**
- `monthly_amount_today`: non-negative real monthly spending amount in GBP.
- `survivor_budget_factor`: non-negative multiplier applied after one person dies. Per-person overrides may be supported; precedence must be documented.

**Inflation**
- Source and source period.
- Calibrated annual mean and volatility, or a versioned empirical series.
- Explicit stochastic-process choice and units.
- The implementation must define whether inflation is sampled annually and held constant within each year, or generated monthly. V1 should use annual draws held constant for the twelve months of each simulated year unless an approved alternative is documented.

**Mortality**
- Source, geography, projection variant, and local data file.
- Dataset version/publication date and retrieval date recorded in run metadata.
- Mapping from age/sex/year to annual death probability.

**People**
- Unique `id`, display `name`, ISO date of birth (`YYYY-MM-DD`), and supported mortality-table sex category.
- Optional survivor budget factor.
- Sex-category mapping must match the selected mortality dataset's definitions; do not infer or silently transform categories.

**Income stream**
- Unique `id`, `name`, `start_date`, `annual_amount_today`, `inflation_linked`, `survivor_percentage`, and `recipient`.
- `survivor_percentage` is a proportion from 0 to 1.
- The implementation must document how a stream is treated if its recipient dies and the other person remains alive.
- If an income has no individual recipient, support an explicitly configured household-level stream and define its end/survivor behavior.
- Optional future fields may include `end_date`, `escalation_rule`, and `recipient`.

### 4.3 Validation

Fail fast with actionable errors if:
- required keys are missing or have invalid types;
- dates are invalid or inconsistent;
- IDs are duplicated;
- monetary amounts are negative where prohibited;
- percentages fall outside their permitted ranges;
- the mortality data do not cover required ages/years;
- inflation or mortality data contain invalid values;
- no valid simulation horizon is defined.

Unknown configuration keys should either be rejected or reported as warnings according to a documented strictness setting.

## 5. Units, timing, and conventions

- Currency: nominal GBP unless a field explicitly says “today”.
- `annual_amount_today` and `monthly_amount_today` are expressed in purchasing-power terms at the model's valuation date.
- Simulation step: one calendar month.
- Use one documented within-month ordering consistently. V1 default: at each month start, update alive/dead state, determine income and spending due for that month, apply the month's investment return to the opening balance, then add income and subtract spending. The implementation must use this same ordering in tests and documentation.
- The model valuation date and first simulated month must be explicit in configuration or derived deterministically from a configured `as_of_date`.
- A death occurring during a month takes effect according to a documented convention. V1 may model death at month boundaries using monthly mortality probabilities.
- Values should be computed in nominal terms internally; real-value reporting must deflate using the same inflation path.

The example YAML should be extended with `as_of_date` before production implementation.

## 6. Inflation model

Inflation changes nominal spending and inflation-linked income while leaving the underlying “today's pounds” lifestyle definition unchanged.

Let \(\pi_y\) be the inflation rate drawn for simulated year \(y\). V1 should draw one annual rate per path per year and apply it to each of the twelve monthly steps in that year.

The model must define the distribution precisely. Recommended options are:
1. resampling annual historical CPI inflation observations; or
2. a calibrated parametric process with documented parameters and constraints.

The implementation must not silently equate a sample mean and standard deviation of annual rates with parameters of a lognormal distribution. It must document whether the inputs are arithmetic moments, log-space parameters, or empirical observations.

Cumulative price level:
\[
I_0 = 1,\qquad I_y = I_{y-1}(1+\pi_y)
\]
subject to the chosen inflation process guaranteeing \(1+\pi_y>0\).

Monthly nominal household spending:
\[
S_t = B_m \times I_t \times F_t
\]
where:
- \(B_m\) is the base monthly budget in today's GBP;
- \(I_t\) is the cumulative inflation index;
- \(F_t=1\) while both people are alive;
- \(F_t\) is the configured survivor budget factor when exactly one person remains alive.

If a per-person survivor factor is configured, it overrides the household default according to the documented precedence.

Income that is inflation-linked uses the same CPI path unless a separate escalation rule is explicitly supported. Non-linked income remains at its configured nominal amount after commencement.

## 7. Mortality model

### 7.1 Data source

Use the Office for National Statistics (ONS) 2024-based UK cohort life tables/projections, with the principal projection unless configuration specifies otherwise. The implementation must verify the exact dataset file, table, geography, sex categories, age range, and year coverage before release.

Reference sources:
- ONS, *National population projections: 2024-based*: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections
- ONS mortality and life tables landing pages: https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies

These links are starting points, not a substitute for recording the exact downloaded dataset and version.

### 7.2 Sampling

For each person and simulation path, sample a death time from the configured cohort mortality rates. Mortality paths for the two people are independent in V1 unless a later model explicitly adds dependence.

If the input provides annual conditional probability of death \(q_{x,y}\), a simple conversion to a constant monthly conditional probability is:
\[
q_{m}=1-(1-q_{x,y})^{1/12}
\]
This conversion assumes the annual probability is spread uniformly over twelve months. A more precise implementation may use fractional-age cohort rates if available, but it must document the method.

For each month, if the person is alive at the beginning of the month, sample death using the relevant conditional probability for their age and calendar year. Once dead, the person remains dead.

The simulation horizon is a computational cap, not a claim that a person necessarily dies by that age. If one or both people remain alive at the horizon, record the path as right-censored and report it. Do not silently count a path as a lifetime success if the modeled lifetime has not completed; for conservative sustainability calculations, a horizon-reaching path should be treated as unresolved or failed according to a documented policy. Recommended V1 policy: classify it as unresolved and report the unresolved fraction separately; exclude unresolved paths from neither numerator nor denominator without explicit reporting.

## 8. Income calculation

Each income stream is calculated independently each month.

For an income stream \(j\):
- it is inactive before `start_date` and after any configured `end_date`;
- it is available only according to the configured recipient and survivor rules;
- if inflation-linked, its nominal value is based on `annual_amount_today` multiplied by the simulated cumulative inflation index;
- monthly income is the applicable annual amount divided by 12.

For a stream with recipient \(p\), if \(p\) has died and the other person is alive, apply `survivor_percentage` to the otherwise applicable amount. If both people have died, the simulation ends and household income is no longer relevant.

V1 must make explicit whether survivor percentage applies only after the named recipient dies, and whether the stream ceases after both deaths. It must not assume that every pension or Social Security benefit follows the same legal survivor rules. The configuration represents user-supplied assumptions, not legal eligibility validation.

## 9. Portfolio accounting

Convert the fixed annual effective nominal return \(r_a\) into a monthly effective rate:
\[
r_m = (1+r_a)^{1/12}-1
\]
This is valid for \(r_a>-1\).

At each month, under the specified timing convention:
\[
P_{t+1} = P_t(1+r_m)+Y_t-S_t
\]
where:
- \(P_t\) is opening portfolio balance;
- \(Y_t\) is total income received during the month;
- \(S_t\) is required household spending for the month.

A path fails at the first month where the portfolio cannot fund required spending. The implementation must choose and document whether failure is assessed before or after that month's cash flows. Recommended definition: if the balance after applying return and income but before spending is less than the required spending, the path fails in that month; the remaining balance is set to zero for reporting and the shortfall is recorded. Do not allow a negative balance to compound as though borrowing were available.

This explicit shortfall-based rule is preferable to merely checking whether the closing balance is negative, because a negative balance can otherwise obscure the amount and timing of unmet spending.

## 10. Monte Carlo engine

### 10.1 Inputs

- Validated configuration.
- Inflation process and calibrated parameters/data.
- Mortality table.
- Starting balance, fixed annual return, income definitions, budget, survivor rules.
- Number of simulations and seed.

### 10.2 Per-path process

For each path:
1. Initialize the portfolio, inflation index, income state, and alive status for both people.
2. Generate or sample mortality outcomes over the horizon.
3. Generate the inflation path.
4. For each month, determine the alive state.
5. Stop the path when both people are dead.
6. Calculate applicable income and spending.
7. Apply portfolio return and cash flows according to the documented ordering.
8. Record depletion month, shortfall, portfolio balance, alive state, and inflation index.
9. Mark the path as solvent only if it meets all required spending through the last month in which at least one person is alive.
10. Mark paths that reach the horizon with at least one person alive as unresolved/censored.

### 10.3 Reproducibility

- A fixed seed must reproduce identical outputs for the same software version, inputs, and data files.
- Record the seed, software version, configuration hash, mortality dataset version/hash, and inflation dataset version/hash in run metadata.
- Use separate random-number streams for mortality and inflation so changes to one component do not inadvertently change the other component's draws.
- Use common random numbers when comparing candidate budgets or returns. The same underlying mortality and inflation paths should be reused across candidates.

### 10.4 Performance

The implementation should avoid storing every monthly value for every path unless needed for reporting. Aggregate statistics should be calculated incrementally or with memory-conscious arrays. If path-level detail is needed for quantiles, store only the minimum data required.

## 11. Success metric and uncertainty

A completed path is successful if the portfolio funds every required monthly expense until both people have died, with no unmet spending.

For a set of completed, non-censored paths:
\[
\hat{p}_{success}=\frac{N_{success}}{N_{completed}}
\]

Because horizon-reaching paths are censored, outputs must separately include:
- completed paths;
- successful completed paths;
- failed paths;
- unresolved/censored paths;
- success rate among completed paths;
- conservative lower-bound success rate using all paths as denominator and unresolved paths as non-successes.

The optimization target must use the conservative lower-bound rate in V1 unless an explicit alternative is configured. This avoids overstating sustainability because of a finite horizon.

“Confidence level” refers to this simulated success proportion, not a formal confidence interval. The output should optionally include a binomial Monte Carlo standard error:
\[
SE(\hat p)=\sqrt{\hat p(1-\hat p)/N}
\]
with the denominator definition clearly stated.

## 12. Annual reporting

Produce one row per calendar year and include, where applicable:

- `year`
- `probability_both_alive`
- `probability_person_1_alive`
- `probability_person_2_alive`
- `monthly_budget_today`
- `monthly_budget_nominal_median` (or another explicitly identified statistic)
- `annual_budget_nominal_median`
- `annual_income_median`
- `annual_net_withdrawal_median`
- `portfolio_p05`
- `portfolio_p25`
- `portfolio_median`
- `portfolio_p75`
- `portfolio_p95`
- `probability_funded`
- `probability_depleted`
- `completed_paths`
- `unresolved_paths`

Definitions must be consistent. For example, portfolio percentiles should state whether they include failed paths (with portfolio value set to zero) and paths where the household has already died. Recommended: calculate household portfolio distributions across all paths still in scope, set failed portfolios to zero after depletion, and separately report alive-conditioned distributions if useful.

`probability_funded` must be explicitly defined as the proportion of all simulation paths that have not yet experienced depletion by the reporting date, or as a lifetime-success probability conditioned on the path's future outcome. These are different measures; V1 should publish both under unambiguous names:
- `probability_not_depleted_yet`: no depletion has occurred by this year;
- `estimated_lifetime_success_rate`: eventual completed-path success estimate, with censored paths reported separately.

## 13. Sustainability and return analysis

For a fixed monthly budget, evaluate the conservative sustainability probability.

For a fixed budget, find the minimum annual effective return required to reach each configured target, using a bracketed root-finding or bisection method. Define search bounds, stopping tolerance, and behavior when no solution exists within the bounds. Return monotonicity is expected in this deterministic-return V1 model but must be verified for the chosen cash-flow convention.

Suggested output columns:
- `monthly_budget_today`
- `target_probability`
- `required_annual_return`
- `estimated_success_probability`
- `unresolved_fraction`
- `converged`
- `iterations`

Return results are model outputs under fixed-return assumptions, not forecasts.

## 14. Maximum sustainable budget optimization

For a target probability \(p^*\), find the maximum base monthly budget \(B^*\) such that:
\[
\hat p_{conservative}(B^*) \ge p^*
\]

Use bisection over the budget, with common random numbers across candidates.

Requirements:
- Set lower and upper bounds explicitly.
- Verify the lower bound is feasible and upper bound infeasible, or expand bounds using a documented strategy.
- Define a currency tolerance, e.g. £1 or £5 per month.
- Record convergence status and iteration count.
- Use a conservative success estimate that treats unresolved/censored paths as non-successes.
- Report estimated Monte Carlo uncertainty at the selected budget.
- Avoid presenting illustrative example numbers as calculated results.

Suggested output columns:
- `target_probability`
- `maximum_monthly_budget_today`
- `maximum_annual_budget_today`
- `estimated_success_probability`
- `unresolved_fraction`
- `budget_tolerance`
- `converged`
- `iterations`

## 15. CSV outputs

V1 produces three CSV files.

### 15.1 `annual_results.csv`

Year-by-year survival, spending, income, and portfolio statistics as defined in Section 12.

### 15.2 `sustainability_results.csv`

One row per tested budget/target pair, or per target for a configured budget, with:
- `monthly_budget_today`
- `target_probability`
- `estimated_success_probability`
- `conservative_success_probability`
- `unresolved_fraction`
- `required_annual_return` (when return search is run)
- `converged`
- `iterations`

### 15.3 `lifestyle_results.csv`

One row per target confidence level, containing the maximum sustainable monthly and annual budget in today's GBP, estimated probability, unresolved fraction, tolerance, and convergence metadata.

All CSV files must:
- use UTF-8 encoding;
- include a header row;
- use `.` as decimal separator;
- use ISO dates where dates appear;
- document units in column names or README;
- avoid currency symbols and thousands separators in numeric fields.

A separate run metadata file (JSON or YAML) is recommended for reproducibility, although the three CSV files remain the required primary outputs.

## 16. Tax module boundary

Tax is excluded from V1. Later tax support must be implemented behind a clearly defined interface that receives gross income, taxable portfolio withdrawals, household/person state, and tax-year rules, and returns net spendable cash flow and tax amounts.

The core simulation must not contain embedded tax thresholds or country-specific tax logic. Tax implementation must have its own configuration, source/versioning, and tests.

## 17. Testing and acceptance criteria

### 17.1 Unit tests

At minimum:
- YAML loads and validates valid configuration.
- Missing fields, duplicate IDs, invalid dates, and invalid percentages are rejected.
- Annual-to-monthly return conversion matches the formula.
- Zero inflation keeps the price index constant.
- Inflation-linked income tracks the inflation index.
- Non-inflation-linked income remains nominally constant.
- Income starts and ends on configured dates.
- Survivor percentage applies only under the configured recipient-death condition.
- Spending changes after the first death according to the configured factor.
- A dead person never becomes alive again.
- Monthly mortality conversion reproduces the annual probability over twelve identical monthly intervals, within numerical tolerance.
- Portfolio cash-flow ordering matches the documented convention.
- A path records failure at the first month it cannot fund spending.
- No negative balance is allowed to compound after failure.
- A fixed seed reproduces outputs.
- Common random numbers are reused across candidate budgets and returns.

### 17.2 Integration tests

- A zero-spending scenario does not fail from spending depletion.
- A scenario with no starting capital and no income fails when positive spending is due.
- A sufficiently large portfolio with zero spending remains solvent for all completed paths.
- A deterministic mortality fixture produces expected household state transitions.
- A deterministic inflation fixture produces expected nominal spending.
- CSV schemas and units match this specification.
- Censored paths are reported and do not silently count as successes.
- Budget optimization returns a feasible budget within configured tolerance on a small deterministic fixture.
- Return optimization either converges to a valid bracketed result or clearly reports no solution.

### 17.3 Acceptance criteria

V1 is acceptable when:
1. All required configuration fields are validated.
2. All unit and integration tests pass.
3. A fixed seed and unchanged data/configuration reproduce identical results in the supported environment.
4. Mortality and inflation source files and versions are documented.
5. Annual, sustainability, and lifestyle CSVs are generated with documented schemas.
6. Censored paths and Monte Carlo uncertainty are visible in outputs.
7. Budget and return optimization use common random numbers and report convergence.
8. Tax logic is absent from the core model.
9. The README explains installation, configuration, running the model, output interpretation, assumptions, and limitations.

## 18. Implementation decisions to finalize before release

The following must be explicitly resolved and documented during implementation:
- Exact ONS file/table and age/period mapping used for cohort mortality.
- Valuation date and first simulated month.
- Exact inflation stochastic process and calibration dataset.
- Within-month cash-flow ordering and death timing.
- Behavior of each income stream after recipient death.
- Treatment of household-level income and survivor benefits.
- Whether any income is indexed to a measure other than CPI.
- Horizon-censoring policy and conservative sustainability denominator.
- Budget and return optimization bounds and tolerances.
- Definition of annual portfolio percentiles and funded probabilities.

These are deliberate implementation decisions, not details to be left implicit.

## 19. References and provenance

Use official sources and preserve the exact downloaded data with version metadata.

- Office for National Statistics (ONS), *National population projections: 2024-based*: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections
- Office for National Statistics (ONS), *Life expectancy and mortality*: https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies

The implementation team must verify the exact dataset and methodology from the downloaded source files and include source notes in the repository. Do not claim that a data file is included unless it has actually been downloaded and checked.
