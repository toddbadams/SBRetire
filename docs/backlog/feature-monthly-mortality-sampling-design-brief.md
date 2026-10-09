---
id: F-008
type: feature
parent: stochastic-inputs
status: planned
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-008 Monthly Mortality Sampling

## 1. Purpose

Turn each person's ONS cohort death rates (F-007) into a random **Death Month** per **Path** (SPEC §7.2), drawn from
the mortality **Random Stream** (F-005), in the `(2, n_paths)` shape `simulate_paths` already takes (F-002). With the
stochastic price index (F-006) this completes the inputs F-009 needs for the first Monte Carlo run.

Makes passable SPEC §17.1 "Monthly mortality conversion reproduces the annual probability over twelve identical
monthly intervals" and "A dead person never becomes alive again", and §17.2 "A deterministic mortality fixture
produces expected household state transitions". Records the sampling method (simulation-conventions §6).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Monthly probability | q_m = 1 − (1 − q)^(1/12), constant within each year of age | SPEC §7.2's conversion; twelve months compound back to q exactly | SPEC §7.2 |
| 2 | Rate for a month | Age x at month t = completed years from the birth month to the month's start; q = `MortalityTable.annual_q(sex, b, x)` = q(x, b + x), ages > 100 hold q(100, b + 100) | F-007 mapping | data-and-calibration §1 |
| 3 | Death timing | Death sampled in month t (alive at its start, with full cash flows) → Death Month d = t + 1. Nobody dies in month 0's alive update (both alive at the As-Of month, validated DOB < As-Of). Survivors to the horizon get d = `horizon_months` | Engine convention: alive = month < d; d ≥ horizon ⇒ alive at horizon ⇒ censored | simulation-conventions §2; F-002 |
| 4 | Sampling method | **Inverse CDF**: per person, survival S_0 = 1, S_{t+1} = S_t (1 − q_m,t) for t < H (identical for all paths); one uniform u per person per path mapped through F_k = 1 − S_k so that P(d ≤ k) = 1 − S_k for k < H (rule below) | Same distribution as SPEC §7.2's month-by-month draws, vectorised, 2·n_paths draws; deaths inside a horizon are unchanged by a longer horizon (CRN-stable) | Interview Q1; simulation-conventions §6 |
| 5 | Draw layout | `u = rng.random((2, n_paths))`, person-major (row 0 = `people[0]`), from `RandomStreams.mortality`, once per run | Independence of the two people (SPEC §7.2); CRN | SPEC §7.2, §10.3 |
| 6 | Placement | `monthly_death_probabilities`, `survival_curve`, `sample_death_months` in `sbretire/mortality.py` | Mortality module owns rates and sampling | SPEC §3 |

Precise inverse-CDF rule (#4): with F_k = 1 − S_k (non-decreasing, F_0 = 0) and u ~ U[0, 1),
`d = min(searchsorted(F[1:], u, side="right") + 1, H)`, i.e. 1 + the number of k in 1…H with F_k ≤ u, capped at H.
Then P(d ≤ k) = P(u < F_k) = F_k for k < H, P(d = k) = F_k − F_{k−1}, and P(d = H) = S_{H−1} (dies in the last
simulated month, or survives it).

## 3. Context

- `simulate_paths(death_month (2, n_paths) int64, horizon_months, …)`: alive = month < death_month; censored when the
  later death month ≥ horizon (F-002).
- `MortalityTable.annual_q` vectorised over ages with the age-100 tail; `coverage_issues` (F-007).
- `RandomStreams.mortality` (F-005, child 0).
- `timeline.month_index(as_of, when)`.
- Note on d = H: a death sampled in the last simulated month gives d = H too, which the engine reads as alive at the
  horizon — correct, because the person was alive throughout every simulated month.

## 4. Touch-points

**New**: `tests/unit/test_mortality_sampling.py`, `tests/integration/test_mortality_end_to_end.py`.

**Modified**: `src/sbretire/mortality.py`; `README.md`; `docs/decisions/simulation-conventions.md` (§6, with this
brief); `docs/THESAURUS.md` (Death Month: sampled).

## 5. Interfaces

```python
# sbretire/mortality.py
def monthly_death_probabilities(
    table: MortalityTable, person: Person, as_of: date, horizon_months: int
) -> NDArray[np.float64]: ...  # (horizon_months,) q_m for months 0 … H−1


def survival_curve(monthly_q: NDArray[np.float64]) -> NDArray[np.float64]: ...  # (H + 1,), S_0 = 1


def sample_death_months(
    scenario: Scenario, table: MortalityTable, rng: np.random.Generator, n_paths: int
) -> NDArray[np.int64]: ...  # (2, n_paths), values in 1 … horizon_months
```

## 6. Plan of Work

1. Monthly probabilities and survival curve.
2. Inverse-CDF sampling.
3. Deterministic fixture through the engine; hypothesis invariant; docs.

## 7. Validation

- **T1**: unit tests; ruff; mypy.
- **T2**: deterministic mortality fixture (q = 0 then 1) through `simulate_paths`: exact state transitions.
- **T3**: statistical — 100k paths, seed pinned: empirical P(d ≤ k) within 4 binomial SE of 1 − S_k at several k;
  near-zero correlation between the two people.

## 8. Decision Log

- 2026-10-09 — Inverse-CDF sampling with one uniform per person per path (Interview Q1; simulation-conventions §6).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-008.1 Monthly death probabilities and survival curve
- **Status**: To Do
- **Depends on**: —

`monthly_death_probabilities` and `survival_curve` in `src/sbretire/mortality.py` (§2 #1–#2). Tests in
`tests/unit/test_mortality_sampling.py` (fixture tables via `tests/unit/mortality_fixtures.py`).

**Acceptance criteria**
- [ ] For any q in [0, 1], twelve months at q_m compound to q: 1 − (1 − q_m)^12 = q within 1e-12 (§17.1) — `test_monthly_conversion_reproduces_annual_probability`
- [ ] With pinned As-Of 2026-10-01 and DOB 1958-03-01 (age 68), months 0–4 use age 68 and month 5 (2027-03) age 69; q_m equals the conversion of `annual_q` at those ages — `test_monthly_death_probabilities_age_steps_in_birthday_month`
- [ ] Months at ages above 100 use the q(100, b + 100) rate — `test_monthly_death_probabilities_use_age_100_tail`
- [ ] `survival_curve` has length H + 1, starts at 1, is non-increasing and equals the cumulative product of (1 − q_m) — `test_survival_curve_shape_and_monotone`

### F-008.2 Sampling death months
- **Status**: To Do
- **Depends on**: F-008.1

`sample_death_months` (§2 #3–#5 and the precise rule) in `src/sbretire/mortality.py`.

**Acceptance criteria**
- [ ] Result is int64, shape (2, n_paths), every value in 1 … horizon_months — `test_sample_death_months_shape_and_range`
- [ ] Seed 42 (mortality stream) on the example scenario + real table gives pinned death months for 4 paths, computed independently from the uniforms — `test_sample_death_months_seed_42_known_answer`
- [ ] 100,000 paths (seed 11): for k in {12, 120, 240, 360, H}, the share with d ≤ k is within 4 binomial SE of 1 − S_k for each person — `test_sample_death_months_matches_survival_curve`
- [ ] The two people's death months are independent: |corr| < 0.01 over 100,000 paths — `test_sample_death_months_people_independent`
- [ ] A 30-year horizon gives the same death months as a 60-year horizon wherever the 60-year death month < 360 (else 360) — `test_sample_death_months_horizon_stable`
- [ ] A q = 1 table kills every path in month 0 (d = 1); a q = 0 table leaves every path alive (d = H) — `test_sample_death_months_degenerate_tables`

### F-008.3 Deterministic mortality fixture end to end
- **Status**: To Do
- **Depends on**: F-008.2

Integration test through `simulate_paths`; hypothesis invariant; README; THESAURUS.

**Acceptance criteria**
- [ ] Fixture table with q = 0 below a chosen age and q = 1 from it: through `sample_death_months` + `simulate_paths`, alive states move both → one → none at the expected months, `household_end_month` is the later death month, and a fixture with q = 0 throughout is censored (§17.2) — `test_deterministic_mortality_fixture_state_transitions`
- [ ] For any sampled death months, once a person's alive flag is False in some month it stays False in every later month (hypothesis over seeds) (§17.1) — `test_dead_person_never_alive_again`
- [ ] README documents monthly sampling (q_m formula, inverse CDF, death month timing, horizon survivors) — `check: grep -n "q_m" README.md`

## 11. Open Questions

- None. Dependence between the two people's mortality is out of V1 (SPEC §7.2).

## 12. Acceptance Criteria

1. Monthly conversion — `test_monthly_conversion_reproduces_annual_probability`
2. Age steps in birthday month — `test_monthly_death_probabilities_age_steps_in_birthday_month`
3. Age-100 tail — `test_monthly_death_probabilities_use_age_100_tail`
4. Survival curve — `test_survival_curve_shape_and_monotone`
5. Shape and range — `test_sample_death_months_shape_and_range`
6. Seed 42 known answer — `test_sample_death_months_seed_42_known_answer`
7. Matches survival curve — `test_sample_death_months_matches_survival_curve`
8. Independence — `test_sample_death_months_people_independent`
9. Horizon stable — `test_sample_death_months_horizon_stable`
10. Degenerate tables — `test_sample_death_months_degenerate_tables`
11. Deterministic fixture transitions — `test_deterministic_mortality_fixture_state_transitions`
12. Dead never alive again — `test_dead_person_never_alive_again`
13. README — `check: grep -n "q_m" README.md`
