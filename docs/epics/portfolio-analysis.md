---
epic: portfolio-analysis
title: Portfolio Analysis
status: active
spec_sections: [§4.2]
depends_on: [results-viewer]
milestones:
  - { id: F-024, title: Account Import and Normalised Ledger, status: done }
  - { id: F-025, title: Holdings Valuation and Starting Balance, status: done }
  - { id: F-026, title: Price History and Monthly Returns, status: done }
  - { id: F-027, title: Performance and Drawdown Report, status: done }
  - { id: F-028, title: Sector and Region Look-Through, status: in-progress }
  - { id: F-029, title: Sharpe Efficient Frontier and Re-Weighting Analysis, status: proposed }
  - { id: F-030, title: Portfolio Page in the Viewer, status: proposed }
  - { id: F-031, title: Account Returns from the Ledger, status: proposed }
created: 2026-10-18
updated:
  - 2026-10-18: created from the user's request to import account transaction histories and analyse the portfolio
---

# Portfolio Analysis

## Goal

Import the household's monthly account exports (five accounts across four providers) into one normalised ledger, then
answer five questions about the savings the retirement model draws on:

1. **What are they worth today?** One total for `portfolio.starting_balance`, split by account and person.
2. **How have they performed?** Returns, volatility and drawdowns.
3. **What are they invested in?** Sectors, regions, asset classes and currencies, looking through funds.
4. **How efficient is the mix?** Where it sits against a Sharpe-ratio efficient frontier built from the current
   holdings.
5. **What would a more efficient mix look like?** The re-weighting, its trades and costs.

Results appear on a Portfolio page beside the results viewer (same common theme, offline, Save as PDF), designed with
Claude Design (`docs/design/portfolio-design-handoff.md`).

**Analysis, not advice.** The re-weighting output is a model calculation under stated assumptions: historical
returns, a fixed risk-free rate and long-only weights capped per holding. It is not a personal recommendation; the
page says so, and every suggested change shows what it trades off.

## Scope

**In** (user decisions, 2026-10-18):

- **Accounts.** Each month's exports live in `data/transactions/<mon-yy>/` (e.g. `oct-26/`), one file per account.
  The five accounts:

  | Provider | Wrapper | Owner | File |
  |---|---|---|---|
  | Charles Schwab | taxable brokerage (USD) | person 1 | `schwab.csv` |
  | Hargreaves Lansdown | SIPP | person 1 | `hl.csv` |
  | Vanguard UK | ISA | person 2 | `vanguard_isa.csv` |
  | Vanguard UK | personal pension | person 2 | `vanguard_pension.csv` |
  | interactive investor | SIPP | person 2 | `ii.csv` |

  A git-ignored `config/accounts.yaml` maps each file to its account, owner, wrapper, currency, parser and fee
  schedule. Holdings exports (added 2026-10-18) are `schwab-Individual-Positions-<date>-<time>.csv`,
  `hl-account-summary.csv`, `vanguard-holdings.csv.csv` (one file for both Vanguard wrappers) and
  `ii_holdings.csv`; file names vary by provider, so the account file matches them by pattern.
- **Holdings come from a holdings/valuation export per account each month**, saved next to the transactions. The
  transaction exports cover only 2026 and contain no opening positions. Transactions supply cash flows, dividends,
  interest, fees and trades for performance.
- **Prices are supplied by the user:** monthly price history per holding plus USD/GBP, as CSV files in
  `data/prices/`. The app only reads them, and analysis runs offline. Provenance (file, date range, SHA-256) is
  recorded in the analysis metadata.
- **Total for `starting_balance`:** all five accounts, cash included, USD converted at the valuation-date rate, with
  the split by account and person. A CLI prints the figure and a ready-to-paste YAML line; it never edits the
  personal config itself.
- **Risk and Sharpe basis:**
  - monthly total returns over the last 5 years (shorter where a holding is newer, and flagged), annualised;
  - in GBP;
  - the risk-free rate is a single UK Bank Rate figure set in config.
- **Sectors:** look-through for funds and ETFs, using published sector and region weights from a factsheet file per
  fund in `data/factsheets/`. Single stocks use their own sector.
- **Efficient frontier on current holdings only:** long-only, with a user-set maximum weight per holding. The
  analysis shows the frontier, the current mix, the minimum-variance and maximum-Sharpe mixes, and the trades to move
  from current to a chosen mix, with estimated trading costs from each account's fee schedule.
- **Re-weighting treats the household as one portfolio** (the user did not choose "keep accounts separate").
  Because money cannot move freely between wrappers (e.g. pension to ISA), the page marks cross-account moves as
  analysis only and also shows the within-account trades.
- **Output:** `sbretire portfolio` writes `portfolio.json` (a versioned schema like `results.json`) plus CSVs, and
  the viewer gains a Portfolio page.

**Out:**

- Tax (no capital gains or dividend tax calculations, consistent with SPEC §16), live price downloads, broker
  connections, automatic edits to `config/model.yaml`.
- Forecasts of future returns; the frontier is historical.
- Personal investment advice.

## Decomposition — features and order

| F-NNN | Feature | Delivers | depends_on |
|---|---|---|---|
| F-024 | Account Import and Normalised Ledger | Parsers for the five export formats into one ledger (account, owner, wrapper, date, type, security, quantity, price, amount, currency) | — |
| F-025 | Holdings Valuation and Starting Balance | Holdings from the holdings exports; household total, split by account and person; `sbretire portfolio value` prints the `starting_balance` line | F-024 |
| F-026 | Price History and Monthly Returns | Reads user price files and USD/GBP; monthly total returns in GBP per holding (income units add distributions); coverage report | F-024 |
| F-027 | Performance and Drawdown Report | Time- and money-weighted returns for the export period; 5-year back-test of current weights: return, volatility, Sharpe, drawdowns, rolling metrics | F-025, F-026 |
| F-028 | Sector and Region Look-Through | Factsheet weights per fund, sectors of single stocks; household exposure by sector, region, asset class, currency; top look-through exposures | F-025 |
| F-029 | Sharpe Efficient Frontier and Re-Weighting Analysis | Frontier on current holdings (long-only, capped); min-variance and max-Sharpe mixes; trades and estimated costs; estimation caveats | F-026, F-027 |
| F-030 | Portfolio Page in the Viewer | `portfolio.json` + schema; Portfolio page from the Claude Design hand-off; Save as PDF | F-025, F-027, F-028, F-029 |
| F-031 | Account Returns from the Ledger | Month-end account values rebuilt from today's holdings back through the ledger and prices (with a transaction-to-holding name map for HL and Vanguard); time-weighted (chained Modified Dietz) and money-weighted (XIRR) returns per account and household since the first export. Split from F-027 (user, 2026-10-18) | F-024, F-025, F-026 |

## Format notes from the October 2026 exports

These are structure only; no amounts are recorded here.

- **Schwab:** quoted CSV with US dates (MM/DD/YYYY), USD with a `$` sign and `-` for outflows. Actions include Buy,
  Sell, Qualified Dividend, Credit Interest, Foreign Tax Paid, ADR Mgmt Fee, Cash Merger, Cash Merger Adj and
  MoneyLink Transfer.
- **HL:**
  - Windows-1252 encoding (the `£` sign).
  - A summary preamble (title, client details, "Valuation as at" timestamp, blank line) before the
    `Trade date,Settle date,Reference,Description,Unit cost (p),Quantity,Value (£)` table.
  - Prices in pence.
  - Some descriptions contain commas.
- **Vanguard UK** (ISA and pension, same layout): ISO dates, GBP, with Record Type (Cash/Investment) and Transaction
  Type (Buy, Sell (Fee), Account Fee, Interest, Deposit, Contribution, Tax Relief) and a running cash balance.
- **interactive investor:**
  - UTF-8 with repeated byte-order marks, UK dates (DD/MM/YYYY).
  - `£` amounts with thousands separators in quoted fields, `n/a` for empty debit/credit, and a SEDOL column.

## Holdings export formats (October 2026)

These are structure only; no amounts are recorded here.

- **Schwab positions:**
  - Title line "Positions for account … as of <time> ET, <yyyy/mm/dd>", blank line, then a quoted table:
    Symbol, Description, quantity, Price, Mkt Val, Cost Basis, gain columns and Asset Type.
  - A "Cash & Cash Investments" row and a "Positions Total" row.
  - USD with `$`, thousands separators and `--` for empty.
- **HL account summary:**
  - The SIPP: "HL SIPP" title, client name and number, "Spreadsheet created at <dd-mm-yyyy hh:mm>".
  - Stock value, Total cash, Amount available to invest and Total value lines, then a table: Code, Stock,
    Units held, Price (pence), Value (£), Cost (£), gain columns.
  - Holds US single stocks valued in GBP.
  - Windows-1252 encoding.
- **Vanguard holdings:**
  - One file for both wrappers: Valuation Date, Account Number, Product Wrapper (Personal Pension / Stocks & Shares
    ISA), Investment Name, Asset Sector, Quantity, Original Cost, Current Price, Current Value, Gain/Loss and % of
    Total Portfolio.
  - A "GBP Cash" row per wrapper.
  - The Asset Sector labels are coarse and sometimes misleading (a 60–100% equity fund labelled "Fixed Interest"
    or "Unclassified"), so look-through uses factsheets, not this column.
  - UTF-8 with a `®` in names; the file has a doubled `.csv.csv` extension.
- **ii holdings:**
  - Symbol, Name, Qty, Price, day change, Market Value (£), Market Value, Book Cost, gains, Average Price.
  - Holdings only, with **no cash row and no valuation date** in the file. The cash comes from the transactions'
    running balance, and the date from the folder or a setting.
  - Holds one ETF bought before the transaction export period.

## Risks and open questions

- **USD/GBP rate:** Schwab values are in USD and no export carries an exchange rate. The valuation needs a
  USD/GBP rate for the valuation date, from the user's FX price file (F-026) or a setting.
- **Valuation dates differ by account** (exports taken on different days). The total states each account's date;
  F-025 decides whether to require one common month-end.

- **Personal data:** `data/transactions/`, `data/prices/`, `data/factsheets/`, `config/accounts.yaml` and
  `output/` are git-ignored (committed 2026-10-18). The design hand-off uses synthetic data only.
- **Holdings export formats** are not yet seen; each provider's layout is confirmed in F-025's brief.
- **Estimation error:** five years of monthly data (60 points) make mean-return estimates noisy, so
  maximum-Sharpe weights can swing.
  - **Mitigations:** the weight cap, a covariance shrinkage option, and showing frontier sensitivity.
  - **To settle in F-029's brief.**
- **USD holdings:** returns and volatility in GBP include currency moves; the page shows currency exposure.
- **Income vs accumulation units:** returns must add distributions where prices exclude them. To settle in F-026's
  brief.
- **Cross-wrapper moves are not executable as shown;** the page must make that explicit.
