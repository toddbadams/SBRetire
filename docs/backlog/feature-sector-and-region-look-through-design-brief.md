---
id: F-028
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 5
created: 2026-10-18
updated: 2026-10-18
---
# F-028 Sector and Region Look-Through

## 1. Purpose

Show **what the household's savings are invested in**, looking through funds to what they hold:

- asset class (equity, bond, cash, property, other);
- sector (the 11 GICS sectors);
- region;
- currency;
- the largest underlying holdings across all funds and stocks.

Every figure is in GBP and as a share of today's household value. `sbretire portfolio exposure` reads:

- a factsheet per fund (`data/factsheets/<file>.yaml`, weights copied from the fund's published factsheet);
- `sector:` / `region:` on each single-stock series in `data/prices/securities.yaml`;
- today's valuation (F-025).

It prints the tables and writes `output/portfolio/exposure.csv`. The Portfolio page (F-030) and the
re-weighting analysis (F-029) use the same exposures.

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Where the data lives | A fund's series names `factsheet: <file>.yaml` (in `data/factsheets/`, git-ignored). A single stock's series sets `sector:`, `region:` and optionally `asset_class:` (default `equity`) and `currency:` (default from the region). A series with neither is **unclassified** | One file per fund, copied from its factsheet; a stock needs one line | user 2026-10-18 |
| 2 | Factsheet file | `as_of` (date), `source` (text), `asset_classes`, `sectors`, `regions`, optional `currencies` and optional `top_holdings` (name: weight). Each weight map is a share of the fund's total value: fractions summing to 0.98–1.02, or percentages summing to 98–102, rescaled to exactly 1. A map outside that range is an error with its location. A missing map leaves that dimension unclassified for the fund. `top_holdings` need not sum to 1, since factsheets list only the largest | Factsheets print percentages that rarely add to exactly 100 | this brief |
| 3 | Fixed names | **Sectors:** Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities, Other. **Regions:** UK, North America, Europe ex UK, Japan, Asia Pacific ex Japan, Emerging Markets, Other. **Asset classes:** equity, bond, cash, property, other. **Currencies:** GBP, USD, EUR, JPY, Other. Matching ignores case. A short alias list maps common factsheet wording (e.g. "Technology" → Information Technology, "Healthcare" → Health Care, "United States" → North America, "Europe ex-UK" → Europe ex UK, "Fixed Income" → bond). Any other name is an error with its location | Typos never split a sector; factsheets from different managers line up | user 2026-10-18 |
| 4 | Look-through arithmetic | A holding's GBP value × the fund's weight for each label. Sector and region weights are of the fund's whole value, so a 60/40 fund's sectors add to about 60% plus Other/bond lines as the factsheet gives them. Values add up across holdings and accounts | Shares are of today's household value | this brief |
| 5 | Cash | Each account's cash is asset class `cash`, sector and region `Cash`, currency = the account's currency | Cash is part of the household total | this brief |
| 6 | Currency | From the factsheet's `currencies` when given. Otherwise from regions: UK → GBP, North America → USD, Europe ex UK → EUR, Japan → JPY, else Other. The approximated share is reported | Currency exposure is not the quote currency (a GBX-quoted ETF of US stocks is USD exposure) | this brief |
| 7 | Unclassified | Holdings in no series, series with neither factsheet nor stock fields, and dimensions a factsheet leaves out are shown as an **Unclassified** line in each table, so every table adds to 100% | Gaps stay visible | this brief |
| 8 | Top look-through holdings | Each stock counts as one holding (its series name). Each fund's `top_holdings` add `value × weight` under the holding's name, matched ignoring case and punctuation. The 15 largest are shown with their share of the household value; the report notes that funds disclose only their largest holdings | Shows concentration hidden inside funds (epic) | epic |
| 9 | Staleness | A factsheet whose `as_of` is more than 12 months before the newest valuation date gets a warning | Weights drift | this brief |
| 10 | Output | `sbretire portfolio exposure [--root] [--accounts] [--prices] [--factsheets data/factsheets] [--output-dir] [--usd-gbp R]` prints one table per dimension plus the top holdings, and writes `exposure.csv` (`dimension`, `label`, `value_gbp`, `share`). Exit 0 ok, 1 unreadable, 2 invalid factsheet or map. USD values use `--usd-gbp` or the FX file's latest month-end (as F-026) | Same pattern as the other portfolio commands | this brief |
| 11 | Tests | Synthetic factsheets and holdings only: percentage and fraction maps, aliases, an unknown name, a 60/40 fund, a stock, cash, an unclassified holding, region-derived currency and top holdings shared by two funds | Known answers by hand | this brief |

## 3. Context

- **From F-025 and F-026:**
  - F-025: `read_holdings`, `value_holdings`, `Valuation.value_gbp` and `Holding.kind`.
  - F-026: `SeriesConfig` / `load_securities` (this feature extends them) and the USD rate fallback in
    `build_returns`, factored out here so both commands share it.
- **The holdings:**
  - about 20 single stocks (Schwab; HL's US stocks);
  - about 12 ETFs and funds (Vanguard LifeStrategy and Target Retirement funds, iShares and Invesco sector ETFs,
    Vanguard FTSE All-World, VHYL);
  - Vanguard's own Asset Sector column is misleading (epic), so factsheets are the source.
- **Privacy:** `data/factsheets/` is git-ignored.

## 4. Touch-points

**New:** `src/sbretire/ledger/exposure.py` (taxonomy, aliases, factsheet loader, look-through, CSV, summary),
`config/factsheet.example.yaml`, tests `tests/unit/test_exposure_*.py`.

**Modified:**
- `src/sbretire/ledger/prices.py`: `factsheet`, `sector`, `region`, `asset_class` and `currency` on
  `SeriesConfig`.
- `src/sbretire/ledger/returns.py`: shared today's-values helper.
- `config/securities.example.yaml`.
- `src/sbretire/__main__.py`: `portfolio exposure`.
- `README.md`.
- `docs/THESAURUS.md`: Look-Through, Factsheet.
- `docs/decisions/portfolio-data.md`: §18–§20.

## 5. Interfaces

```python
# sbretire/ledger/exposure.py
SECTORS: Final[tuple[str, ...]]
REGIONS: Final[tuple[str, ...]]
ASSET_CLASSES: Final[tuple[str, ...]]
CURRENCIES: Final[tuple[str, ...]]
Dimension = Literal["asset_class", "sector", "region", "currency"]


def canonical(dimension: Dimension, label: str) -> str | None: ...  # alias-aware; None if unknown


@dataclass(frozen=True)
class Factsheet:
    path: Path
    as_of: dt.date
    source: str
    weights: dict[Dimension, dict[str, float]]  # each rescaled to 1; missing dimension absent
    currency_derived: bool  # currencies came from regions
    top_holdings: dict[str, float]


def load_factsheet(path: Path) -> Factsheet: ...  # ScenarioError with locations


@dataclass(frozen=True)
class Exposure:
    tables: dict[Dimension, dict[str, float]]  # label -> GBP, incl. "Unclassified" / "Cash"
    top_holdings: list[tuple[str, float]]  # name, GBP, largest first
    total_gbp: float
    approximated_currency_gbp: float
    warnings: list[str]


def look_through(
    values: Mapping[str, float],
    cash: Mapping[str, float],
    securities: SecuritiesConfig,
    factsheets: Mapping[str, Factsheet],
) -> Exposure: ...
```

## 6. Plan of Work

1. Taxonomy, aliases, the new `SeriesConfig` fields and the factsheet loader.
2. Look-through: funds, stocks, cash, unclassified, currencies, top holdings.
3. `sbretire portfolio exposure`, `exposure.csv` and the summary.
4. Docs, example factsheet, local run.

## 7. Validation

- **T1:** loader on synthetic factsheets: percentages vs fractions, rescaling, aliases, unknown names and bad sums
  with locations. Look-through on hand-sized values: a £60 60/40 fund, a £30 stock, £10 cash and a £20
  unclassified holding give hand-checked tables that each add to £120.
- **T2:** the command on the F-026 synthetic holdings with synthetic factsheets: tables, CSV, exit 2 on a bad
  factsheet.
- **T3:** the real holdings (all unclassified until factsheets exist): `check:`.

## 8. Decision Log

- 2026-10-18 — §2 #1 and #3 from the user's answers (YAML per fund with stock fields in `securities.yaml`; fixed
  lists with aliases). The rest by me.

## 9. Surprises

## 10. Tasks

### F-028.1 Taxonomy, series fields and factsheets
- **Status**: Verification
- **Depends on**: —

`ledger/exposure.py` (lists, aliases, `canonical`, `load_factsheet`); `SeriesConfig` gains `factsheet`, `sector`,
`region`, `asset_class`, `currency`, with stock fields validated against the lists. §2 #1–#3.

**Acceptance criteria**
- [x] Aliases and case map to the fixed names and unknown names give `None`; a series with an unknown `sector` or `region` is rejected with its location — `test_taxonomy_and_series_fields`
- [x] A factsheet in percentages and one in fractions load to the same rescaled weights; an unknown label, a sector map summing to 0.9 and a missing `as_of` are each rejected with their location; omitting `currencies` derives them from the regions and says so — `test_load_factsheet`

**Notes**
2026-10-18 ledger/taxonomy.py (fixed names, aliases, canonical, region_currency) — the taxonomy sits in its own module so prices.py can validate stock fields without importing exposure.py; SeriesConfig gains factsheet, sector, region, asset_class, currency; ledger/exposure.py Factsheet and load_factsheet (fractions or percentages, rescaled, aliases merged, currencies derived from regions); tests/unit/test_exposure_factsheets.py (2).

### F-028.2 Look-through
- **Status**: Verification
- **Depends on**: F-028.1

`look_through` (§2 #4–#9).

**Acceptance criteria**
- [x] For a £60 fund (60% equity / 40% bond, with sectors, regions and top holdings), a £30 stock (Information Technology, North America), £10 GBP cash and a £20 holding in no series, every table adds to £120 with hand-checked lines, including Unclassified and Cash; currencies are derived from regions for the fund and flagged; a holding named in two funds' top holdings adds up under one name — `test_look_through_known_answers`

**Notes**
2026-10-18 ledger/exposure.py Exposure, look_through (funds by factsheet weights, stocks by series fields, cash by currency, Unclassified for unknowns and missing dimensions, region-derived currencies counted, top holdings merged by name ignoring case and punctuation); tests/unit/test_exposure_look_through.py (typing tidied: no ignores).

### F-028.3 `sbretire portfolio exposure`
- **Status**: To Do
- **Depends on**: F-028.2

The command, the shared today's-values helper, `exposure.csv` and the summary, and the stale-factsheet warning.
§2 #9–#10.

**Acceptance criteria**
- [ ] On the F-026 synthetic holdings with synthetic factsheets, the command prints the asset class, sector, region and currency tables and the top holdings, each with GBP and share, writes `exposure.csv` (UTF-8, LF, columns, every dimension adding to the household total), warns on a factsheet over 12 months old, and exits 2 with the location on a bad factsheet — `test_cli_portfolio_exposure`

### F-028.4 Docs and a local run
- **Status**: To Do
- **Depends on**: F-028.3

README section, `config/factsheet.example.yaml`, `config/securities.example.yaml` stock fields, THESAURUS
(Look-Through, Factsheet, sorted), `docs/decisions/portfolio-data.md` §18–§20; run on the real holdings.

**Acceptance criteria**
- [ ] README documents factsheets, the stock fields, the fixed names and `portfolio exposure`; THESAURUS defines Factsheet and Look-Through in order; decisions recorded — `check: grep -n "portfolio exposure" README.md docs/decisions/portfolio-data.md`
- [ ] On the real holdings the command runs (all unclassified until factsheets exist), exit 0 (run locally; never committed) — `check: uv run sbretire portfolio exposure --usd-gbp 0.7503`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Taxonomy and series fields — `test_taxonomy_and_series_fields`
2. Factsheets — `test_load_factsheet`
3. Look-through — `test_look_through_known_answers`
4. CLI — `test_cli_portfolio_exposure`
5. Docs — `check: grep -n "portfolio exposure" README.md docs/decisions/portfolio-data.md`
6. Real run — `check: uv run sbretire portfolio exposure --usd-gbp 0.7503`
