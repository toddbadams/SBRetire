---
id: F-007
type: feature
parent: stochastic-inputs
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-007 ONS Mortality Data Ingest and Mapping

## 1. Purpose

Give the model a verified, local, versioned source of **annual death probabilities** q for each person: ONS
2024-based UK cohort mortality, principal projection (SPEC §7.1). A one-off build script turns the exact downloaded
ONS workbook into `data/ons_mortality.csv` plus a provenance sidecar; a loader validates it (SPEC §4.3: invalid
values, coverage of required ages/years) and answers q(sex, birth year, age) with a documented rule above age 100.
Provenance goes in `data/README.md` and into Run Metadata (SPEC §4.2 Mortality, §10.3, §19).

Resolves SPEC §18 "Exact ONS file/table and age/period mapping used for cohort mortality" (data-and-calibration §1).
Sampling death months from these rates is F-008.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Dataset | ONS "Mortality rates (qx), principal projection, UK", 2024-based edition, file `ukppp24qx.xlsx` (published 2026-05-15, retrieved 2026-10-09, SHA-256 `fbc6991b…6dac`) | SPEC §7.1 names ONS 2024-based UK principal; this is its qx table by single year of age 0–100, 1981–2074 | SPEC §7.1; data-and-calibration §1 |
| 2 | Table construction | Period sheets give q(x, y) for 1981–2074. Verified: cohort qx(b, x) == period qx(b + x, x) exactly on all 4,465 overlapping cells per sex, so period sheets read along (age, b + x) *are* the cohort rates, covering cohorts born before 1981. For y > 2074 use the cohort sheets (ONS's own projection, ≈1.1 %/yr improvement, to 2174). Remaining gap — ages 95–100 in 2075–2080 (birth years 1975–1980) — filled by log-linear interpolation in q between (x, 2074) and (x, 1981 + x) | No invented improvement; younger households can run long horizons | Interview Q1 |
| 3 | Above age 100 | q(x, ·) = q(100, b + 100) for every x > 100 (hold the cohort's age-100 rate) | Conservative (never shortens lives below ONS's last published rate); no parameters; close to the observed ≈0.5 plateau | Interview Q2 |
| 4 | Age/period mapping | A person aged x (completed years, counted from the birth month) uses q(x, b + x) for that whole year of age, b = birth year | Exactly ONS's cohort qx definition; one rate per year of age | Interview Q3 |
| 5 | CSV shape | `data/ons_mortality.csv`: columns `sex,birth_year,age,qx`; `sex` ∈ {male, female}; `qx` a probability (ONS value ÷ 100,000) written with `repr`-exact floats; sorted by sex, birth_year, age; LF; one row per available (sex, birth_year, age), ages 0–100 | Matches the lookup in #4; long form validates simply | Brief author |
| 6 | Sex mapping | Workbook sheets `males …` → `male`, `females …` → `female`; no other category accepted | SPEC §4.2: no inference or silent transformation | SPEC §4.2 |
| 7 | Provenance sidecar | `data/ons_mortality.meta.json`: `source` (`ONS_2024_BASED`), `geography` (`UK`), `projection` (`principal`), `publication_date`, `retrieved`, `source_url`, `raw_file`, `raw_sha256`, `units` (`probability`), `age_max` (100) | Feeds Run Metadata (F-005 `DataFileRecord.version/retrieved`); lets the loader check the config refers to this dataset | SPEC §4.2 Mortality |
| 8 | Config check | Loader rejects a table whose sidecar `source/geography/projection` differ from `mortality.*` in the Scenario | Fail fast on a mismatched dataset | SPEC §4.3 |
| 9 | Coverage | For each person, every age from their age at the As-Of month to 100 must be present for their birth year; ages > 100 are covered by #3. Reported as `ScenarioIssue`s; `sbretire validate --require-data-files` loads the table and fails (exit 2) on any issue | SPEC §4.3 | SPEC §4.3 |
| 10 | Raw data | `data/raw/ukppp24qx.xlsx` committed unmodified; the build script is never called by a run; `openpyxl` is a **dev** dependency only | SPEC §2 (no downloads in a run), §19 (preserve the exact download) | SPEC §2, §19 |
| 11 | Placement | `scripts/build_ons_mortality.py`; `src/sbretire/mortality.py` | SPEC §3 | SPEC §3 |

## 3. Context

- `MortalityAssumptions(source, geography, projection, data_file)` (F-001); `data_file` resolved against the config
  directory; `--require-data-files` currently checks only that the file exists.
- `Person.sex: Literal["male", "female"]`, `date_of_birth` (any day; only year and month matter).
- `metadata.DataFileRecord(role, path, sha256, version, retrieved)` and `file_sha256` (F-005).
- Example configs point at `../data/ons_mortality.csv`, which this feature creates.
- Workbook facts (inspected 2026-10-09): sheets `males period qx`, `females period qx`, `males cohort qx`,
  `females cohort qx`; header row 4 (`Exact age (years)`, `Year 1981` / `Year of birth 1981`, `1982` … `2074`);
  ages 0–100 in rows 5–105; values per 100,000; no blanks.
- Check: a person b. 1964 reaches 100 in 2064, one b. 1968 in 2068 — both within period data; above 100
  the tail rule applies for the rest of the 60-year horizon.

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `data/raw/ukppp24qx.xlsx` | Exact ONS download (committed with this brief) |
| `scripts/build_ons_mortality.py` | Workbook → CSV + sidecar (one-off, reproducible) |
| `data/ons_mortality.csv`, `data/ons_mortality.meta.json` | Model inputs |
| `src/sbretire/mortality.py` | `MortalityTable`, `load_mortality_table`, `annual_q`, `coverage_issues`, `data_file_record` |
| `tests/tooling/test_build_ons_mortality.py`, `tests/unit/test_mortality.py` | Tests |
| `tests/fixtures/mortality/` | Small hand-made CSV + sidecar fixtures |

**Modified**

| File | Change |
|---|---|
| `pyproject.toml`, `uv.lock` | `openpyxl` in the dev group |
| `data/README.md` | Provenance row filled; build command; rules |
| `src/sbretire/__main__.py` | `validate --require-data-files` loads the table and reports coverage issues |
| `README.md` | Mortality section |
| `docs/decisions/data-and-calibration.md` | §1 (with this brief) |

## 5. Interfaces

```python
# sbretire/mortality.py
Sex = Literal["male", "female"]
AGE_MAX: Final = 100  # last tabulated age; above it the tail rule holds q(100, b + 100)


class MortalityTableError(ValueError):
    issues: tuple[
        ScenarioIssue, ...
    ]  # location like "ons_mortality.csv:42" or "ons_mortality.meta.json:projection"


@dataclass(frozen=True)
class MortalityTable:
    path: Path
    meta: Mapping[str, object]  # the sidecar contents

    def annual_q(self, sex: Sex, birth_year: int, ages: NDArray[np.int64]) -> NDArray[np.float64]:
        """Annual probability of dying between exact age x and x+1 for the cohort born in ``birth_year``.
        Ages > 100 use q(100, birth_year + 100). KeyError naming sex/birth_year/age if not covered."""

    def has(self, sex: Sex, birth_year: int, age: int) -> bool: ...
    def data_file_record(self) -> DataFileRecord: ...  # role "mortality", sha256, version, retrieved


def load_mortality_table(path: Path, mortality: MortalityAssumptions | None = None) -> MortalityTable: ...
def coverage_issues(table: MortalityTable, scenario: Scenario) -> list[ScenarioIssue]: ...
```

CSV columns: `sex,birth_year,age,qx`. Sidecar keys as §2 #7.

## 6. Plan of Work

1. Build script + committed CSV + sidecar + `data/README.md` provenance.
2. `load_mortality_table` with schema, value and config checks.
3. `annual_q` (tail), `coverage_issues`, CLI validate hook, `data_file_record`, README.

## 7. Validation

- **T1**: unit tests (fixture CSVs), ruff, mypy.
- **T2**: `sbretire validate --config config/model.example.yaml --require-data-files` exits 0 against the real file.
- **T3**: regression snapshot — known q values from the workbook pinned (period cells, an extension cell, a gap cell)
  and the build reproduces the committed CSV byte-for-byte.

## 8. Decision Log

- 2026-10-09 — Dataset `ukppp24qx.xlsx`; period sheets for 1981–2074, cohort-sheet extension to 2174, log-linear gap
  fill (Interview Q1; data-and-calibration §1).
- 2026-10-09 — Above 100: hold q(100, b + 100) (Interview Q2).
- 2026-10-09 — Lookup q(x, b + x) for the whole year of age (Interview Q3).

## 9. Surprises

- 2026-10-09 — The cohort sheets are indexed by **year of birth 1981–2074**, so they don't contain anyone born before
  1981; the period sheets do, and match the cohort sheets exactly on the diagonal.

## 10. Tasks

### F-007.1 Build the mortality CSV and provenance
- **Status**: Verification
- **Depends on**: —

Add `openpyxl` to the dev group. Write `scripts/build_ons_mortality.py` (reads `data/raw/ukppp24qx.xlsx`, applies §2
#2, #5–#7, writes `data/ons_mortality.csv` and `data/ons_mortality.meta.json`); run it and commit the outputs; fill
the `data/README.md` row and document the build command. Tests in `tests/tooling/test_build_ons_mortality.py`.

**Acceptance criteria**
- [x] Running the build into a temp dir reproduces the committed CSV and sidecar byte-for-byte — `test_build_ons_mortality_reproduces_committed_files`
- [x] Known cells: male b. 1964 age 62 = 0.0092454 (period 2026); female b. 1969 age 57 = 0.0039146 (period 2026); a y > 2074 cell equals the cohort sheet value ÷ 100,000 — `test_ons_mortality_known_answers`
- [x] Gap cells (ages 95–100, years 2075–2080) are log-linear between their endpoints and lie strictly between them — `test_build_fills_gap_log_linear`
- [x] Every row has sex ∈ {male, female}, 0 < qx < 1, ages 0–100, and no duplicate (sex, birth_year, age) — `test_ons_mortality_csv_is_well_formed`
- [x] `data/README.md` records file, URL, publication date, retrieval date and the raw SHA-256 that `file_sha256` computes — `check: grep fbc6991bbeeab2691e0e7ce6aabf697fbcbe341a84f8dba6d11f48b29f4e6dac data/README.md data/ons_mortality.meta.json`

**Notes**
- 2026-10-09 Added `scripts/build_ons_mortality.py` (openpyxl, layout checks per sheet, Decimal ÷ 100,000, cohort/period agreement asserted, log-linear gap); built and committed `data/ons_mortality.csv` (29,088 rows: 2 sexes × birth years 1881–2074) and `data/ons_mortality.meta.json`; `data/README.md` provenance + build section; `openpyxl`/`types-openpyxl` dev deps; ruff `known-local-folder` += build_ons_mortality. Tests `tests/tooling/test_build_ons_mortality.py` (5, incl. sidecar provenance).

### F-007.2 Mortality table loader and validation
- **Status**: To Do
- **Depends on**: F-007.1

`src/sbretire/mortality.py`: `load_mortality_table`, `MortalityTableError` (§5). Fixtures in
`tests/fixtures/mortality/`; tests in `tests/unit/test_mortality.py`.

**Acceptance criteria**
- [ ] The real `data/ons_mortality.csv` loads and its sidecar matches `config/model.example.yaml` — `test_load_mortality_table_real_file`
- [ ] Missing/extra column, non-numeric value, duplicate (sex, birth_year, age), qx outside [0, 1] or non-finite, and unknown sex each raise `MortalityTableError` with the file row and a fix-it message — `test_load_mortality_table_rejects_invalid_rows`
- [ ] Missing sidecar, or sidecar `source`/`geography`/`projection` differing from the Scenario's `mortality`, is rejected naming both values — `test_load_mortality_table_rejects_mismatched_sidecar`

### F-007.3 Lookup, tail rule and coverage
- **Status**: To Do
- **Depends on**: F-007.2

`MortalityTable.annual_q`, `has`, `data_file_record`; `coverage_issues`; `sbretire validate --require-data-files`
reports coverage issues; README mortality section; data-and-calibration §1 already recorded with the brief.

**Acceptance criteria**
- [ ] `annual_q` is vectorised over ages, returns float64, matches table cells, and ages > 100 equal q(100, b + 100) — `test_annual_q_lookup_and_tail`
- [ ] An age ≤ 100 not in the table raises `KeyError` naming sex, birth year and age — `test_annual_q_uncovered_age_raises`
- [ ] `coverage_issues` is empty for the example scenario and names `people[i].date_of_birth` when a fixture table lacks a needed age — `test_coverage_issues_reports_missing_ages`
- [ ] `sbretire validate --require-data-files` exits 0 on the example config and 2 with the coverage message on a gapped fixture — `test_cli_validate_reports_mortality_coverage`
- [ ] `data_file_record()` gives role `mortality`, the CSV's SHA-256, version `2024-based (published 2026-05-15)` and retrieved `2026-10-09` — `test_mortality_data_file_record`
- [ ] README documents the dataset, the q(x, b + x) rule and the age-100 tail — `check: grep -n "ons_mortality.csv" README.md`

## 11. Open Questions

- Request ages up to 125 from ONS (pop.info@ons.gov.uk) as a later refinement of the tail rule — not needed for V1.

## 12. Acceptance Criteria

1. Build reproduces committed files — `test_build_ons_mortality_reproduces_committed_files`
2. Known q cells — `test_ons_mortality_known_answers`
3. Gap fill log-linear — `test_build_fills_gap_log_linear`
4. CSV well formed — `test_ons_mortality_csv_is_well_formed`
5. Provenance recorded — `check: grep raw SHA-256 in data/README.md and the sidecar`
6. Real file loads — `test_load_mortality_table_real_file`
7. Invalid rows rejected — `test_load_mortality_table_rejects_invalid_rows`
8. Sidecar mismatch rejected — `test_load_mortality_table_rejects_mismatched_sidecar`
9. Lookup + tail — `test_annual_q_lookup_and_tail`
10. Uncovered age raises — `test_annual_q_uncovered_age_raises`
11. Coverage issues — `test_coverage_issues_reports_missing_ages`
12. CLI coverage — `test_cli_validate_reports_mortality_coverage`
13. Data-file record — `test_mortality_data_file_record`
14. README — `check: grep -n "ons_mortality.csv" README.md`
