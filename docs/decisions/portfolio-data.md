# Portfolio Data Decisions

Scope: the household's account exports: which files belong to which account, how monthly exports are merged, the
normalised ledger, and the checks made before anything analyses it (epic `portfolio-analysis`).

## 1. Accounts are listed in a git-ignored `config/accounts.yaml`; nothing about an account is in code

Each account has an `id`, `name`, `provider` (the parser: `schwab`, `hl`, `vanguard` or `ii`), `owner` (a person
id from the model config), `wrapper` (`taxable`, `isa`, `pension` or `sipp`), `currency` (three capital letters)
and file-name patterns (`*` and `?`) for its `transactions` and `holdings` exports, matched inside each month
folder. A file shared by several accounts is split with `filter`, which keeps the rows whose provider `Account`
column equals it (Vanguard). Ids must be unique. Problems are reported like scenario errors: every one, each with
its YAML location. `config/accounts.example.yaml` (committed) shows the layout with made-up values. (F-024)

**Why**: account names, owners and file names are personal facts, so they stay out of code and git; patterns
survive the dates and suffixes providers put in file names.

## 2. Exports live in monthly folders `data/transactions/<mon>-<yy>/` and every folder is read

`oct-26` means October 2026. `sbretire portfolio import` reads every such folder under `--root` (default
`data/transactions`, git-ignored) and ignores anything else there. (F-024)

**Why**: it matches the household's routine of downloading each provider's year-to-date export once a month, and
keeps old downloads as they were.

## 3. Overlapping months are merged on a fingerprint; the newest folder wins and true repeats are kept

A row's fingerprint is (account, trade date, type, security key, quantity to 6 places, cash to 2 places,
reference). Folders are taken newest first; an older folder adds a row only where it holds more copies of that
fingerprint than the newer folders already gave, so two identical rows in one file (for example two equal
dividends on one day) both survive, and a row repeated by next month's export is not counted twice. Each row's
`source_file` is `<folder>/<file>`. (F-024)

**Why**: year-to-date exports repeat earlier months; keeping the newest copy means a provider's later correction
of a row's wording does not create a second row, and multiplicity rather than a plain set keeps genuine repeats.

## 4. One ledger row shape for every provider, signed from the account's side, with a `flow` on every row

Columns (`ledger.csv`, in this order): `account`, `owner`, `wrapper`, `date` (trade date), `settle_date` (or
empty), `type`, `flow`, `security_key` (the provider's symbol, SEDOL or fund name; empty for cash-only rows),
`security_name`, `quantity_change` (units, + received), `price` (per unit, in pounds or dollars, never pence),
`cash_change` (+ into the account's cash), `fees`, `currency`, `reference`, `source_file`, `source_row`,
`sequence` (1 = the file's oldest row) and `stated_balance` (the export's running cash balance, where stated).
Amounts stay in the account's own currency; no conversion happens here. Types are `buy`, `sell`, `dividend`,
`interest`, `fee`, `tax_withheld`, `contribution`, `tax_relief`, `transfer_in`, `transfer_out`,
`internal_transfer` and `corporate_action`. `flow` is `external` (money entering or leaving the household:
bank transfers, contributions, tax relief, transfers from or to another provider), `internal` (a move inside one
account, such as HL's SIPP income account to its capital account) or `none` (trades, income, fees, tax, corporate
actions). Where an export writes one event as two records (Vanguard's Investment and Cash records), both are
kept: the investment row carries the units with `cash_change` 0, the cash row carries the cash. The per-provider
mappings are tables in each parser (`src/sbretire/ledger/parsers/`). (F-024)

**Why**: performance analysis must leave external flows out of returns and net internal ones away, and security
and cash legs kept apart can be reconciled to both holdings and cash balances without double counting.

## 5. An unknown transaction stops the import; nothing is guessed

A row whose action, reference or description is not in its parser's map stops the import with exit code 2 and
the message `<folder>/<file> row <n>: unknown transaction '<what was found>'; add it to the parser's map`. (F-024)

**Why**: a silently misclassified row (a transfer read as income, say) would corrupt every return figure built on
it; a new type is rare and cheap to add.

## 6. Cash is reconciled to every stated running balance, file by file

Where an export states a running cash balance (Vanguard `Cash Balance (GBP)`, ii `Running Balance`), each file's
rows are taken in date order, the opening cash is inferred from the first stated balance, and the cumulative
`cash_change` must equal every later stated balance to half a penny. The first break per file is reported
(`<account> (<folder>/<file> row <n>): ledger cash X but the export states Y`); the ledger is still written for
inspection, and the command exits 1. Schwab and HL state no running balance; their summary says so. (F-024)

**Why**: it proves the parser against the provider's own arithmetic before anything uses the ledger. Each file is
checked alone because merging removes rows that a later export repeats.

## 7. Holdings come from the newest month folder's holdings exports, each checked against its own totals

`sbretire portfolio value` reads only the newest `<mon>-<yy>` folder. Each account's `holdings` patterns must match
a file there (otherwise exit 2 naming the account and folder); where several match, the last by name is used
(provider names carry the date). A file read by two accounts needs `holdings_filter` on each (Vanguard's
`Product Wrapper`: `Stocks & Shares ISA`, `Personal Pension`). Values are the provider's own, in the account's
currency: Schwab `Mkt Val`; HL `Value (£)` (its US stocks already converted) with `Price (pence)` / 100; Vanguard
`Current Value (GBP)`; ii `Market Value (£)` with price = value / quantity (its `Price` and `Market Value` are in
the listing currency). Cash is a holding of kind `cash`: Schwab "Cash & Cash Investments", HL "Total cash",
Vanguard "GBP Cash"; an export with no cash line (ii) takes the newest running balance in the account's
transactions export in the same folder. Self-checks, to a penny: Schwab securities + cash = "Positions Total";
HL securities = "Stock value" = the table's Totals row, and securities + cash = "Total value". A mismatch stops
with exit 2. (F-025)

**Why**: holdings are snapshots, so older folders are history; using the providers' own valuations and checking
them against the providers' own totals proves the parser, as §6 does for cash.

## 8. Each account keeps its own valuation date; a missing one is assumed and shown

An account is valued at the date its export states (Schwab's title, HL's "Spreadsheet created at", Vanguard's
`Valuation Date`). An export that states none (ii) takes the newest date stated by the other exports in the
folder and is shown "(assumed)". The summary warns when the dates span more than 7 days. No common date is
imposed. (F-025)

**Why**: the household downloads exports on different days; showing each date (user's choice, 2026-10-18) is
more honest than pretending they share one.

## 9. USD is converted at a rate given on the command line

`--usd-gbp R` (GBP per US dollar) converts every USD account and is required while any account is in USD (exit 2
otherwise); other non-GBP currencies are refused. The rate is printed and written to `holdings.csv` (`fx_rate`).
Where an export states its own rate (HL's footer "x USD to 100 pence … at <date>"), the summary prints it and warns
if `--usd-gbp` differs from it by more than 2%. (F-025)

**Why**: no export carries Schwab's rate and runs stay offline (SPEC §2); the user chose a flag over a config
setting (2026-10-18). F-026's FX price file may later supply a default.

## 10. The starting balance is printed to paste, never written into the model config

The summary gives GBP totals by account (securities, cash), by owner and for the household, then the YAML to paste:
`portfolio:` / `starting_balance: <household total rounded to the pound>` with a comment naming the folder and
the date range. `output/portfolio/holdings.csv` (UTF-8, LF) has one row per holding: the `Holding` fields
(`account`, `owner`, `wrapper`, `valuation_date`, `date_stated`, `kind`, `security_key`, `security_name`,
`quantity`, `price`, `value`, `currency`, `source_file`, `source_row`), then `fx_rate` and `value_gbp`. Exit 0
valued, 1 unreadable, 2 invalid. (F-025)

**Why**: `config/model.yaml` is the user's file (epic scope: no automatic edits); a pasted line keeps every change
to the scenario deliberate and visible.
