# Optimization Decisions

Scope: maximum-sustainable-budget bisection and required-return search — bounds, bound expansion, tolerances, convergence reporting, Monte Carlo standard error.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- Budget and return optimization bounds and tolerances (SPEC §13, §14). — budget: ~~resolved~~ → §1; return: F-011.

## 1. Maximum Sustainable Budget: per-path threshold bisection, £0 to a doubling upper bound, £1/month tolerance

With one `RandomInputs` reused for every candidate (Common Random Numbers), each Path's success is monotone non-increasing in the Budget, so each Path has a threshold T_i — the largest Budget at which it is Successful. All Paths are bisected together by giving each its own candidate budget in one vectorised engine run: lower bound £0 (feasible for every completed-by-death Path), upper bound starting at 2 × the configured Budget (£1,000 if zero) and doubling until every completed-by-death Path fails, capped at £1,000,000/month (Paths still Successful there take T = cap and are flagged). Bisection stops when every bracket is ≤ £1/month; T_i is the feasible end. Paths with someone alive at the Horizon can never be Successful and have no threshold. For a target p*, B* is the ⌈p*·N⌉-th largest threshold, so the Conservative Success Rate at B* is ≥ p*; if fewer Paths have thresholds, the target is reported infeasible rather than given a number. Each result reports B* per month and per year, the estimated success probability with its standard error (denominator: all Paths), the unresolved fraction, the tolerance, convergence and the iteration count. (F-010)

**Why**: SPEC §14 asks for bisection on the Budget with CRN, explicit bounds verified feasible/infeasible, a documented expansion strategy and a currency tolerance. Because the rate at budget B is exactly the share of thresholds ≥ B, bisecting thresholds per Path is the same bisection resolved for every Path at once: one search (~20 engine runs) serves every confidence level, instead of a separate scalar bisection per target. Taking the feasible end and the ⌈p*·N⌉-th threshold never overstates sustainability. £1/month matches SPEC's example and costs only two runs more than £5; bounds and tolerance are fixed constants echoed in the output rather than configuration.

