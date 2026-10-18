---
id: F-026
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 5
created: 2026-10-18
updated: 2026-10-18
---
# F-026 Price History and Monthly Returns

## 1. Purpose

Turn the price files the household supplies into **monthly total returns in GBP** for every holding, over the last
five years. Performance and drawdown (F-027) and the Sharpe frontier (F-029) are built on these returns.

`sbretire portfolio returns`:

- reads `data/prices/securities.yaml`, which maps each holding to its price file;
- converts every series to GBP month-end values, including dividends where the file carries them;
- writes `output/portfolio/returns.csv` and `returns_metadata.json` (each file's SHA-256 and date range);
- prints a coverage report: which holdings have full, short or no history, and their share of the household value.

Runs stay offline: the app only reads the files (SPEC §2; epic scope). Epic `portfolio-analysis`; requested by the
user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Price file layout | One CSV per series in `data/prices/` (git-ignored). Yahoo Finance's "Historical data" download is read as is (`Date,Open,High,Low,Close,Adj Close,Volume`, daily or monthly, ISO dates). Any other file needs only `Date,Close`, with an optional `Dividend` column (cash paid per unit on that date). Rows with `null`, empty or non-numeric prices are skipped | Yahoo is free and covers the US stocks and London ETFs; Vanguard fund prices can be typed into the minimal layout | user 2026-10-18 |
| 2 | Securities map | `data/prices/securities.yaml` (git-ignored; committed example `config/securities.example.yaml`): `fx:` names the USD/GBP file (GBP per USD, e.g. Yahoo `GBP=X`), and `securities:` lists each series with `id`, `name`, `file`, `quote` (`GBP`, `GBX` pence or `USD`) and `holdings` (`<account id>:<security key>`, one or more: the same ETF held in two accounts shares one series). Unknown keys, duplicate ids and a holding mapped twice are errors with their YAML location | One series per security, wherever it is held | this brief |
| 3 | Total return basis | Per series, in order: `Adj Close` when present (dividends already reinvested), else `Close` plus the `Dividend` column, else `Close` alone. The basis (`adjusted`, `dividends`, `price`) is reported per series, and `price` is flagged as possibly understating income units | Income units must add distributions (epic risk); accumulation units and adjusted prices need nothing | epic; user 2026-10-18 |
| 4 | Month-end | The last row in each calendar month is that month's value (works for daily and monthly files). A month's return in GBP is `(P_t + D_t) × X_t / (P_{t-1} × X_{t-1}) − 1`, with `P` in pounds (GBX ÷ 100), `D` the dividends paid in month t, and `X` the month-end GBP per unit of the quote currency (1 for GBP and GBX, the FX file for USD) | One convention for every provider and frequency | this brief |
| 5 | Window | 60 monthly returns (`--months`, default 60) ending with the last complete month before the newest export folder's month (`oct-26` → September 2026), so the first return is October 2021 and needs the September 2021 price | Matches "5 years monthly" (epic) and the holdings snapshot | epic |
| 6 | Gaps and short history | A month with no price inside a series' range is a gap: the returns into and out of it are missing and listed. A series starting after the window start is **short** and its months are reported. Neither stops the run | Honest coverage beats silent filling | this brief |
| 7 | Missing files | A holding with no series, or a series whose file is absent, is listed in the coverage report with its share of the household value; returns are written for the rest and the command exits 0 | User adds files a few at a time | user 2026-10-18 |
| 8 | Value shares | Coverage shares use F-025's valuation of the newest folder, with USD converted at the FX file's latest month-end rate (or `--usd-gbp` when given) | Shows what share of the money each gap affects | this brief |
| 9 | Output | `sbretire portfolio returns [--root] [--accounts] [--prices data/prices] [--output-dir output] [--months 60] [--usd-gbp R]` writes `output/portfolio/returns.csv` (UTF-8, LF; `month` (YYYY-MM), `series`, `value_gbp` (month-end value per unit in GBP), `dividend_gbp`, `return_gbp` (empty when missing), `basis`) and `returns_metadata.json` (window, and per file: path, SHA-256, first and last date, rows). Exit 0 run (even with gaps or missing files), 1 unreadable, 2 invalid map or unreadable price layout | Provenance as SPEC §10.3 asks of model inputs | epic |
| 10 | Tests | Synthetic price files only, with known-answer returns (constant growth, a dividend, a GBX series, a USD series with a moving rate, a gap) | Closed-form checks (CLAUDE.md) | this brief |

## 3. Context

- F-024/F-025 give `AccountConfig`, `month_folders`, `read_holdings` / `value_holdings` (`Valuation.value_gbp`) and
  `Holding.security_key` (Schwab and HL symbols or codes, Vanguard fund names, ii symbols).
- About 36 distinct securities in October 2026: US stocks (Schwab in USD; HL holds US stocks converted to GBP, but
  their prices are still quoted in USD), London-listed ETFs (some quoted in GBX, some in USD) and four Vanguard
  funds (prices from Vanguard's site).
- `data/prices/` and `data/factsheets/` are already git-ignored.

## 4. Touch-points

**New:** `src/sbretire/ledger/prices.py` (map config, price file reader, month-end series),
`src/sbretire/ledger/returns.py` (GBP returns, window, coverage, CSV and metadata), `config/securities.example.yaml`,
fixtures `tests/fixtures/prices/`, tests `tests/unit/test_prices_*.py`, `tests/unit/test_returns_*.py`.

**Modified:** `src/sbretire/__main__.py` (`portfolio returns`), `README.md`, `docs/THESAURUS.md` (Price Series,
Monthly Return), `docs/decisions/portfolio-data.md` (§11–§14).

## 5. Interfaces

```python
# sbretire/ledger/prices.py
Quote = Literal["GBP", "GBX", "USD"]


class SeriesConfig(BaseModel):  # frozen, extra=forbid
    id: str
    name: str
    file: str
    quote: Quote
    holdings: tuple[str, ...]  # "<account>:<security key>", min 1


class SecuritiesConfig(BaseModel):
    fx: dict[Literal["USD"], str]  # quote currency -> file of GBP per unit
    securities: tuple[SeriesConfig, ...]


def load_securities(path: Path) -> SecuritiesConfig: ...  # ScenarioError with locations


@dataclass(frozen=True)
class MonthEnd:
    month: dt.date  # first day of the month
    close: float  # quote units (GBX not yet divided)
    dividend: float  # paid in that month, quote units


@dataclass(frozen=True)
class PriceFile:
    path: Path
    basis: Literal["adjusted", "dividends", "price"]
    months: list[MonthEnd]
    first: dt.date
    last: dt.date
    rows: int
    sha256: str


def read_price_file(path: Path) -> PriceFile: ...  # raises PriceFileError


# sbretire/ledger/returns.py
@dataclass(frozen=True)
class MonthlyReturn:
    month: dt.date
    series: str
    value_gbp: float | None
    dividend_gbp: float
    return_gbp: float | None
    basis: str


def window(folder: str, months: int) -> tuple[dt.date, dt.date]: ...  # (first return month, last)
def gbp_returns(series: SeriesConfig, prices: PriceFile, fx: PriceFile | None,
                first: dt.date, last: dt.date) -> list[MonthlyReturn]: ...
def coverage(...) -> Coverage: ...  # full / short / gaps / missing, with GBP value shares
```

## 6. Plan of Work

1. Securities map and price file reader (Yahoo and minimal layouts, month-ends, SHA-256).
2. Monthly GBP total returns (adjusted, dividends, price; GBX; USD via the FX file; gaps; window).
3. Coverage report, `returns.csv`, `returns_metadata.json` and `sbretire portfolio returns`.
4. Docs and a local run on the real holdings.

## 7. Validation

- **T1:** reader on synthetic Yahoo (daily and monthly) and minimal files; known-answer returns: 1% a month gives
  0.01 every month; a dividend adds D/P; GBX equals the same GBP series; USD with the rate moving from 0.80 to 0.75
  gives the product of the two moves; a gap gives two missing returns.
- **T2:** the command on synthetic holdings plus price files: coverage classes, value shares, CSV and metadata.
- **T3:** on the real holdings with whatever price files exist (manual `check:`; prices never committed).

## 8. Decision Log

- 2026-10-18 — §2 #1 and #7 from the user's answers (Yahoo-style files; report missing and exit 0). The rest by me
  from the epic.

## 9. Surprises

- 2026-10-18 — F-026.1: pydantic reports a list whose only item failed as also "too short" (0 items after
  validation); `load_securities` drops that error when a deeper error under the same field explains it.

## 10. Tasks

### F-026.1 Securities map and price files
- **Status**: Verification
- **Depends on**: —

`ledger/prices.py`: `load_securities`, `read_price_file` (Yahoo daily/monthly, minimal with optional `Dividend`,
`null` rows skipped, last row per month, basis, SHA-256), `config/securities.example.yaml`. §2 #1–#3.

**Acceptance criteria**
- [x] `load_securities` accepts the example and rejects an unknown quote, a duplicate id, a holding mapped twice and an unknown key, each with its YAML location — `test_load_securities_validates`
- [x] Synthetic Yahoo daily and monthly files and a minimal file with dividends read to the same hand-checked month-ends, with basis `adjusted`, `adjusted` and `dividends`, null rows skipped and the file's SHA-256 — `test_read_price_file_layouts_to_month_ends`

**Notes**
2026-10-18 ledger/prices.py (SeriesConfig, SecuritiesConfig, load_securities with duplicate-id and mapped-twice checks, PriceFile/MonthEnd, read_price_file: Adj Close / Close+Dividend / Close, last row per month, null rows skipped, SHA-256), config/securities.example.yaml, tests/fixtures/prices/ (3 files); tests/unit/test_prices_files.py (2).

### F-026.2 Monthly GBP total returns
- **Status**: Verification
- **Depends on**: F-026.1

`ledger/returns.py`: `window`, `gbp_returns` (§2 #4–#6).

**Acceptance criteria**
- [x] Known answers: 1% monthly growth gives 0.01 each month; a dividend adds D/P_{t-1}; a GBX series equals its GBP twin; a USD series with the rate moving gives (1+r)(X_t/X_{t-1})−1; a missing month gives two missing returns; `window("oct-26", 60)` is October 2021 to September 2026 — `test_gbp_returns_known_answers`

**Notes**
2026-10-18 ledger/returns.py (MonthlyReturn, add_months, window, gbp_returns: GBX ÷ 100, USD via the FX series, dividends, missing months give no value and no return into or out of them); tests/unit/test_returns_gbp.py (closed-form cases).

### F-026.3 Coverage and `sbretire portfolio returns`
- **Status**: To Do
- **Depends on**: F-026.2

Coverage (full, short, gaps, missing, with value shares from the valuation), `returns.csv`,
`returns_metadata.json`, the command. §2 #5–#9.

**Acceptance criteria**
- [ ] On synthetic holdings and price files, coverage classes each holding as full, short (with its first month), gappy or missing, with GBP value shares that sum to 100%; holdings sharing one series are grouped — `test_coverage_classifies_holdings`
- [ ] `sbretire portfolio returns` writes `returns.csv` (UTF-8, LF, columns) and `returns_metadata.json` (window, SHA-256 per file), prints the coverage report and exits 0 with missing files; an invalid map exits 2 with its location — `test_cli_portfolio_returns`

### F-026.4 Docs and a local run
- **Status**: To Do
- **Depends on**: F-026.3

README section (getting Yahoo files, `securities.yaml`, the command), THESAURUS (Price Series, Monthly Return),
`docs/decisions/portfolio-data.md` §11–§14; run on the real holdings.

**Acceptance criteria**
- [ ] README documents the price files, `securities.yaml` and `portfolio returns`; THESAURUS defines Price Series and Monthly Return in alphabetical order; decisions recorded — `check: grep -n "portfolio returns" README.md docs/decisions/portfolio-data.md`
- [ ] On the real holdings the command runs and reports coverage (every holding missing until price files are supplied), exit 0 (run locally; never committed) — `check: uv run sbretire portfolio returns`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Securities map — `test_load_securities_validates`
2. Price file layouts — `test_read_price_file_layouts_to_month_ends`
3. GBP returns — `test_gbp_returns_known_answers`
4. Coverage — `test_coverage_classifies_holdings`
5. CLI — `test_cli_portfolio_returns`
6. Docs — `check: grep -n "portfolio returns" README.md docs/decisions/portfolio-data.md`
7. Real run — `check: uv run sbretire portfolio returns`
