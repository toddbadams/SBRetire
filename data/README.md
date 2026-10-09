# Data files and provenance

Per SPEC §19, a file is listed as present only once it has been downloaded, checked, and recorded below.

| File | Source | Publisher / dataset | Version / publication date | Retrieved | SHA-256 | Notes |
|---|---|---|---|---|---|---|
| `raw/ukppp24qx.xlsx` | ONS | [Mortality rates (qx), principal projection, UK](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies/datasets/mortalityratesqxprincipalprojectionunitedkingdom) — 2024-based edition | published 2026-05-15 | 2026-10-09 | `fbc6991bbeeab2691e0e7ce6aabf697fbcbe341a84f8dba6d11f48b29f4e6dac` | Exact download, unmodified. Period and cohort qx per 100,000, males/females, ages 0–100, 1981–2074 |
| `ons_mortality.csv` (+ `ons_mortality.meta.json`) | built | from `raw/ukppp24qx.xlsx` by `scripts/build_ons_mortality.py` | 2024-based | 2026-10-09 | in `run_metadata.json` | `sex,birth_year,age,qx`, qx a probability; rules in `docs/decisions/data-and-calibration.md` §1 |
| `raw/ons_cpi_d7g7.csv` | ONS | [CPI annual rate 00: all items 2015=100](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23) (series D7G7, dataset MM23) | released 2026-09-16 | 2026-10-09 | `ff87e9f1cc2412d1688a35b21c67243be6902b463ccbd9df19387109978fdcae` | Exact download, unmodified; annual rows 1989–2025 (%) plus quarterly/monthly rows |
| `raw/ons_cpi_d7bt.csv` | ONS | [CPI index 00: all items 2015=100](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23) (series D7BT, dataset MM23) | released 2026-09-16 | 2026-10-09 | `27a2473f818423a499fce4be23a2816d6670b1ae93b8eaaa11687c2237322865` | Exact download, unmodified; used only to cross-check D7G7 |
| `uk_cpi.csv` (+ `uk_cpi.meta.json`) | built | from `raw/ons_cpi_d7g7.csv` by `scripts/build_uk_cpi.py` | D7G7 (released 2026-09-16) | 2026-10-09 | in `run_metadata.json` | `year,annual_rate` (decimal), 1989–2025; calibration rules in `docs/decisions/data-and-calibration.md` §2 |

Reference landing pages (starting points only — record the exact file you download):

- https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections
- https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies

Raw downloads go in `data/raw/` unmodified; any transformation into the model's CSV shape must be
a script in `scripts/` so it is reproducible.

## Mortality (`ons_mortality.csv`)

Rebuild from the raw workbook (dev dependency `openpyxl`; output is byte-identical to the committed files):

```bash
uv run python scripts/build_ons_mortality.py
```

- **Columns**: `sex` (`male`/`female`, from the workbook's `males`/`females` sheets), `birth_year`, `age` (exact age,
  0–100), `qx` = probability of dying between exact age x and x + 1 (ONS value ÷ 100,000).
- **Construction**: period sheets read along the cohort diagonal (q for birth year b at age x = period q at age x in
  year b + x — verified equal to the cohort sheets on every overlapping cell), so cohorts born before 1981 are covered;
  years after 2074 come from the cohort sheets (ONS projection, birth years 1981–2074); ages 95–100 in 2075–2080 are
  interpolated log-linearly between the 2074 value and the birth-year-1981 value.
- **Use in the model**: a person aged x uses q(x, b + x) for that whole year of age; above 100 the cohort's age-100
  rate is held (`docs/decisions/data-and-calibration.md` §1).
- `ons_mortality.meta.json` records source, geography, projection, publication and retrieval dates and the raw
  file's SHA-256; the loader checks it against the config's `mortality` section.

## Inflation (`uk_cpi.csv`)

Rebuild from the raw downloads (output is byte-identical to the committed files):

```bash
uv run python scripts/build_uk_cpi.py
```

- **Columns**: `year`, `annual_rate` = the D7G7 calendar-year CPI annual rate as a decimal (5.2 % → 0.052).
- **Check**: every year must agree with the change in the D7BT annual-average index within 0.15 percentage points
  (the index is published to one decimal place); the build fails otherwise.
- `uk_cpi.meta.json` records series, dataset, release and retrieval dates and both raw files' SHA-256.
