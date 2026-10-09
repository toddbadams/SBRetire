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
- 2026-10-09 — F-007.2: test fixtures are generated per test in tmp_path (`tests/unit/mortality_fixtures.py`) rather than committed under `tests/fixtures/mortality/` as §4 listed.
- 2026-10-09 — F-007.3: Run Metadata's dataset version needed an `edition` field ("2024-based") in the sidecar — added to the build script and made a required sidecar key.

## 10. Tasks

### F-007.1 Build the mortality CSV and provenance
- **Status**: Done
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
- 2026-10-09 /verify PASS:
  - test_build_ons_mortality.py: 5 passed; rebuild into scratch byte-identical (csv sha256 cb562589…76d2, meta 04588e0d…0d8b)
  - independent openpyxl check: 30 period cells, 20 cohort cells (y > 2074), 42 gap cells log-linear and strictly between endpoints — 0 mismatches; 29,088 rows, birth years 1881–2074
  - raw sha256 fbc6991b…6dac in data/README.md and meta.json; URL, dates and build command documented
  - ruff + mypy clean; openpyxl only in the dev group, absent from src/

### F-007.2 Mortality table loader and validation
- **Status**: Done
- **Depends on**: F-007.1

`src/sbretire/mortality.py`: `load_mortality_table`, `MortalityTableError` (§5). Fixtures in
`tests/fixtures/mortality/`; tests in `tests/unit/test_mortality.py`.

**Acceptance criteria**
- [x] The real `data/ons_mortality.csv` loads and its sidecar matches `config/model.example.yaml` — `test_load_mortality_table_real_file`
- [x] Missing/extra column, non-numeric value, duplicate (sex, birth_year, age), qx outside [0, 1] or non-finite, and unknown sex each raise `MortalityTableError` with the file row and a fix-it message — `test_load_mortality_table_rejects_invalid_rows`
- [x] Missing sidecar, or sidecar `source`/`geography`/`projection` differing from the Scenario's `mortality`, is rejected naming both values — `test_load_mortality_table_rejects_mismatched_sidecar`

**Notes**
- 2026-10-09 Added `src/sbretire/mortality.py`: `load_mortality_table` (csv module, collects every issue with `ons_mortality.csv:<line>` locations; header, value count, sex, whole-number ages, qx finite in [0, 1], duplicates; sidecar required keys and source/geography/projection vs config), `MortalityTableError(issues)`, `MortalityTable` with read-only dense per-sex grids and `has`, `sidecar_path`. Tests `tests/unit/test_mortality.py` (16) using `tests/unit/mortality_fixtures.py` (tables written to tmp_path instead of a committed `tests/fixtures/mortality/` dir — each case needs its own variant).
- 2026-10-09 /verify PASS:
  - load tests: 16 passed
  - probes: CRLF CSV loads; three bad rows reported at their exact lines; qx 0 and 1 accepted; invalid-JSON sidecar -> MortalityTableError; missing CSV -> FileNotFoundError with path; grids read-only
  - real table loads in 0.043 s; has(male,1964,62) True, has(male,1964,16) False
  - ruff + mypy clean; no network imports or global np.random

### F-007.3 Lookup, tail rule and coverage
- **Status**: Verification
- **Depends on**: F-007.2

`MortalityTable.annual_q`, `has`, `data_file_record`; `coverage_issues`; `sbretire validate --require-data-files`
reports coverage issues; README mortality section; data-and-calibration §1 already recorded with the brief.

**Acceptance criteria**
- [x] `annual_q` is vectorised over ages, returns float64, matches table cells, and ages > 100 equal q(100, b + 100) — `test_annual_q_lookup_and_tail`
- [x] An age ≤ 100 not in the table raises `KeyError` naming sex, birth year and age — `test_annual_q_uncovered_age_raises`
- [x] `coverage_issues` is empty for the example scenario and names `people[i].date_of_birth` when a fixture table lacks a needed age — `test_coverage_issues_reports_missing_ages`
- [x] `sbretire validate --require-data-files` exits 0 on the example config and 2 with the coverage message on a gapped fixture — `test_cli_validate_reports_mortality_coverage`
- [x] `data_file_record()` gives role `mortality`, the CSV's SHA-256, version `2024-based (published 2026-05-15)` and retrieved `2026-10-09` — `test_mortality_data_file_record`
- [x] README documents the dataset, the q(x, b + x) rule and the age-100 tail — `check: grep -n "ons_mortality.csv" README.md`

**Notes**
- 2026-10-09 Added `MortalityTable.annual_q` (vectorised, any shape; ages > 100 use q(100, b + 100); KeyError naming sex/birth year/age), `data_file_record`, `coverage_issues` (ages from age at As-Of to 100, ASCII ranges) in `src/sbretire/mortality.py`; `validate --require-data-files` now loads the table and reports table/coverage issues (exit 2) via `_check_mortality` in `src/sbretire/__main__.py`; sidecar gains `edition` (build script + rebuilt `data/ons_mortality.meta.json`; required key); README mortality section. 7 tests added to `tests/unit/test_mortality.py`. Example and personal configs validate against the real table.
- 2026-10-09 /verify FAIL: a birth year outside the table raises KeyError 'no female mortality rates for birth year 1800 in ons_mortality.csv (covers 1881-2074)' without the age; `test_annual_q_uncovered_age_raises` didn't assert the age for that case. All other steps passed (lookup vs CSV, tail, dtype/shape, coverage probe, CLI exit codes + ASCII stderr, data_file_record, README). Minor: README still described `--require-data-files` as an existence check only.
- 2026-10-09 Fix after /verify FAIL: out-of-range birth year KeyError now names the first requested age ("no female mortality rate for birth year 1800 at age 90 …"); `test_annual_q_uncovered_age_raises` asserts "birth year B at age A" for all four cases (adds birth year 2075); README `--require-data-files` line updated.

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
