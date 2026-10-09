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
