# Data files and provenance

No data files are committed yet. Per SPEC §19, do not claim a file is present until it has been
downloaded, checked, and recorded below.

| File | Source | Publisher / dataset | Version / publication date | Retrieved | SHA-256 | Notes |
|---|---|---|---|---|---|---|
| `ons_mortality.csv` | ONS | 2024-based UK cohort life tables, principal projection | _tbd_ | _tbd_ | _tbd_ | Mapping age/sex/year → q(x,y) documented in an ADR |
| `uk_cpi.csv` | ONS | CPI annual rate (series D7G7 or equivalent) | _tbd_ | _tbd_ | _tbd_ | Calibration period recorded in config |

Reference landing pages (starting points only — record the exact file you download):

- https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationprojections
- https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/lifeexpectancies

Raw downloads go in `data/raw/` unmodified; any transformation into the model's CSV shape must be
a script in `scripts/` so it is reproducible.
