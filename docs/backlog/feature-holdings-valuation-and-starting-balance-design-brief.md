---
id: F-025
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 5
created: 2026-10-18
updated: 2026-10-18
---
# F-025 Holdings Valuation and Starting Balance

## 1. Purpose

Read each account's holdings export from the newest month folder and say **what the household's savings are worth
today**:

- one household total in GBP, ready to paste as `portfolio.starting_balance` (SPEC §4.2);
- split by account and by person;
- every account's valuation date, and the exchange rate used for USD.

`sbretire portfolio value` prints the figures and the ready-to-paste YAML line, and writes
`output/portfolio/holdings.csv`. It never edits the personal model config (epic scope). Later features use the same
holdings: performance (F-027), look-through (F-028) and the frontier (F-029).

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Which exports | The holdings exports in the **newest** `<mon>-<yy>` folder, found with each account's `holdings` patterns. An account with no matching file there is an error naming the account and folder | Holdings are snapshots; older folders are history, not today | epic; this brief |
| 2 | USD→GBP | `--usd-gbp R` (GBP per USD, > 0) converts every USD account; it is required when any account is not GBP (exit 2 otherwise). The rate is printed and written to `holdings.csv`. Where an export states its own rate (HL's footer "x USD to 100 pence … at <date>"), the summary prints it beside the given rate and warns if they differ by more than 2% | No export carries Schwab's rate; F-026 may later default it from the FX file | user 2026-10-18 |
| 3 | Valuation dates | Each account keeps its export's own date (Schwab title, HL "Spreadsheet created at", Vanguard `Valuation Date`). ii states none: it takes the newest date stated by the other holdings exports in the same folder and is marked **assumed**. The summary lists each date and warns when they span more than 7 days | Exports are taken on different days; nothing is hidden | user 2026-10-18 |
| 4 | Cash | Cash is a holding row of kind `cash`: Schwab "Cash & Cash Investments", HL "Total cash", Vanguard "GBP Cash" rows. ii's holdings file has no cash, so its cash is the latest stated running balance in the account's transactions export in the same folder; no such balance is an error | Starting balance includes cash (epic) | epic |
| 5 | Shared Vanguard file | A new optional account field `holdings_filter` keeps the holdings rows whose `Product Wrapper` equals it (`Stocks & Shares ISA`, `Personal Pension`); the transactions `filter` is unchanged | The holdings file is shared but labels wrappers differently from the transactions | this brief |
| 6 | Holding row | `account`, `owner`, `wrapper`, `valuation_date`, `date_stated` (false when assumed), `kind` (`security` or `cash`), `security_key` (symbol, code or fund name; empty for cash), `security_name`, `quantity`, `price` (per unit in the account's currency, pounds never pence), `value` (account currency), `currency`, `source_file` (`<folder>/<file>`), `source_row` | One shape for every provider, like the ledger | this brief |
| 7 | Values used | Schwab `Mkt Val`; HL `Value (£)` (US stocks already converted by HL), with `Price (pence)` / 100; Vanguard `Current Value (GBP)`; ii `Market Value (£)` with price = value / quantity (ii's `Price` and `Market Value` are in the listing currency) | Each provider's own valuation in the account's currency | export layouts |
| 8 | Self-checks | Schwab: securities + cash = "Positions Total". HL: securities = "Stock value", securities + cash = "Total value". Each to a penny; a mismatch stops with exit 2 naming the file and both figures | Proves the parser against the provider's arithmetic, as F-024 does for cash | this brief |
| 9 | Totals | GBP value = value × rate (1 for GBP). Printed per account (securities, cash, total, date), per person (owner) and for the household. The YAML line is the household total rounded to the nearest pound: `starting_balance: 1234567` under `portfolio:`, with a comment naming the folder and dates | What the user pastes into `config/model.yaml` | epic |
| 10 | Output | `sbretire portfolio value [--root data/transactions] [--accounts config/accounts.yaml] [--output-dir output] [--usd-gbp R]` writes `output/portfolio/holdings.csv` (UTF-8, LF, the §5 columns plus `fx_rate`, `value_gbp`). Exit 0 ok, 1 unreadable, 2 invalid | Same pattern as `portfolio import` | this brief |
| 11 | Tests | Synthetic fixtures copying each layout (title lines, preamble and footer, `$`, pence, `--`, `®`, doubled `.csv.csv`, cp1252); real exports never read by tests | Personal data stays out of the repo | portfolio-data; epic risk |

## 3. Context

- **F-024** gives `AccountConfig` (with `holdings` patterns), `month_folders`, the transaction parsers and the
  ledger's `stated_balance` (ii cash). Parsers live in `src/sbretire/ledger/parsers/<provider>.py`; each gains a
  `parse_holdings` beside `parse`.
- **Holdings layouts (October 2026, digits masked):** the epic's "Holdings export formats". Also seen while
  briefing:
  - Schwab: title `"Positions for account … as of <h:mm> AM ET, <yyyy/mm/dd>"`, a blank line, then the table; each
    row ends with a trailing comma; `Qty (Quantity)` has thousands separators.
  - HL: rows of the table are quoted; the table ends at a blank line followed by footnotes, the last giving the
    USD rate "`<x>`USD to 100 pence. Exchange rate correct at `<dd/mm/yyyy>`".
  - ii: `Price` and `Market Value` are in the listing currency (USD for some ETFs); `Market Value (£)` is GBP.
  - Vanguard: decoded as UTF-8 (the `®` is UTF-8 here, unlike the transactions).
- `_common.read_text` already decodes UTF-8 then cp1252 and strips BOMs; `money` handles `$`, `£`, commas, `--`.

## 4. Touch-points

**New:** `src/sbretire/ledger/holdings.py` (`Holding`, `HOLDING_COLUMNS`, `HoldingsError`), `src/sbretire/ledger/valuation.py`
(`read_holdings`, `value_holdings`, `Valuation`, summary and CSV), synthetic fixtures
`tests/fixtures/accounts/{schwab-positions.csv,hl-account-summary.csv,vanguard-holdings.csv.csv,ii_holdings.csv}`,
tests `tests/unit/test_holdings_*.py`.

**Modified:** `src/sbretire/ledger/parsers/{schwab,hl,vanguard,ii}.py` (`parse_holdings`),
`src/sbretire/ledger/accounts.py` (`holdings_filter`), `config/accounts.example.yaml`, `src/sbretire/__main__.py`
(`portfolio value`), `README.md`, `docs/THESAURUS.md` (Holding, Valuation Date), `docs/decisions/portfolio-data.md`
(§7–§10).

## 5. Interfaces

```python
# sbretire/ledger/holdings.py
HoldingKind = Literal["security", "cash"]


@dataclass(frozen=True)
class Holding:
    account: str
    owner: str
    wrapper: str
    valuation_date: dt.date | None  # None until assigned (ii)
    date_stated: bool
    kind: HoldingKind
    security_key: str
    security_name: str
    quantity: float
    price: float | None
    value: float  # account currency
    currency: str
    source_file: str
    source_row: int


@dataclass(frozen=True)
class HoldingsExport:
    holdings: list[Holding]
    stated_fx: tuple[float, dt.date] | None = None  # GBP per USD and its date, where the export states one


class HoldingsError(ValueError): ...  # file, what failed, both figures


# sbretire/ledger/parsers/<provider>.py
def parse_holdings(path: Path, account: AccountConfig) -> HoldingsExport: ...


# sbretire/ledger/valuation.py
@dataclass(frozen=True)
class Valuation:
    folder: str
    holdings: list[Holding]  # dates assigned
    usd_gbp: float | None
    stated_fx: list[tuple[str, float, dt.date]]  # (file, GBP per USD, date)
    warnings: list[str]

    def total_gbp(self) -> float: ...
    def by_account(self) -> dict[str, tuple[float, float]]: ...  # (securities, cash) in GBP
    def by_owner(self) -> dict[str, float]: ...


def read_holdings(root: Path, accounts: Sequence[AccountConfig]) -> tuple[str, list[HoldingsExport]]: ...
def value_holdings(folder: str, exports: Sequence[HoldingsExport], usd_gbp: float | None) -> Valuation: ...
def write_holdings_csv(valuation: Valuation, path: Path) -> None: ...
def format_valuation(valuation: Valuation, accounts: Sequence[AccountConfig]) -> str: ...
```

`holdings.csv` columns: the `Holding` fields in order, then `fx_rate`, `value_gbp`.

## 6. Plan of Work

1. `Holding`, `holdings_filter`, Schwab and HL holdings parsers with their self-checks and HL's stated rate.
2. Vanguard and ii holdings parsers; ii cash from the transactions' running balance.
3. Valuation: newest folder, date assignment and spread warning, USD conversion and rate check, totals,
   `holdings.csv`, `sbretire portfolio value`.
4. Docs and the real October run.

## 7. Validation

- **T1:** each holdings parser on its synthetic fixture gives hand-checked rows; self-check mismatches raise with
  file and figures; `holdings_filter` splits the Vanguard file.
- **T2:** two synthetic month folders: only the newest is valued; totals by account, person and household equal
  hand sums; USD converted at the given rate; missing `--usd-gbp` exits 2; ii's date is assumed.
- **T3:** the real October 2026 exports value without error (manual `check:`; never in tests).

## 8. Decision Log

- 2026-10-18 — §2 #2 and #3 from the user's answers (`--usd-gbp` flag; per-account dates, ii assumed, 7-day
  warning). The rest by me from the epic and the export layouts.
- 2026-10-18 — F-025.3: where an account's pattern matches several files in the folder, the last by name is used
  (provider names carry the date and time). Any export without a cash line takes its cash from the account's
  transactions in the same folder (only ii today). A holdings file read by two accounts needs `holdings_filter`
  on each. Amounts print as `1,234.56 GBP`, like the rest of the CLI, not with `£` (the test's expected text was
  changed to match; the figures are unchanged).

## 9. Surprises

- 2026-10-18 — While briefing: ii's holdings `Price` and `Market Value` are in the listing currency (a ratio of
  about 1.33 to `Market Value (£)` for USD lines), so only `Market Value (£)` is used. HL's footer states its own
  USD rate and date, which gives a free cross-check on `--usd-gbp`.
- 2026-10-18 — F-025.1: the real HL table ends with a `"","Totals",…` row (empty code) that was first read as a
  holding, doubling the securities; the Stock value check caught it. That row is now a third self-check
  (securities = Totals), and the fixture gained it.
- 2026-10-18 — F-025.2: without `holdings_filter`, each Vanguard account read the whole shared holdings file, so
  both wrappers' holdings would have been counted twice. F-025.3's valuation therefore refuses a holdings file
  matched by two accounts unless each sets `holdings_filter`.

## 10. Tasks

### F-025.1 Holding model, Schwab and HL holdings
- **Status**: Verification
- **Depends on**: —

`ledger/holdings.py`, `AccountConfig.holdings_filter`, `parsers/schwab.py::parse_holdings` (title date, cash row,
Positions Total check), `parsers/hl.py::parse_holdings` (created-at date, Total cash, pence, Stock value and Total
value checks, footer rate). §2 #4–#8.

**Acceptance criteria**
- [x] A synthetic Schwab positions export parses to hand-checked security and cash rows dated from the title, and a total that does not add up raises `HoldingsError` naming the file and both figures — `test_schwab_holdings_parse_and_check_total`
- [x] A synthetic HL account summary (cp1252, preamble, footnotes) parses to hand-checked rows with prices in pounds, a cash row from "Total cash", the created-at date and the footer's USD rate; a wrong "Stock value" raises — `test_hl_holdings_parse_and_check_totals`

**Notes**
2026-10-18 ledger/holdings.py (Holding, HOLDING_COLUMNS, HoldingsExport, HoldingsError), AccountConfig.holdings_filter, parsers/schwab.py::parse_holdings (title date, cash line, Positions Total check), parsers/hl.py::parse_holdings (created-at date, Total cash, pence, Stock value / Totals row / Total value checks, footer rate); tests/unit/test_holdings_schwab_hl.py (2). Real Schwab and HL exports parse and pass every check.

### F-025.2 Vanguard and ii holdings
- **Status**: Verification
- **Depends on**: F-025.1

`parsers/vanguard.py::parse_holdings` (`holdings_filter` on `Product Wrapper`, GBP Cash rows),
`parsers/ii.py::parse_holdings` (`Market Value (£)`, price = value / quantity, no date, no cash), and the ii cash
row from the ledger's latest stated balance. §2 #4, #5, #7.

**Acceptance criteria**
- [x] The synthetic shared Vanguard holdings file yields each wrapper's rows only, with cash rows of kind `cash` and the stated valuation date — `test_vanguard_holdings_filter_by_wrapper`
- [x] A synthetic ii holdings file parses to hand-checked GBP rows with no date; its cash comes from the latest stated running balance of the account's transactions export, and is an error when there is none — `test_ii_holdings_values_in_gbp_and_cash_from_ledger`

**Notes**
2026-10-18 parsers/vanguard.py::parse_holdings (holdings_filter on Product Wrapper, GBP Cash rows), parsers/ii.py::parse_holdings (Market Value (£), price = value / quantity, no date) and cash_from_transactions (newest stated running balance); holdings_filter added to config/accounts.example.yaml; tests/unit/test_holdings_vanguard_ii.py (2). Real Vanguard ISA/pension and ii holdings parse.

### F-025.3 Valuation, holdings.csv and `sbretire portfolio value`
- **Status**: Verification
- **Depends on**: F-025.2

`ledger/valuation.py` and the `portfolio value` command: newest folder, missing-export error, date assignment and
spread warning, `--usd-gbp` conversion with the stated-rate check, totals, YAML line, `holdings.csv`. §2 #1–#3,
#9, #10.

**Acceptance criteria**
- [x] With two synthetic month folders only the newest is valued; account, person and household GBP totals equal hand sums with USD at the given rate; ii's date is the newest stated date and marked assumed; dates over 7 days apart and a stated rate more than 2% from `--usd-gbp` each warn — `test_value_holdings_totals_dates_and_fx`
- [x] `sbretire portfolio value` prints the per-account table, per-person totals, the household total and the `starting_balance` line, and writes `holdings.csv` (UTF-8, LF, columns); without `--usd-gbp` for a USD account, or with an account missing its export, it exits 2 with the reason — `test_cli_portfolio_value`

**Notes**
2026-10-18 ledger/valuation.py (read_holdings: newest folder, missing-export and shared-file checks, cash from transactions where an export has none; value_holdings: assumed dates, USD rate, 7-day and 2% warnings; Valuation totals; holdings.csv; format_valuation), `sbretire portfolio value` in __main__.py; tests/unit/test_holdings_valuation.py (3). Real October run at 0.7503: 42 rows, five accounts, exit 0.

### F-025.4 Docs and the real October run
- **Status**: To Do
- **Depends on**: F-025.3

README section, THESAURUS (Holding, Valuation Date), `docs/decisions/portfolio-data.md` §7–§10 from §2,
`config/accounts.example.yaml` `holdings_filter` entries; run on the real exports locally.

**Acceptance criteria**
- [ ] README documents `portfolio value`, `--usd-gbp` and the pasted line; THESAURUS defines Holding and Valuation Date; decisions recorded — `check: grep -n "portfolio value" README.md docs/decisions/portfolio-data.md`
- [ ] The real October 2026 exports value without error, every self-check passes, and the household total is printed (run locally; never committed) — `check: uv run sbretire portfolio value --usd-gbp <rate>`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Schwab holdings — `test_schwab_holdings_parse_and_check_total`
2. HL holdings — `test_hl_holdings_parse_and_check_totals`
3. Vanguard holdings — `test_vanguard_holdings_filter_by_wrapper`
4. ii holdings and cash — `test_ii_holdings_values_in_gbp_and_cash_from_ledger`
5. Valuation — `test_value_holdings_totals_dates_and_fx`
6. CLI — `test_cli_portfolio_value`
7. Docs — `check: grep -n "portfolio value" README.md docs/decisions/portfolio-data.md`
8. Real exports — `check: uv run sbretire portfolio value --usd-gbp <rate>`
