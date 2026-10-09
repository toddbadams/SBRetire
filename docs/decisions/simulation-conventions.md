# Simulation Conventions Decisions

Scope: within-month ordering, death timing, depletion/shortfall rule, horizon censoring, Random Streams and common random numbers, annual percentile and funded-probability definitions.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Valuation date and first simulated month (SPEC §5).~~ → §1
- Within-month cash-flow ordering and death timing (SPEC §5, §7.2).
- Horizon-censoring policy and conservative sustainability denominator (SPEC §7.2, §11).
- Definition of annual portfolio percentiles and funded probabilities (SPEC §12).

## 1. As-Of Date is the 1st of a month and is the first simulated month

`model.as_of_date` is required and must fall on the 1st of a month; the first simulated month is the month it names, and "today's GBP" means prices in that month. Any other day is rejected at validation. (F-001)

**Why**: whole months only — no partial-month cash flows, and income dates, monthly steps and calendar-year reporting align. Rejecting beats rounding because silent rounding shifts a month of inflation and cash flow. An implicit "run date" default was rejected: the same file would give different results on different days (SPEC §10.3).
