---
id: F-031
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 7
created: 2026-10-18
updated: 2026-10-18
---
# F-031 Account Returns from the Ledger

## 1. Purpose

Measure how each account **actually** did since the first transaction export:
- the **time-weighted return** (TWR): the investments' performance, unaffected by when money went in or out;
- the **money-weighted return** (MWR): the household's own result, including the timing of contributions and
  withdrawals;
- both for each account in its own currency, and for the household in GBP.

The back-test (F-027) applies today's mix to the past. This feature uses what the accounts really held.

How it works:
1. Rebuild each account's **month-end value** backwards from today's holdings, undoing every later transaction
   in the ledger: units and cash.
2. Value the units with the price files.
3. Chain monthly Modified Dietz returns for the TWR.
4. Solve the internal rate of return over the external flows for the MWR.

`sbretire portfolio account-returns` prints and writes the results; `portfolio.json` (1.1) and the Portfolio page
gain an "Actual returns" section.

Split from F-027 at the user's request (2026-10-18). Epic `portfolio-analysis`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Matching | Each ledger security, within its account, is matched to a price series in this order: (1) a series whose new `ledger_names` list holds the ledger row's `security_key` or `security_name`; (2) the account's holding with the same security key (Schwab and ii symbols); (3) the account's holding with the same **normalised name**: lower case, punctuation removed, and trailing share-class words ("acc", "accumulation", "inc", "income", "shares", "class", "gbp", "usd", "fund", "a", single letters) dropped. The holding's series is then the series that prices it. Unmatched securities are listed | HL and Vanguard name securities differently in transactions and holdings | user 2026-10-18 |
| 2 | Rebuilding | For each account, at each month-end *m* from the month before its first ledger row to the last complete month before the valuation date: units of a security = today's units − the sum of its `quantity_change` dated after *m*; cash = today's cash − the sum of all `cash_change` dated after *m*. The end point is today's valuation (F-025) | The exports hold no opening positions (epic) | epic |
| 3 | Pricing | A month-end value is Σ units × the series' month-end price in the **account's currency**, plus cash. Conversions: GBX ÷ 100; a USD quote in a GBP account × that month's GBP=X rate; a GBP quote in a USD account ÷ it. If any security held (units ≠ 0) at any month-end lacks a match or a price, the account's returns are **unavailable**, with the missing securities and months listed | No guessed values | user 2026-10-18 |
| 4 | Flows | External flows (ledger `flow: external`: contributions, tax relief, transfers in and out) are the money in or out. Dividends, interest, fees and internal transfers stay inside the account and so count as return | portfolio-data §4 | portfolio-data §4 |
| 5 | TWR | Each sub-period (month-end to month-end, the last ending at the valuation date) has the Modified Dietz return `(V₁ − V₀ − F) / (V₀ + Σ wᵢFᵢ)`, with `wᵢ` = days from the flow to the period end ÷ days in the period. The sub-periods chain as `Π(1 + r) − 1`, and the total is reported for the period with no annualising when it is under a year | Standard; a short history should not be annualised | this brief |
| 6 | MWR | The rate *r* solving `−V₀ − Σ Fᵢ(1+r)^(−tᵢ) + V_end (1+r)^(−T) = 0`, with times in years from the start (deposits are negative from the household's side). Solved by bracketing (`scipy.optimize.brentq`). Reported as the period's return `(1+r)^T − 1`, and annualised only when T ≥ 1 year. Unavailable if no root is found | Money-weighted = the household's own result | this brief |
| 7 | Currency | Each account in its own currency. The household in GBP: month-end values and flows converted at that month's GBP=X rate (flows at their month's rate). The household is unavailable when any account is unavailable, or a USD account exists without a GBP=X file | User's choice; keeps currency moves out of Schwab's own figure | user 2026-10-18 |
| 8 | Output | `sbretire portfolio account-returns [--root] [--accounts] [--prices] [--output-dir] [--usd-gbp R]` prints a table (account, currency, period, start and end value, net flows, TWR, MWR, months) with reasons for any unavailable account and the unmatched securities. It writes `account_returns.csv` (`account`, `month`, `value`, `external_flow`, `return`; month-end rows, with the household in GBP as `household`). `portfolio.json` becomes **1.1** with an `account_returns` section, and the page gains an "Actual returns" section with a table and a line of month-end values. Exit 0 ok (unavailable accounts reported), 1 unreadable, 2 invalid configuration | Same pattern as the other portfolio commands | this brief |
| 9 | Tests | Synthetic known answers: Modified Dietz with a mid-month deposit; chaining; XIRR on a single deposit grown at a known rate; rebuilding units and cash backwards through buys, sells and fees; matching by key, by normalised name and by `ledger_names`; unavailable with reasons | Closed-form checks | this brief |

## 3. Context

- **F-024:** `build_ledger` provides the rows: `security_key`, `security_name`, `quantity_change`, `cash_change`,
  `flow` and `date`.
- **F-025:** today's `Holding`s and their valuation.
- **F-026:**
  - `load_securities` and `SeriesConfig`; this feature adds `ledger_names`;
  - `read_price_file`, giving month-ends in quote units;
  - `today_values` and the FX file.
- **F-030:** `portfolio.json` (1.0) and the page.
- **Known name differences:**
  - HL: the ledger's names come from the trade description; the holdings use the "Stock" name with footnotes
    removed. They usually match.
  - Vanguard: the holdings' "Investment Name" can be truncated ("… Fund -").

## 4. Touch-points

**New:**
- `src/sbretire/ledger/account_returns.py`: matching, rebuilding, returns, CSV and summary.
- Tests `tests/unit/test_account_returns_*.py`.

**Modified:**
- `src/sbretire/ledger/prices.py`: `ledger_names`.
- `config/securities.example.yaml`.
- `src/sbretire/__main__.py`: `portfolio account-returns`.
- `src/sbretire/ledger/document.py` and `schemas/portfolio.schema.json`: 1.1 and `account_returns`.
- The page (`portfolio.html` / `portfolio-view.js`): the Actual returns section.
- The design sample.
- `README.md`.
- `docs/THESAURUS.md`: Time-Weighted Return, Money-Weighted Return.
- `docs/decisions/portfolio-data.md`: §26–§28.

## 5. Interfaces

```python
# sbretire/ledger/account_returns.py
def normalise_name(name: str) -> str: ...
def match_securities(
    rows, holdings, securities
) -> tuple[
    dict[tuple[str, str], str], list[tuple[str, str]]
]: ...  # (account, ledger key) -> series; unmatched


def units_at(rows, today_units: Mapping[str, float], month_end: dt.date) -> dict[str, float]: ...
def cash_at(rows, today_cash: float, month_end: dt.date) -> float: ...
def modified_dietz(
    v0: float, v1: float, flows: Sequence[tuple[dt.date, float]], start: dt.date, end: dt.date
) -> float: ...
def xirr(
    v0: float, flows: Sequence[tuple[dt.date, float]], v_end: float, start: dt.date, end: dt.date
) -> float | None: ...


@dataclass(frozen=True)
class AccountReturn:
    account: str
    currency: str
    available: bool
    reason: str | None
    start: dt.date | None
    end: dt.date | None
    start_value: float | None
    end_value: float | None
    net_flows: float | None
    twr: float | None
    mwr_period: float | None
    mwr_annual: float | None
    months: list[tuple[dt.date, float, float, float | None]]  # month-end, value, external flow, return
```

## 6. Plan of Work

1. Matching ledger securities to series (with `ledger_names`).
2. Rebuilding month-end units, cash and values; availability with reasons.
3. Returns: Modified Dietz TWR, XIRR MWR, and the household in GBP.
4. The command, the CSV, `portfolio.json` 1.1, the page section, docs, and a real run.

## 7. Validation

- **T1:** known answers for every formula and for rebuilding and matching (§2 #9).
- **T2:** the command on the F-029 synthetic setup (24 months of prices; fixtures whose ledger matches today's
  holdings) gives available accounts with hand-checkable figures. A missing price makes an account unavailable,
  with the reason.
- **T3:** the real exports (`check:`). Without price files every account is unavailable and says why.

## 8. Decision Log

- 2026-10-18 — These come from the user's answers: §2 #1 (auto-matching plus `ledger_names` overrides), #3
  (unavailable when not fully priced) and #7 (each account in its own currency, the household in GBP). The rest
  are mine.

## 9. Surprises

- 2026-10-18 — F-031.2: an unmatched ledger security makes its account unavailable even if it was bought and
  sold inside the period. Its units today are unknown (no holding is matched), so "held at a month-end" cannot
  be decided. The fix for the user is a `ledger_names` entry.

## 10. Tasks

### F-031.1 Matching ledger securities to price series
- **Status**: Verification
- **Depends on**: —

`normalise_name`, `match_securities`, `SeriesConfig.ledger_names`. §2 #1.

**Acceptance criteria**
- [x] A Schwab symbol matches by key; an HL name with a different share-class tail matches by normalised name; a Vanguard ledger name differing from a truncated holdings name matches through `ledger_names`; a sold-out security matches through `ledger_names` without a holding; an unknown one is listed as unmatched — `test_match_securities`

**Notes**
2026-10-18 SeriesConfig.ledger_names; ledger/account_returns.py normalise_name (trailing share-class words and single letters dropped), match_securities (ledger_names in the series' accounts → key → normalised name of holding name or key); tests/unit/test_account_returns_match.py.

### F-031.2 Month-end values rebuilt backwards
- **Status**: Verification
- **Depends on**: F-031.1

`units_at`, `cash_at`, month-end valuation in the account's currency, and availability. §2 #2–#4.

**Acceptance criteria**
- [x] Today 100 units and £50 cash, with a buy of 40 (−£400), a fee (−£5) and a deposit (+£1,000) after a month-end, rebuild to 60 units and £50 + 400 + 5 − 1,000 cash there; GBX, USD-in-GBP and USD-in-USD conversions price as stated; a held security without a price, or unmatched, makes the account unavailable naming it and the months — `test_rebuild_month_end_values`

**Notes**
2026-10-18 account_returns.py month_end, units_at, cash_at, price_in (GBX ÷ 100, USD↔GBP at the month's rate), rebuild (values in the account currency; unmatched ledger securities and unpriced held series listed). Any unmatched ledger security in the account is listed (today's units of an unmatched security are unknown), not only those held at a month-end — recorded in §9. Test assertion split for typing only.

### F-031.3 Time- and money-weighted returns
- **Status**: Verification
- **Depends on**: F-031.2

`modified_dietz`, chaining, `xirr`, the household in GBP. §2 #5–#7.

**Acceptance criteria**
- [x] Modified Dietz with £1,000 deposited halfway through a 30-day period matches the hand value; two sub-periods chain; a single deposit grown at 5% a year for 2 years gives an MWR of 5%, and for 6 months gives the period return 1.05^0.5 − 1 with no annual figure; with no flows the TWR equals the MWR; the household sums the GBP-converted accounts — `test_twr_and_mwr_known_answers`

**Notes**
2026-10-18 account_returns.py modified_dietz, xirr (brentq on −99%…+1,000%, years = days/365), PeriodReturn and returns_for (flows after the first point; MWR annualised only for ≥ 1 year), to_gbp (USD at the month's rate); tests/unit/test_account_returns_twr_mwr.py (assertions split for typing only).

### F-031.4 Command, portfolio.json 1.1, page, docs and a real run
- **Status**: To Do
- **Depends on**: F-031.3

What to build:
- `sbretire portfolio account-returns` and `account_returns.csv`.
- `portfolio.json` 1.1 with the schema and the `account_returns` section.
- The "Actual returns" page section.
- The design sample, README, THESAURUS and `portfolio-data.md` §26–§28.
- A real run.

**Acceptance criteria**
- [ ] On the synthetic setup the command prints each account with TWR, MWR and its period, and an unavailable account with its reason, and writes `account_returns.csv` (UTF-8, LF, columns, month-end rows and household rows); the report's `account_returns` section validates against schema 1.1 and the page renders it (static checks) — `test_cli_account_returns_and_document`
- [ ] README documents the command, `ledger_names` and how the two returns differ; THESAURUS defines Time-Weighted Return and Money-Weighted Return in order; decisions recorded — `check: grep -n "account-returns" README.md docs/decisions/portfolio-data.md`
- [ ] On the real exports the command runs and each account says what it needs (exit 0; run locally, never committed) — `check: uv run sbretire portfolio account-returns --usd-gbp 0.7503`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Matching — `test_match_securities`
2. Rebuilding — `test_rebuild_month_end_values`
3. Returns — `test_twr_and_mwr_known_answers`
4. Command, document, page — `test_cli_account_returns_and_document`
5. Docs — `check: grep -n "account-returns" README.md docs/decisions/portfolio-data.md`
6. Real run — `check: uv run sbretire portfolio account-returns --usd-gbp 0.7503`
