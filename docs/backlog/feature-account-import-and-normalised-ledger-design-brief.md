---
id: F-024
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 6
created: 2026-10-18
updated: 2026-10-18
---
# F-024 Account Import and Normalised Ledger

## 1. Purpose

Read the household's monthly transaction exports from four providers (five accounts) into **one normalised
Ledger**. Every later portfolio feature works from that ledger: valuation (F-025), returns (F-026), performance
(F-027), look-through (F-028) and the frontier (F-029). Each transaction gets:

- one vocabulary of types;
- signed quantity and cash changes;
- its account, owner and wrapper;
- a flag saying whether it is money entering or leaving the household (an External Flow) or a move inside an
  account (an Internal Transfer).

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Accounts | A git-ignored `config/accounts.yaml` lists each account: `id`, `name`, `provider` (parser: `schwab`, `hl`, `vanguard`, `ii`), `owner` (a person id from the model config), `wrapper` (`taxable`, `isa`, `pension`, `sipp`), `currency`, and file-name patterns for its transaction and holdings exports. For a shared file, a `filter` selects its rows (Vanguard's `Account` column). A committed `config/accounts.example.yaml` shows the layout with made-up values | Personal facts stay out of code and git; patterns survive provider file names | user 2026-10-18 |
| 2 | Folders | Exports live in `data/transactions/<mon>-<yy>/` (e.g. `oct-26` = 2026-10); the importer reads every such folder | Matches the user's monthly routine | user 2026-10-18 |
| 3 | Overlap | Every folder is read; rows are de-duplicated on a fingerprint (account, date, type, security key, quantity, cash, reference). For equal fingerprints the newest folder's row is kept, and true repeats within one file are kept | Exports repeat the year so far | user 2026-10-18 |
| 4 | Unknown types | Import stops with an error naming the file, row number and unknown type or description; no row is ever guessed | Nothing silently misclassified | user 2026-10-18 |
| 5 | Flows | Each row has `flow`: `external` (bank transfers, contributions, tax relief, transfers in or out of the household), `internal` (moves inside one account, e.g. HL SIPP income account to capital account) or `none` (trades, income, fees, tax, corporate actions) | Performance must exclude external flows and net internal ones | user 2026-10-18 |
| 6 | Ledger row | `account`, `owner`, `wrapper`, `date` (trade date), `settle_date` (or empty), `type`, `flow`, `security_key` (provider's symbol, SEDOL or fund name), `security_name`, `quantity_change` (units, signed: + received), `price` (per unit, native currency, pounds not pence), `cash_change` (native currency, signed: + into the account's cash), `fees`, `currency`, `reference`, `source_file`, `source_row` | One shape for every provider; security and cash legs kept apart | this brief |
| 7 | Types | `buy`, `sell`, `dividend`, `interest`, `fee`, `tax_withheld`, `contribution`, `tax_relief`, `transfer_in`, `transfer_out`, `internal_transfer`, `corporate_action`. The per-provider mapping is a table in each parser (§5) | Small fixed vocabulary for analysis | this brief |
| 8 | Two-leg exports | Vanguard writes an Investment record (units) and a Cash record (money) for one event; both are kept as rows: the investment row carries `quantity_change` with `cash_change` 0, the cash row the cash | No double counting; cash reconciles to the export's running balance | this brief |
| 9 | Reconciliation | Where an export states a running cash balance (Vanguard `Cash Balance`, ii `Running Balance`), the importer checks that the ledger's cumulative cash for that account equals it at every stated row, and reports any break with the row | Proves the parser before anything uses it | this brief |
| 10 | Currency | Rows keep their native currency (Schwab USD). No conversion in F-024 (F-026 brings USD/GBP) | One concern per feature | epic |
| 11 | Output | `sbretire portfolio import [--root data/transactions] [--accounts config/accounts.yaml] [--output-dir output]` writes `output/portfolio/ledger.csv` and prints a per-account summary: rows, date range, counts by type, external flows in and out, reconciliation result | A ledger the user can open; checks visible | this brief |
| 12 | Tests | Only synthetic fixtures in `tests/fixtures/accounts/` that copy each provider's layout (encoding, preamble, quoting, BOMs, pence, `$`, `n/a`) with invented rows; real exports are never read by tests | Personal data stays out of the repo | epic risk |
| 13 | Holdings exports | Patterns are configured now; the parsing is F-025 | Feature boundary | epic |

## 3. Context

- **Structure of the October 2026 exports:** the epic's "Format notes" and "Holdings export formats".
- **HL:**
  - Trades are only in the description ("<name> <qty> @ <price>"); direction comes from the sign of `Value (£)`,
    and unit cost is in pence.
  - Descriptions can contain commas inside quoted fields.
  - Interest lines read "Interest From <d/m/y> TO <d/m/y>".
  - Internal lines read "Transfer from Income Account" / "HL SIPP To A/C <code>".
- **ii:** "<qty> <issuer> Del <price> S Date <d/m/y>" is a purchase settled into the account; "Trf from <provider>"
  is a transfer in; "Total Monthly Fee" is a fee.
- **Schwab:** Buy, Sell, Qualified Dividend, Credit Interest, Foreign Tax Paid, ADR Mgmt Fee, Cash Merger, Cash
  Merger Adj, MoneyLink Transfer.
- **Vanguard:** Buy, Sell (Fee), Account Fee, Interest, Deposit, Contribution, Tax Relief, with Record Type Cash or
  Investment.
- **Existing pieces:** the CLI has `validate`, `preview` and `run` (`__main__.py`); `config.py` has the strict
  pydantic style to reuse.

## 4. Touch-points

**New:**
- `src/sbretire/ledger/` with `__init__.py`, `accounts.py` (accounts config), `model.py` (`LedgerRow`, types,
  flows), `parsers/{schwab,hl,vanguard,ii}.py`, `merge.py` (folders, fingerprints, de-duplication),
  `reconcile.py`;
- `config/accounts.example.yaml`;
- synthetic fixtures under `tests/fixtures/accounts/`;
- tests in `tests/unit/test_ledger_*.py`;
- `docs/decisions/portfolio-data.md`.

**Modified:** `src/sbretire/__main__.py` (`portfolio import`), `README.md`, `docs/THESAURUS.md` (Account, Wrapper,
Ledger, External Flow, Internal Transfer), `CHANGELOG.md`.

## 5. Interfaces

```python
# sbretire/ledger/model.py
TransactionType = Literal[
    "buy",
    "sell",
    "dividend",
    "interest",
    "fee",
    "tax_withheld",
    "contribution",
    "tax_relief",
    "transfer_in",
    "transfer_out",
    "internal_transfer",
    "corporate_action",
]
Flow = Literal["external", "internal", "none"]


@dataclass(frozen=True)
class LedgerRow:
    account: str
    owner: str
    wrapper: str
    date: date
    settle_date: date | None
    type: TransactionType
    flow: Flow
    security_key: str
    security_name: str
    quantity_change: float
    price: float | None
    cash_change: float
    fees: float
    currency: str
    reference: str
    source_file: str
    source_row: int

    def fingerprint(self) -> tuple[object, ...]: ...


LEDGER_COLUMNS: Final[tuple[str, ...]]


# sbretire/ledger/accounts.py
class AccountConfig(BaseModel):  # id, name, provider, owner, wrapper, currency,
    ...  # transactions: list[str], holdings: list[str], filter: str | None


def load_accounts(path: Path) -> list[AccountConfig]: ...


# sbretire/ledger/parsers/<provider>.py
def parse(path: Path, account: AccountConfig) -> list[LedgerRow]: ...  # raises UnknownTransaction


# sbretire/ledger/merge.py
def month_folders(root: Path) -> list[tuple[date, Path]]: ...  # "oct-26" -> 2026-10-01
def build_ledger(root: Path, accounts: Sequence[AccountConfig]) -> list[LedgerRow]: ...


# sbretire/ledger/reconcile.py
def reconcile_cash(rows: Sequence[LedgerRow], balances: Sequence[StatedBalance]) -> list[str]: ...  # problems
```

Provider type maps (each unknown value raises `UnknownTransaction`):

| Provider | Source | → type / flow |
|---|---|---|
| Schwab | Buy / Sell | buy / sell |
| Schwab | Qualified Dividend; Credit Interest | dividend; interest |
| Schwab | Foreign Tax Paid; ADR Mgmt Fee | tax_withheld; fee |
| Schwab | Cash Merger; Cash Merger Adj | corporate_action (cash leg; units removed) |
| Schwab | MoneyLink Transfer | transfer_out / transfer_in by sign, flow external |
| HL | reference `B…` / `S…` ("<name> <qty> @ <price>") | buy / sell |
| HL | reference `INTEREST` ("Interest From … TO …") | interest |
| HL | reference `Transfer` ("Transfer from Income Account") | internal_transfer, flow internal |
| HL | reference `MANAGE FEE` ("HL SIPP To A/C …") | fee |
| HL | reference `ID TFC` ("Income Drawdown Tax Free Cash … to Bank") | transfer_out, flow external |
| HL | reference `BACS` ("Sipp Transfer (BACS)") | transfer_in, flow external |
| HL | reference `TRANSFER` ("Product Transfer HL SIPP Income Drawdown") | internal_transfer, flow internal |
| Vanguard | Buy; Sell (Fee) | buy; sell (units sold to pay a fee) |
| Vanguard | Account Fee; Interest | fee; interest |
| Vanguard | Deposit; Contribution; Tax Relief | contribution, contribution, tax_relief; flow external |
| ii | "… Del … S Date …" | buy |
| ii | "Trf from <provider>" | transfer_in, flow external |
| ii | "Total Monthly Fee" | fee |

## 6. Plan of Work

1. Accounts config and month folders.
2. Ledger model and the Schwab parser.
3. HL parser.
4. Vanguard and ii parsers with cash reconciliation.
5. Merge and de-duplication, the `sbretire portfolio import` command, `ledger.csv`, and docs.

## 7. Validation

- **T1:** each parser on its synthetic fixture: every row mapped to a hand-checked expected type, quantity, price,
  cash and flow; unknown types raise with file and row; encoding, BOM, pence and `$` handling.
- **T2:** two synthetic month folders with overlapping year-to-date exports merge without duplicates; Vanguard and
  ii cash reconcile to their running balances.
- **T3:** the real October 2026 exports import without error on the user's machine (a manual `check:`; never in
  tests).

## 8. Decision Log

- 2026-10-18 — §2 #1–#5 from the user's answers (merge and de-duplicate; stop on unknown types;
  `config/accounts.yaml`; external vs internal flows). #6–#13 by me from the export layouts.
- 2026-10-18 — F-024.4: `reconcile_cash(rows)` takes the rows alone; each `LedgerRow` carries its export's
  `stated_balance`, so the separate `StatedBalance` sequence in §5 is dropped. Checks run per account and source
  file, to half a penny, and report the first break only.

## 9. Surprises

- 2026-10-18 — The real exports (digits masked) differ from the brief's first reading:
  - **HL:** the `Reference` column says what a row is: `B…` buy, `S…` sell, `INTEREST`, `Transfer` (from the SIPP
    income account) and `MANAGE FEE`. "HL SIPP To A/C …" is the **management fee**, not an internal transfer; the
    type map above was corrected before the code.
  - **Vanguard:** the transactions come as one file per account. Only the holdings export is shared, so `filter`
    is optional.
  - **Encodings:** Vanguard transactions are Windows-1252 (`®`) while Vanguard holdings are UTF-8, so files are
    decoded as UTF-8 first and fall back to Windows-1252.
  - **Row order:** Schwab and ii list rows newest first; Vanguard oldest first. Running balances are checked in
    date order, with the opening balance inferred from the first stated balance (Vanguard's history starts
    mid-way).
- 2026-10-18 — F-024.3: the HL export also has `ID TFC` (tax-free cash paid to the bank: external out), `BACS`
  (pension transfer in: external in) and `TRANSFER` ("Product Transfer HL SIPP Income Drawdown": a move into the
  SIPP's drawdown part, treated as internal). F-025's holdings check should confirm the drawdown money is in the
  HL holdings export; if not, it is really an outflow from the tracked account.
- 2026-10-18 — F-024.4: a Vanguard `Investment` record's amount mirrors its `Cash` record and is not cash, so
  only the units are kept from it. Fee units are sold as `Sell (Fee)` (typed `sell`) a few days before the
  `Account Fee` cash debit.

## 10. Tasks

### F-024.1 Accounts config and month folders
- **Status**: Verification
- **Depends on**: —

`ledger/accounts.py` (strict pydantic, located errors like `config.py`), `config/accounts.example.yaml`,
`merge.month_folders`. The `config/accounts.yaml` path is already git-ignored.

**Acceptance criteria**
- [x] `load_accounts` accepts the example and rejects a duplicate id, an unknown provider or wrapper, a missing pattern list and an unknown key, each with the YAML location — `test_load_accounts_validates`
- [x] `month_folders` maps `oct-26` → 2026-10-01 and `jan-27` → 2027-01-01, sorts by date and ignores other names — `test_month_folders_parse_and_sort`
- [x] The example file holds no real names, numbers or amounts — `test_accounts_example_is_synthetic`

**Notes**
- 2026-10-18 `ledger/accounts.py`: `AccountConfig` (strict pydantic: provider and wrapper literals, 3-letter currency, non-empty pattern lists, optional `filter`), `load_accounts` (duplicate-key YAML loader, located issues via the scenario helpers, duplicate ids). `ledger/merge.month_folders`. `config/accounts.example.yaml` (five placeholder accounts). Tests `tests/unit/test_ledger_accounts.py` (3).

### F-024.2 Ledger model and Schwab parser
- **Status**: Verification
- **Depends on**: F-024.1

`ledger/model.py` (`LedgerRow`, `LEDGER_COLUMNS`, fingerprint) and `parsers/schwab.py` (§5 map; US dates; `$`, signs,
thousands separators; empty quantity and price).

**Acceptance criteria**
- [x] A synthetic Schwab export covering every action in §5 parses to hand-checked rows (type, flow, quantity, price, cash, fees, currency USD) — `test_schwab_parser_maps_every_action`
- [x] An unknown action raises `UnknownTransaction` naming the file, row number and action — `test_schwab_parser_rejects_unknown_action`

**Notes**
- 2026-10-18 `ledger/model.py`: `LedgerRow` (brief §2 #6 plus `sequence`, the chronological position in the source file, and `stated_balance`, the export's running cash balance where given), `fingerprint`, `LEDGER_COLUMNS`, `UnknownTransaction`. `parsers/_common.py`: UTF-8 with any leading BOMs else Windows-1252, money parsing (`$`, `£`, commas, signs, parentheses, n/a, --), dates. `parsers/schwab.py` with the §5 map. Fixture `tests/fixtures/accounts/schwab.csv` (invented rows, every action). Tests `tests/unit/test_ledger_schwab.py` (2).

### F-024.3 HL parser
- **Status**: Verification
- **Depends on**: F-024.2

`parsers/hl.py`: Windows-1252, preamble skipped up to the header row, quoted commas, trades from "<name> <qty> @
<price>" with pence converted to pounds, interest, internal transfers.

**Acceptance criteria**
- [x] A synthetic HL export (preamble, `£` in the header, quoted descriptions with commas) parses to hand-checked rows; trade prices in pounds; quantity sign follows the value sign — `test_hl_parser_reads_trades_interest_and_transfers`
- [x] An unrecognised description raises `UnknownTransaction` with file and row — `test_hl_parser_rejects_unknown_description`

**Notes**
- 2026-10-18 `parsers/hl.py`: preamble skipped to the `Trade date` header; `Reference` drives the type (B/S trades, INTEREST, Transfer/TRANSFER internal, MANAGE FEE, ID TFC external out, BACS external in); trade names from "<name> <qty> @ <price>"; pence to pounds; units from `Quantity`, negated for sells. Fixture `tests/fixtures/accounts/hl.csv` (Windows-1252, quoted commas, invented rows). Tests `tests/unit/test_ledger_hl.py` (2); the test's expected line numbers were off by one (header on line 6) and were corrected before green.

### F-024.4 Vanguard and ii parsers with cash reconciliation
- **Status**: Verification
- **Depends on**: F-024.2

`parsers/vanguard.py` (shared file filtered per account; two-leg records), `parsers/ii.py` (repeated BOMs, UK
dates, quoted `£` amounts, `n/a`, debit/credit columns), `reconcile.py`.

**Acceptance criteria**
- [x] A synthetic Vanguard export with ISA and pension rows yields each account's rows only, with investment legs carrying units and cash legs carrying cash — `test_vanguard_parser_filters_and_splits_legs`
- [x] A synthetic ii export (several BOMs, `n/a`, quoted `£1,234.56`) parses to hand-checked rows — `test_ii_parser_reads_debits_credits_and_transfer_in`
- [x] Cumulative ledger cash equals the stated running balance at every row for both fixtures, and a deliberately broken fixture reports the first break — `test_reconcile_cash_matches_running_balance`

**Notes**
2026-10-18 parsers/vanguard.py (Account filter, Investment legs carry units, Cash legs cash + stated balance), parsers/ii.py (Description-driven types, Credit - Debit, n/a empty), reconcile.py; tests/unit/test_ledger_vanguard_ii.py (5). Real October Vanguard ISA/pension and ii exports reconcile with no breaks.

### F-024.5 Merge, import command and docs
- **Status**: In Progress
- **Depends on**: F-024.3, F-024.4

`merge.build_ledger` (all folders, de-duplication, newest folder wins), `sbretire portfolio import`, `ledger.csv`,
README section, THESAURUS terms, decision record `docs/decisions/portfolio-data.md` (§1–§4 from §2 #1–#5).

**Acceptance criteria**
- [ ] Two synthetic month folders with overlapping year-to-date exports merge to the union with no duplicate fingerprints; a repeated row within one file is kept — `test_build_ledger_merges_months_without_duplicates`
- [ ] `sbretire portfolio import` on the synthetic folders writes `ledger.csv` (UTF-8, LF, `LEDGER_COLUMNS`) and prints per-account rows, date range, counts by type, external in and out, and reconciliation; an unknown type exits 2 with the error — `test_cli_portfolio_import`
- [ ] README documents the folder layout, `accounts.yaml` and the command; THESAURUS defines Account, Wrapper, Ledger, External Flow and Internal Transfer; decisions recorded — `check: grep -n "portfolio import" README.md docs/decisions/portfolio-data.md`
- [ ] The real October 2026 exports import without error and Vanguard and ii reconcile (run by the user or locally; never committed) — `check: uv run sbretire portfolio import`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Accounts config validation — `test_load_accounts_validates`
2. Month folders — `test_month_folders_parse_and_sort`
3. Example is synthetic — `test_accounts_example_is_synthetic`
4. Schwab mapping — `test_schwab_parser_maps_every_action`
5. Schwab unknown — `test_schwab_parser_rejects_unknown_action`
6. HL mapping — `test_hl_parser_reads_trades_interest_and_transfers`
7. HL unknown — `test_hl_parser_rejects_unknown_description`
8. Vanguard legs — `test_vanguard_parser_filters_and_splits_legs`
9. ii parsing — `test_ii_parser_reads_debits_credits_and_transfer_in`
10. Cash reconciliation — `test_reconcile_cash_matches_running_balance`
11. Merge — `test_build_ledger_merges_months_without_duplicates`
12. CLI — `test_cli_portfolio_import`
13. Docs — `check: grep -n "portfolio import" README.md docs/decisions/portfolio-data.md`
14. Real exports — `check: uv run sbretire portfolio import`
