# Simulation Conventions Decisions

Scope: within-month ordering, death timing, depletion/shortfall rule, horizon censoring, Random Streams and common random numbers, annual percentile and funded-probability definitions.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Valuation date and first simulated month (SPEC §5).~~ → §1
- ~~Within-month cash-flow ordering and death timing (SPEC §5, §7.2).~~ → §2
- Horizon-censoring policy and conservative sustainability denominator (SPEC §7.2, §11).
- Definition of annual portfolio percentiles and funded probabilities (SPEC §12).

## 1. As-Of Date is the 1st of a month and is the first simulated month

`model.as_of_date` is required and must fall on the 1st of a month; the first simulated month is the month it names, and "today's GBP" means prices in that month. Any other day is rejected at validation. (F-001)

**Why**: whole months only — no partial-month cash flows, and income dates, monthly steps and calendar-year reporting align. Rejecting beats rounding because silent rounding shifts a month of inflation and cash flow. An implicit "run date" default was rejected: the same file would give different results on different days (SPEC §10.3).

## 2. Within-month ordering, depletion rule and death timing

Each simulated month runs, for every active path: (1) update alive state; (2) determine income and Required Spending due; (3) apply the monthly return r_m = (1+r_a)^(1/12) − 1 to the opening balance; (4) add income; (5) if the balance is now less than Required Spending, the path is depleted: the available balance is spent, the Shortfall (spending − available) is recorded, the balance is set to 0 and the path stops; otherwise (6) subtract spending. Equality is funded. A person's Death Month d is the first month they are dead: they are alive, with full income and spending, through month d−1, and the alive update at the start of month d removes them. When both are dead at a month start the path ends (Household End) before that month's cash flows. (F-002)

**Why**: SPEC §5's V1 default ordering and SPEC §9's shortfall-based failure rule — assessing funding before spending exposes the timing and size of unmet spending, and no negative balance can compound as if borrowing were available. Whole-month death boundaries match monthly q_m sampling (F-008) and avoid pro-rating; a half-month convention and "dead within the death month" were considered and rejected as adding fractional logic without a SPEC requirement.

## 3. ~~Inflation steps on As-Of anniversaries (provisional — F-006 to confirm or replace)~~ — superseded by §5

Deterministic constant inflation steps once a year on As-Of anniversaries: I_t = (1 + π)^floor(t/12), so prices are flat for months 0–11 and step up at months 12, 24, …. First used by the F-015 preview (`AnnualStepPriceIndex`). F-006 must confirm this year boundary for stochastic draws or replace it; the preview follows whatever F-006 decides. (F-015)

**Why**: SPEC §6 recommends one annual rate held for the twelve monthly steps of each simulated year, and "today's GBP" is the As-Of month, so simulation years naturally start there. Smooth monthly compounding was rejected because it would differ from the annual-draw process F-006 will build; calendar-year (January) steps were rejected for now because the first step would come only a few months after the As-Of date — F-006 may still choose it to align with calendar-year reporting.

## 4. Random Streams by fixed spawn index; Common Random Numbers by creating streams once per run

One `numpy.random.SeedSequence(seed)` roots all randomness. Each stochastic component gets its own Random Stream — a `Generator(PCG64)` on a fixed child: mortality = child 0, inflation = child 1; a future component takes the next unused index. Streams are created once per run; the mortality and inflation draws they produce are reused unchanged for every candidate Budget or return in a search (Common Random Numbers) — candidates never re-seed. (F-005)

**Why**: SPEC §10.3 requires separate streams so a change to one component leaves the other's draws identical, and CRN across candidates so optimisation compares like with like. Fixed indices (rather than spawn order at call sites) mean adding a stream never shifts existing draws; a known-answer test pins them. A single shared generator was rejected because consuming more inflation draws would shift every later mortality draw.

## 5. Inflation years start at the As-Of month and compound monthly (supersedes §3)

Simulated year k covers months 12k to 12k + 12, starting in the As-Of month. One annual rate π_k is drawn per Path for year k and applied to each of its twelve monthly steps: I_0 = 1 and, for 12k ≤ t ≤ 12(k + 1), I_t = I_{12k} · (1 + π_k)^((t − 12k)/12), so at anniversaries I_{12k} = ∏_{j<k}(1 + π_j), SPEC §6's I_y. The deterministic preview uses the same index with every π equal to the median rate e^μ − 1. (F-006)

**Why**: SPEC §6 says to apply the annual rate "to each of the twelve monthly steps in that year"; prices rising through the year avoids the provisional §3 step's zero inflation for the first eleven months (≈ half a year of inflation understated on average). Years anchored on the As-Of month keep "today's GBP" at I_0 = 1 with no partial first year; calendar-year reporting (F-012) reads I_t at any month. Calendar-year (January) rate boundaries were rejected as giving a short, partial first year.

## 6. Death Months are sampled by inverse CDF from each person's monthly survival curve

For each person, monthly death probabilities q_m = 1 − (1 − q)^(1/12) (q = the cohort rate for their age in completed years from the birth month, data-and-calibration §1) give a survival curve S_0 = 1, S_{t+1} = S_t (1 − q_m,t) over months 0 … H − 1, identical on every Path. One uniform u per person per Path (`rng.random((2, n_paths))` from the mortality Random Stream, person-major) gives the Death Month d = min(searchsorted(1 − S[1:], u, right) + 1, H): a death in month t gives d = t + 1 (§2), and d = H means alive through the horizon (censored). The two people are independent. (F-008)

**Why**: statistically identical to SPEC §7.2's month-by-month conditional draws, but vectorised and needing 2 · n_paths draws instead of one per person, path and month (144M for 100k paths over 60 years). Because each death uses a single uniform, lengthening the horizon never changes deaths inside the shorter one, which keeps Common Random Numbers stable across runs and candidates. Per-month Bernoulli draws were rejected for cost and memory with no difference in distribution.

