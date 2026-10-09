---
id: F-003
type: feature
parent: household-cash-flows
status: done
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-003 Income Streams

## 1. Purpose

Turn the Scenario's **Income Streams** into the engine's monthly household income for every **Path** at once
(SPEC §8, §4.2): active between start and end dates, **inflation-linked** streams scaled by the **Inflation
Index**, non-linked streams fixed in nominal GBP, and each stream's **Recipient** and **Survivor Percentage**
applied according to who is alive — including **Household Streams** with no individual recipient.

Resolves two SPEC §18 items: behaviour of each income stream after recipient death, and treatment of household-level
income and survivor benefits (configuration §4, §5). Introduces the `PriceIndex` seam that F-004 (spending) and
F-006 (stochastic inflation) build on.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Linked amount | Monthly nominal = `annual_amount_today × I_t / 12`, I indexed from the As-Of month (I = 1 in month 0), including months before `start_date` | SPEC §8: "annual_amount_today multiplied by the simulated cumulative inflation index" | SPEC §6, §8; configuration §4 |
| 2 | Non-linked amount | Monthly nominal = `annual_amount_today / 12`, constant | SPEC §6: "remains at its configured nominal amount" | SPEC §6, §8 |
| 3 | Active months | Pays in month t iff `month_index(start_date) ≤ t < month_index(end_date)`; start before As-Of → pays from month 0; no `end_date` → no end | configuration §3 (exclusive end) | configuration §3 |
| 4 | Person recipient | Recipient alive → full; recipient dead and other alive → × `survivor_percentage`; both dead → path has ended | SPEC §8 | SPEC §8; configuration §4 |
| 5 | Recipient dies before `start_date` | Survivor receives × `survivor_percentage` from `start_date` (nothing before). Streams that die with their owner use `survivor_percentage: 0` | Literal SPEC §8; one rule covers State Pension (0) and DB spouse pensions (> 0) | Interview Q1; configuration §4 |
| 6 | Household Stream | `recipient: household` (reserved; no person may use the id): full while both alive, × `survivor_percentage` while exactly one alive | Reuses one field with one meaning — "what continues after a death" | Interview Q2; configuration §5 |
| 7 | Price index seam | `PriceIndex` protocol, `level(month) -> FloatArray` (n_paths,), I = 1 at month 0; `FlatPriceIndex` = zero inflation | Per-month seam like the engine's (bounded memory); exact tests; F-006 plugs in | Interview Q3 |
| 8 | Month indexing | `timeline.month_index(as_of, when) = (when.year − as_of.year)·12 + (when.month − as_of.month)` | One shared date→month rule for all features | Brief author, confirmed |
| 9 | Placement | `sbretire/income.py` (`ScenarioIncome`), `sbretire/inflation.py` (seam), `sbretire/timeline.py`; F-004 composes income + spending into the engine's `HouseholdCashFlows` | Module per SPEC §3 responsibility | SPEC §3 |

## 3. Context

- `sbretire.config` validates streams (dates on the 1st, exclusive end, recipient ∈ people ids).
- `sbretire.simulation.simulate_paths` asks a `HouseholdCashFlows` for `income(month, alive)` with
  `alive: bool[2, n_paths]` (person order = `scenario.people` order).
- Constraints: vectorised over paths (loop over the few streams is fine; never over paths); nominal GBP internally;
  no inflation process here (F-006).

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/timeline.py` | `month_index` |
| `src/sbretire/inflation.py` | `PriceIndex` protocol, `FlatPriceIndex` |
| `src/sbretire/income.py` | `ScenarioIncome` |
| `tests/unit/test_timeline.py`, `tests/unit/test_inflation.py`, `tests/unit/test_income.py` | unit tests |
| `tests/integration/test_income_end_to_end.py` | engine + income agreement (T2) |

**Modified**

| File | Change |
|---|---|
| `src/sbretire/config.py` | `recipient` may be `household`; person id `household` rejected |
| `tests/unit/test_config_consistency.py` | household recipient tests |
| `README.md` | configuration rules: household streams, survivor behaviour |

**Deleted:** none.

## 5. Interfaces

```python
# sbretire.timeline
def month_index(as_of: date, when: date) -> int: ...  # months from the As-Of month; negative before it


# sbretire.inflation
class PriceIndex(Protocol):
    def level(self, month: int) -> FloatArray: ...  # I_t per path, shape (n_paths,); I = 1 at month 0


class FlatPriceIndex:  # zero inflation
    def __init__(self, n_paths: int) -> None: ...
    def level(self, month: int) -> FloatArray: ...  # all ones


# sbretire.income
HOUSEHOLD = "household"


class ScenarioIncome:
    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None: ...
    def income(self, month: int, alive: BoolArray) -> FloatArray: ...  # nominal GBP this month, (n_paths,)
```

Per month: for each stream active at t, `amount = annual/12 × (I_t if linked else 1)`;
`factor` = person stream: `1` where recipient alive, `survivor_percentage` where recipient dead and other alive,
`0` where both dead; household stream: `1` where both alive, `survivor_percentage` where exactly one alive, `0` where
none. Sum `amount × factor` over streams.

## 6. Plan of Work

1. `timeline.month_index`; `inflation.PriceIndex` + `FlatPriceIndex`.
2. Config: allow `recipient: household`; reserve the id.
3. `ScenarioIncome` with the rules in §5.
4. End-to-end check through `simulate_paths`; README configuration rules.

## 7. Validation

- **T1** — unit tests per AC; ruff; mypy --strict.
- **T2** — `tests/integration/test_income_end_to_end.py`: fixture scenario, `FlatPriceIndex`, zero return, zero
  spending, fixed Death Months → final balance = starting balance + hand-computed income total.
- **T3** — n/a (no randomness yet).

## 8. Decision Log

- 2026-10-09 — Interview Q1–Q3 settled decisions 5–7; decisions 1–4 from SPEC §6/§8 and configuration §3; decision 8–9 proposed by brief author and confirmed. Recorded configuration §4 (recipient death, linking base) and §5 (household streams); thesaurus gains Household Stream, Recipient updated.

## 9. Surprises

- 2026-10-09 — The per-file ruff hook and the full gate sorted `sbretire` imports differently in tests (first-party detection depends on the path ruff is given); fixed by pinning `known-first-party` / `known-local-folder` in pyproject (separate chore commit).
- 2026-10-09 — /verify noted `ScenarioIncome` checks the price index's path count only in months where a stream pays (early return otherwise). Harmless — nothing is read from the index then — but F-004/F-006 should validate the index shape once at construction instead.

## 10. Tasks

Task format and statuses: `docs/project-sdlc.md` §2. Definition of done: `docs/project-sdlc.md` §4.

### F-003.1 Timeline and price-index seam
- **Status**: Done
- **Depends on**: —

`src/sbretire/timeline.py` (`month_index`) and `src/sbretire/inflation.py` (`PriceIndex`, `FlatPriceIndex`) — brief
§2 #7–#8, §5. Tests in `tests/unit/test_timeline.py`, `tests/unit/test_inflation.py`.

**Acceptance criteria**
- [x] `month_index` is 0 for the As-Of month, counts calendar months across year ends, and is negative before the As-Of month — `test_month_index_counts_calendar_months`
- [x] Zero inflation keeps the price index constant at 1 for every path and month — `test_flat_price_index_is_constant`

**Notes**
- 2026-10-09: `src/sbretire/timeline.py` (`month_index`), `src/sbretire/inflation.py` (`PriceIndex` protocol; `FlatPriceIndex` returns one shared read-only array of ones). Tests: `tests/unit/test_timeline.py` (8 cases), `tests/unit/test_inflation.py`.
- 2026-10-09 /verify PASS:
  - test_timeline.py + test_inflation.py: 9 passed; year boundary, multi-year and negative months covered
  - probe: month_index(2026-10-01, 2030-02-01) = 40; FlatPriceIndex array is read-only, later calls unaffected
  - docstrings state I = 1 at the As-Of month; no randomness or network; ruff + mypy clean

### F-003.2 Household recipient in config
- **Status**: Done
- **Depends on**: —

`src/sbretire/config.py`: `income[].recipient` may be `household`; a person whose `id` is `household` is rejected
(brief §2 #6). Tests added to `tests/unit/test_config_consistency.py`.

**Acceptance criteria**
- [x] A stream with `recipient: household` validates — `test_household_recipient_accepted`
- [x] A person with id `household` is rejected at `people[i].id` — `test_household_is_reserved_person_id`

**Notes**
- 2026-10-09: `src/sbretire/config.py` — `HOUSEHOLD = "household"` constant; consistency rules reject a person id `household` ("is reserved for household-level income streams") and accept `recipient: household`; recipient error now lists the ids and `'household'`. Tests added to `tests/unit/test_config_consistency.py`.
- 2026-10-09 /verify PASS:
  - test_config_consistency.py: 14 passed (no regression in earlier rules)
  - probe: 'Household' (capitalised) and 'nobody' rejected at income[0].recipient; message lists 'household'
  - matches configuration §5 and thesaurus Household Stream / Recipient; ruff + mypy clean

### F-003.3 ScenarioIncome
- **Status**: Done
- **Depends on**: F-003.1, F-003.2

`src/sbretire/income.py`: `ScenarioIncome(scenario, price_index).income(month, alive)` per brief §2 #1–#6, §5.
Tests in `tests/unit/test_income.py` with a scripted test `PriceIndex`.

**Acceptance criteria**
- [x] Inflation-linked income tracks the index (amount × I_t / 12), including a stream starting after the As-Of month — `test_linked_income_tracks_price_index`
- [x] Non-linked income stays at annual_amount_today / 12 nominal whatever the index — `test_unlinked_income_is_nominally_constant`
- [x] Income starts in its start month (month 0 if it started earlier) and stops at its exclusive end month — `test_income_starts_and_ends_on_configured_dates`
- [x] Survivor percentage applies only when the recipient has died and the other person is alive; full while the recipient lives, whoever else has died — `test_survivor_percentage_applies_only_after_recipient_death`
- [x] A recipient who dies before start_date leaves the survivor × survivor_percentage from start_date, nothing before — `test_recipient_dying_before_start_pays_survivor_from_start`
- [x] A household stream pays in full while both are alive and × survivor_percentage while one is alive — `test_household_stream_survivor_rule`
- [x] Streams sum per path with paths in different alive states evaluated together — `test_income_sums_streams_per_path`

**Notes**
- 2026-10-09: `src/sbretire/income.py` — `ScenarioIncome` precomputes per-stream rules (start/end month indices, monthly today's-GBP amount, linking, survivor %, recipient row or household); `income()` loops over the few paying streams, vectorised over paths, and validates that the price index covers the same paths. Tests: `tests/unit/test_income.py` (9, incl. no-streams and index-shape cases).
- 2026-10-09 /verify PASS:
  - test_income.py: 9 passed; every expected value recomputed from the fixture (pension month 3, annuity end month 162)
  - code matches configuration §4–§5 and SPEC §8; loops only over streams, numpy over paths
  - probe with index 1.5: month 3 all alive [2000, 2000]; sam dead [1500, 1500]; month 162 [1500, 1500]
  - ruff + mypy clean; no network/tax

### F-003.4 End-to-end income check
- **Status**: Done
- **Depends on**: F-003.3

`tests/integration/test_income_end_to_end.py` (T2) and README configuration rules for income (brief §7).

**Acceptance criteria**
- [x] With zero return and zero spending, the engine's final balance equals the starting balance plus a hand-computed income total over fixed Death Months — `test_income_end_to_end_matches_hand_total`
- [x] README documents household streams and the survivor rule — `check: grep -n "recipient: household" README.md`

**Notes**
- 2026-10-09: `tests/integration/test_income_end_to_end.py` — 3 paths (alex dies first, sam dies first, both censored) with zero return/spending; final balances equal hand totals and household end months match. It exercises existing F-003.3 behaviour, so it passed on first run (no red phase). README gains an "Income streams" section (linking from as-of, survivor percentage incl. death before start, `recipient: household`).
- 2026-10-09 /verify PASS:
  - test_income_end_to_end.py: passed; totals 240000 / 447000 / 798000 re-derived independently
  - README 'Income streams' section agrees with configuration §4–§5
  - ruff + mypy clean

## 11. Open Questions

- A survivor's pension that starts at the death rather than at `start_date` (some DB schemes) is not modelled; revisit if a real scheme needs it (would add an optional per-stream field).

## 12. Acceptance Criteria

1. Month indexing — `test_month_index_counts_calendar_months`
2. Zero inflation keeps index constant — `test_flat_price_index_is_constant`
3. Household recipient accepted — `test_household_recipient_accepted`
4. `household` reserved as person id — `test_household_is_reserved_person_id`
5. Linked income tracks index — `test_linked_income_tracks_price_index`
6. Non-linked constant — `test_unlinked_income_is_nominally_constant`
7. Start/end dates — `test_income_starts_and_ends_on_configured_dates`
8. Survivor % condition — `test_survivor_percentage_applies_only_after_recipient_death`
9. Death before start — `test_recipient_dying_before_start_pays_survivor_from_start`
10. Household survivor rule — `test_household_stream_survivor_rule`
11. Per-path summation — `test_income_sums_streams_per_path`
12. Engine + income agree — `test_income_end_to_end_matches_hand_total`
13. README rules — `check: grep -n "recipient: household" README.md`
