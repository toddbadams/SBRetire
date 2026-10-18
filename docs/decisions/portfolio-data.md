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

## 11. Prices come from files the household downloads; one map ties them to holdings

Price files live in `data/prices/` (git-ignored) and are only read. A Yahoo Finance "Historical data" download is
used as it is (`Date,Open,High,Low,Close,Adj Close,Volume`, daily or monthly); any other file needs `Date,Close`
with an optional `Dividend` column. Rows without a usable price (`null`, empty) are skipped.
`data/prices/securities.yaml` (example `config/securities.example.yaml`) gives `fx: {USD: <file of GBP per USD>}`
and one entry per series: `id`, `name`, `file`, `quote` (`GBP`, `GBX`, `USD`) and `holdings`
(`<account>:<security key>`, one or more). Unknown keys, duplicate ids and a holding priced by two series are
errors with their YAML location (exit 2). A missing map is treated as empty, so every holding is reported
missing. (F-026)

**Why**: runs stay offline (SPEC §2); Yahoo covers the US stocks and London ETFs for free, and the user chose its
layout (2026-10-18); one series per security avoids pricing the same ETF twice when two accounts hold it.

## 12. A month's return is the total return in GBP from month-end prices

The last row in each calendar month is its value. A series' return for month t is
`(P_t + D_t) × X_t / (P_{t-1} × X_{t-1}) − 1`: `P` the price in pounds (GBX ÷ 100) or dollars, `D` the dividends
paid in month t, `X` GBP per unit of the quote currency at month-end (1 for GBP and GBX; the FX file for USD).
The basis is `adjusted` when the file has `Adj Close` (dividends already reinvested; `D` = 0), `dividends` when
it has a `Dividend` column, else `price`, which is reported because it may understate income units. A month
without a price (or, for USD, a rate) has no value, and the returns into and out of it are unknown. (F-026)

**Why**: income units must include their distributions (epic risk) and USD holdings' GBP returns include the
currency move; one formula covers daily and monthly files from every source.

## 13. The window is the last 60 complete months before the newest export folder

`--months N` (default 60) monthly returns end with the month before the newest `<mon>-<yy>` folder's month:
`oct-26` gives October 2021 to September 2026, using the September 2021 price for the first. (F-026)

**Why**: "five years monthly" (epic); ending before the export month avoids a half-finished month.

## 14. Coverage is reported, never enforced, with each gap's share of the invested value

Each series is **full** (a return every month), **short** (history starts later; first month shown), **gaps**
(months missing inside its history) or **missing** (no price file, no prices in the window, or USD with no FX
file); each holding in no series is **missing** too. Each line shows its share of the newest holdings' invested
(non-cash) GBP value, with USD at `--usd-gbp` or the FX file's latest month-end. Missing prices never stop
`sbretire portfolio returns` (exit 0). `output/portfolio/returns.csv` (UTF-8, LF: `month`, `series`, `value_gbp`, `dividend_gbp`,
`return_gbp`, `basis`) and `returns_metadata.json` (window, USD rate used, and each file's SHA-256, first and last
date, rows and basis) are written. (F-026)

**Why**: the household adds price files a few at a time (user, 2026-10-18); showing what share of the money each
gap affects says which files matter most, and the hashes make later analyses reproducible (SPEC §10.3).

## 15. Performance figures are defined once

Over n monthly returns `r_t`: the **annual return** is `Π(1 + r_t)^(12/n) − 1`; the **annual volatility** is the
sample standard deviation (n − 1) × √12; the **Sharpe ratio** is `12 × mean(r_t − r_f) / (√12 × sd)`, with
`r_f = (1 + R)^(1/12) − 1` from the annual risk-free rate `R`, and is undefined (`n/a`) when the standard deviation
is zero. The **maximum drawdown** is the largest fall of the wealth index (1 before the first month, × (1 + r_t)
each month) below its previous peak, reported with the peak, trough and first recovery month (none if not
regained). **Rolling 12 months**: the compounded return and annualised volatility of each 12-month run, from the
12th month. A series with fewer than 12 returns shows no volatility or Sharpe. (F-027)

**Why**: standard definitions, stated so every page and later feature (F-029, F-030) uses the same figures.

## 16. The back-test applies today's weights to past returns, re-weighting over gaps

Weights are today's GBP values from the newest folder's valuation: each series' holdings and all cash. Holdings in
no series (or whose series has no file) are left out. Each month counts only the series with a return that month;
they and the cash are rescaled to 100%, and cash earns the monthly risk-free rate. Each month's **covered share**
(counted value ÷ today's household value) is reported. With nothing priced the back-test is all cash.
`sbretire portfolio performance` prints the figures with the note that they are historical, not a forecast or
advice, and writes `performance.csv` and `performance_series.csv` (columns in the README). (F-027)

**Why**: the user chose re-weighting over a shorter common window or dropping short histories (2026-10-18);
showing the covered share keeps the gaps visible.

## 17. The risk-free rate is one annual figure in the securities map

`risk_free_rate` (a fraction, 0 ≤ R < 0.2) at the top of `data/prices/securities.yaml`; `--risk-free R` overrides
it for one run; with neither, the command exits 2 naming `risk_free_rate`. (F-027)

**Why**: a single UK Bank Rate figure (epic), kept next to the price files it is used with (user, 2026-10-18).
Account-level time- and money-weighted returns since the first export are deferred to F-031 (user, 2026-10-18).

## 18. Look-through data: a YAML factsheet per fund, sector and region on each stock, fixed names

A fund's series names `factsheet: <file>.yaml` in `data/factsheets/` (git-ignored; example
`config/factsheet.example.yaml`): `as_of`, `source`, and weight maps `asset_classes`, `sectors`, `regions`,
optional `currencies` and optional `top_holdings`, each a share of the **whole** fund. A map is fractions summing
to 0.98–1.02 or percentages summing to 98–102 and is rescaled to 1; outside that range it is an error with its
location; a missing map leaves that part of the fund Unclassified. A single stock's series sets `sector`,
`region` and optionally `asset_class` (default equity) and `currency` (default from the region). Names are fixed:
the 11 GICS sectors and Other; UK, North America, Europe ex UK, Japan, Asia Pacific ex Japan, Emerging Markets,
Other; equity, bond, cash, property, other; GBP, USD, EUR, JPY, Other. Matching ignores case and punctuation, an
alias list accepts common factsheet wording (`src/sbretire/ledger/taxonomy.py`), and any other name is an error
with its location (exit 2). (F-028)

**Why**: the user chose a file per fund plus stock fields, and fixed lists so that typos or different managers'
wording never split a sector (2026-10-18); Vanguard's own Asset Sector column is unreliable (epic).

## 19. Look-through arithmetic, cash, currencies and Unclassified

Each holding's GBP value (F-025 valuation; USD at `--usd-gbp` or the FX file's latest month-end) is spread over
its fund's weights, or put whole on a stock's labels. Cash is asset class `cash`, sector and region `Cash`, and
the account's currency. Currencies come from a factsheet's `currencies`, else from its regions (UK → GBP, North
America → USD, Europe ex UK → EUR, Japan → JPY, else Other), and the share derived this way is reported. Holdings
in no series, series with neither a factsheet nor stock fields, missing factsheets and dimensions a factsheet
leaves out are **Unclassified**, so every table adds to the household total. A factsheet more than 12 months
older than the newest valuation date gets a warning. (F-028)

**Why**: currency exposure is not the quote currency (a GBX-quoted ETF of US stocks is USD exposure); keeping
Unclassified visible shows how much is not yet looked through.

## 20. Top look-through holdings and the output

Each stock counts as one holding under its series name; each fund's `top_holdings` add `value × weight` under the
holding's name, matched ignoring case and punctuation. The 15 largest are shown, noting that funds publish only
their largest holdings. `sbretire portfolio exposure` prints one table per dimension (GBP and share) and the top
holdings, and writes `output/portfolio/exposure.csv` (UTF-8, LF: `dimension`, `label`, `value_gbp`, `share`, the
top holdings last as `top_holding`). Exit 0 ok, 1 unreadable, 2 an invalid map or factsheet. (F-028)

**Why**: concentration hidden inside funds (the same large company in several ETFs) is one of the epic's
questions; one CSV feeds the Portfolio page (F-030).

## 21. The frontier re-weights only the priced sleeve, from shrunk estimates

The **priced sleeve** is the series with today's value > 0 and a return in every month of the window; everything
else (cash, short-history and unpriced holdings) stays at today's GBP values, and its share is shown. Expected
return = 12 × the mean monthly return; covariance = 12 × the Ledoit–Wolf (2004) estimate: the sample covariance
(÷ T) shrunk towards its mean variance × I, with the intensity `min(b̄², d²) / d²` from the data.
`--covariance sample` uses the n − 1 sample covariance instead. (F-029)

**Why**: a covariance needs a common window; about 36 series and 60 months make the raw estimate noisy, and
shrinkage gives steadier weights (user, 2026-10-18).

## 22. Mixes: long-only, capped, minimum variance to maximum return; the target keeps today's risk

Weights are ≥ 0, sum to 1 over the sleeve and are each ≤ `max_weight` (`securities.yaml`, default 0.25;
`--max-weight`); `max_weight × n < 1` or fewer than 2 sleeve series is an error (exit 2). Sharpe uses
`12 × monthly risk-free` (as F-027). Shown: today's mix; minimum variance; 21 frontier points from the
minimum-variance return to the highest return the cap allows; maximum Sharpe (never below a frontier point); and
the **target**: by default the highest return with volatility ≤ today's sleeve volatility (minimum variance if
today's is lower), or `--target max-sharpe` / `min-variance`. Solved with SciPy SLSQP from deterministic starts.
`sbretire portfolio frontier` prints the mixes with return, volatility and Sharpe, and warns when today's weight
of a series is above the cap. (F-029)

**Why**: a cap stops the optimiser piling into one past winner; keeping today's risk shows what the same
holdings might have done for the risk the household already lives with (user, 2026-10-18).

## 23. Trades: household view for analysis, within-account trades to act on

**Household trades** treat the sleeve as one portfolio: target weight × sleeve value − today's value per
series. They are labelled analysis only, because they need moves between accounts and wrappers. **Within-account
trades** re-split each account's sleeve value over the series it already holds, in proportion to those series'
target weights (an account whose series all have target 0 is left as it is). Trades under `--min-trade` (default
50 GBP) are skipped. The resulting household mix ("within accounts") is reported beside the target. (F-029)

**Why**: the household is analysed as one portfolio (epic), but money cannot move freely from a pension to an
ISA, so only within-account trades can actually be made.

## 24. Costs, sensitivity and outputs

`trading: {fee_per_trade, cost_rate}` on an account in `accounts.yaml` (fee ≥ 0 in the account's currency,
converted to GBP; `0 ≤ cost_rate < 0.05` for spread, stamp duty and FX). A trade costs `fee + rate × |amount|`;
an account without `trading` costs 0, with a warning. **Sensitivity:** the target is re-estimated on each half of
the window and the turnover `Σ|w₁ − w₂| / 2` between the two is reported. Outputs (UTF-8, LF):
- `frontier.csv`: `point`, `return`, `volatility`, `sharpe`; 21 points, then `today`, `min_variance`,
  `max_sharpe`, `target` and `within_accounts`;
- `frontier_weights.csv`: series × those five mixes;
- `trades.csv`: `scope`, `account`, `series`, `current_gbp`, `target_gbp`, `trade_gbp`, `cost_gbp` (pennies).
(F-029)

**Why**: per-account fee schedules (user, 2026-10-18); estimation error is the frontier's main weakness (epic
risk), and a turnover figure says plainly how much to trust the target.

