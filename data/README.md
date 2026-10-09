# Data files and provenance

Per SPEC §19, a file is listed as present only once it has been downloaded, checked, and recorded below.

| File | Source | Publisher / dataset | Version / publication date | Retrieved | SHA-256 | Notes |
|---|---|---|---|---|---|---|
| `raw/ukppp24qx.xlsx` | ONS | [Mortality rates (qx), principal projection, UK](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies/datasets/mortalityratesqxprincipalprojectionunitedkingdom) — 2024-based edition | published 2026-05-15 | 2026-10-09 | `fbc6991bbeeab2691e0e7ce6aabf697fbcbe341a84f8dba6d11f48b29f4e6dac` | Exact download, unmodified. Period and cohort qx per 100,000, males/females, ages 0–100, 1981–2074 |
| `ons_mortality.csv` (+ `ons_mortality.meta.json`) | built | from `raw/ukppp24qx.xlsx` by `scripts/build_ons_mortality.py` | 2024-based | 2026-10-09 | in `run_metadata.json` | `sex,birth_year,age,qx`, qx a probability; rules in `docs/decisions/data-and-calibration.md` §1 |
| `uk_cpi.csv` | ONS | CPI annual rate (series D7G7 or equivalent) | _tbd_ | _tbd_ | _tbd_ | Calibration period recorded in config |

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
