---
id: F-005
type: feature
parent: foundations
status: planned
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-005 Random Streams and Run Metadata

## 1. Purpose

Give the Monte Carlo engine its randomness and its receipt. One `SeedSequence`, seeded from `model.random_seed`,
spawns an independent **Random Stream** for mortality and one for inflation (SPEC §10.3) so changes to one component
never perturb the other's draws. When `random_seed: null` a seed is generated and recorded (SPEC §4.2). A
**Run Metadata** record — seed, software version, **Config Hash**, data-file hashes, environment — is built and
written as `run_metadata.json` so a run can be reproduced and audited (SPEC §10.3, §17.3 #3).

Makes passable SPEC §17.1 "A fixed seed reproduces outputs" at the stream level; the end-to-end reproducibility
check lands with F-009 (first stochastic run) and F-014. Common Random Numbers are *enabled* here (draws come from
streams created once per run) and *exercised* by F-010/F-011.

Out of scope: wiring metadata into `sbretire run` (F-013); filling dataset version / retrieval date for the
mortality and CPI files (F-007 / F-006 supply their `DataFileRecord`s); any draw consumers (F-006, F-008).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Generator | `numpy.random.Generator(PCG64)` per stream, from one `SeedSequence(seed)` | NumPy's recommended parallel-stream pattern; CLAUDE.md constraint 4 | SPEC §10.3; CLAUDE.md |
| 2 | Stream derivation | Fixed child indices: mortality = `SeedSequence(seed).spawn` child 0, inflation = child 1 (built as `SeedSequence(seed, spawn_key=(k,))`); a future stream takes the next index | Adding a stream never changes existing draws; order is pinned by a known-answer test | simulation-conventions §4 |
| 3 | Null seed | `SeedSequence().entropy` — 128-bit OS entropy — recorded in metadata with `seed_source: "generated"`; feeding it back as `random_seed` reproduces the run | NumPy practice; collision-free; YAML/pydantic accept arbitrary-size ints | Interview Q2; configuration §8 |
| 4 | Config Hash | SHA-256 of the validated `Scenario` as canonical JSON (sorted keys, no whitespace, `model_dump(mode="json")`), **excluding** `mortality.data_file` | Stable across comments, key order, formatting and machines; any value change alters it; the data file's *content* is hashed separately | Interview Q1; configuration §7 |
| 5 | Metadata contents | SPEC §10.3 fields + Python / NumPy / platform versions, UTC `created_at`, config path, `seed_source`, `simulation_count`, `horizon_years`, `metadata_schema: 1` | §17.3 limits reproducibility to "the supported environment" — versions explain a mismatch; `created_at` is the only field expected to differ between identical runs | Interview Q3 |
| 6 | Software version | `sbretire.__version__` (no git shell-out) | No subprocess / VCS dependency; wheel installs work | Interview Q3 |
| 7 | CRN | Streams are created once per run; every candidate budget/return reuses the draws materialised from them; candidates never re-seed | SPEC §10.3 | simulation-conventions §4 |
| 8 | Placement | `sbretire/randomness.py` (seed + streams), `sbretire/metadata.py` (hashes + RunMetadata + JSON) | SPEC §3 module responsibilities; keeps the engine free of I/O | Brief author |

## 3. Context

- `ModelSettings.random_seed: Integer ≥ 0 | None` (F-001); `Integer` rejects bools/strings. A 128-bit int must
  validate — covered by a test, not assumed.
- `LoadedScenario(scenario, source_path, warnings)`; `mortality.data_file` is resolved to an absolute path at load
  (configuration §2) — which is why it is excluded from the Config Hash.
- Warn mode drops unknown keys before validation, so they never reach the hash.
- No stochastic consumer exists yet; the engine (`simulate_paths`) takes `death_month` and a `PriceIndex` — F-006/F-008
  will build those from the streams.
- Constraint: never call `np.random.<function>` globals in `src/`.

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/randomness.py` | `SeedSource`, `ResolvedSeed`, `resolve_seed`, `RandomStreams` |
| `src/sbretire/metadata.py` | `config_sha256`, `file_sha256`, `DataFileRecord`, `RunMetadata`, `build_run_metadata`, `write_run_metadata` |
| `tests/unit/test_randomness.py` | F-005.1 |
| `tests/unit/test_metadata.py` | F-005.2, F-005.3 |

**Modified**

| File | Change |
|---|---|
| `tests/unit/test_config_fields.py` | 128-bit `random_seed` accepted |
| `README.md` | Reproducibility / `run_metadata.json` section |
| `docs/THESAURUS.md` | Run Metadata, Config Hash (added with this brief) |

## 5. Interfaces

```python
# sbretire/randomness.py
SeedSource = Literal["config", "generated"]
MORTALITY_STREAM: Final = 0
INFLATION_STREAM: Final = 1

@dataclass(frozen=True)
class ResolvedSeed:
    value: int            # >= 0; up to 128 bits when generated
    source: SeedSource

def resolve_seed(configured: int | None) -> ResolvedSeed: ...

@dataclass(frozen=True)
class RandomStreams:
    seed: ResolvedSeed
    mortality: np.random.Generator
    inflation: np.random.Generator

    @classmethod
    def from_seed(cls, seed: ResolvedSeed) -> RandomStreams: ...
```

Each call to `RandomStreams.from_seed` returns fresh generators at their initial state.

```python
# sbretire/metadata.py
def config_sha256(scenario: Scenario) -> str: ...      # 64 lowercase hex chars
def file_sha256(path: Path) -> str: ...                # FileNotFoundError naming the path if missing

@dataclass(frozen=True)
class DataFileRecord:
    role: str                    # "mortality" | "inflation"
    path: str
    sha256: str
    version: str | None = None   # publication/version — filled by F-006/F-007
    retrieved: str | None = None # ISO date — filled by F-006/F-007

@dataclass(frozen=True)
class RunMetadata:
    metadata_schema: int         # 1
    software_version: str
    created_at: str              # ISO 8601 UTC, e.g. 2026-10-09T14:03:00Z
    config_path: str | None
    config_sha256: str
    seed: int
    seed_source: SeedSource
    simulation_count: int
    horizon_years: int
    data_files: tuple[DataFileRecord, ...]
    python_version: str
    numpy_version: str
    platform: str

def build_run_metadata(loaded: LoadedScenario, seed: ResolvedSeed,
                       data_files: Sequence[DataFileRecord] = (), *,
                       now: datetime | None = None) -> RunMetadata: ...
def write_run_metadata(metadata: RunMetadata, output_dir: Path) -> Path:  # writes output_dir/run_metadata.json
```

`run_metadata.json`: UTF-8, `indent=2`, `sort_keys=True`, trailing newline; `seed` is a JSON integer (Python reads it
exactly; note in README that JavaScript would lose precision on a generated seed).

## 6. Plan of Work

1. `randomness.py`: `resolve_seed`, `RandomStreams.from_seed` with fixed child indices; config accepts a 128-bit seed.
2. `metadata.py` hashes: canonical Config Hash excluding `mortality.data_file`; streaming `file_sha256`.
3. `RunMetadata`, `build_run_metadata` (injectable `now`), `write_run_metadata`; README section.

## 7. Validation

- **T1**: unit tests per task; `ruff`, `mypy --strict`.
- **T2**: seeded reproducibility at stream level (pinned seed 42 known answer); end-to-end seeded run deferred to F-009.
- **T3**: regression snapshot — first draws of each stream for seed 42 pinned, so a reordering of child indices or a
  NumPy bit-generator change is caught.

## 8. Decision Log

- 2026-10-09 — Config Hash over the canonical validated Scenario, excluding the data-file path (configuration §7).
- 2026-10-09 — Null seed → 128-bit `SeedSequence().entropy`, recorded with `seed_source` (configuration §8).
- 2026-10-09 — Metadata adds environment versions and `created_at`; no git commit (Interview Q3).
- 2026-10-09 — Random Streams by fixed spawn index; CRN = streams created once per run (simulation-conventions §4).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-005.1 Random Streams and seed resolution
- **Status**: To Do
- **Depends on**: —

Build `src/sbretire/randomness.py` per §5: `resolve_seed` and `RandomStreams.from_seed` with mortality = child 0,
inflation = child 1 (§2 #1–#3). Tests in `tests/unit/test_randomness.py`; the 128-bit config case in
`tests/unit/test_config_fields.py`.

**Acceptance criteria**
- [ ] The same seed gives identical draws from both streams on two separate `from_seed` calls — `test_random_streams_fixed_seed_reproduces_draws`
- [ ] Consuming any number of inflation draws leaves the mortality draws unchanged (and vice versa) — `test_random_streams_consumption_is_independent`
- [ ] The mortality and inflation streams of one seed produce different draws; different seeds differ — `test_random_streams_streams_and_seeds_differ`
- [ ] `resolve_seed(None)` returns a generated seed in [0, 2^128) with source `generated`; `resolve_seed(7)` returns 7 with source `config`; feeding a generated seed back reproduces the draws — `test_resolve_seed_null_generates_reproducible_seed`
- [ ] A scenario with a 128-bit `random_seed` validates and keeps the exact value — `test_config_accepts_128_bit_random_seed`
- [ ] Seed 42's first draws from each stream equal pinned known answers — `test_random_streams_seed_42_known_answer`
- [ ] No `np.random.<function>` global calls in `src/` — `check: grep -rnE "np\.random\.(rand|randn|random|seed|normal|uniform|choice|randint)\(" src/ returns nothing`

### F-005.2 Config Hash and file hash
- **Status**: To Do
- **Depends on**: —

Add `config_sha256` and `file_sha256` to `src/sbretire/metadata.py` per §2 #4 and §5. Tests in
`tests/unit/test_metadata.py`.

**Acceptance criteria**
- [ ] Reordered keys, added comments and reformatted YAML give the same Config Hash — `test_config_sha256_ignores_formatting`
- [ ] Changing any one value (balance, a seed, an income amount, a person's date of birth) changes the hash — `test_config_sha256_changes_with_values`
- [ ] The same config loaded from two directories (different absolute `data_file`) hashes identically — `test_config_sha256_ignores_data_file_location`
- [ ] Unknown keys dropped in warn mode do not change the hash — `test_config_sha256_ignores_dropped_unknown_keys`
- [ ] `file_sha256` equals `hashlib.sha256` of known bytes and is 64 lowercase hex chars; a missing file raises `FileNotFoundError` naming the path — `test_file_sha256_known_answer_and_missing_file`

### F-005.3 RunMetadata and run_metadata.json
- **Status**: To Do
- **Depends on**: F-005.1, F-005.2

Add `DataFileRecord`, `RunMetadata`, `build_run_metadata`, `write_run_metadata` per §5; README section on
reproducibility and `run_metadata.json`.

**Acceptance criteria**
- [ ] Built metadata carries every SPEC §10.3 field (seed, software version = `sbretire.__version__`, config hash, data-file records) plus Python/NumPy/platform versions, `created_at` (UTC, from injected `now`), `simulation_count`, `horizon_years`, `metadata_schema` 1 — `test_build_run_metadata_has_required_fields`
- [ ] `run_metadata.json` is written to the output dir, sorted keys, and round-trips (JSON → values equal to the dataclass, seed exact for a 128-bit value) — `test_write_run_metadata_round_trips`
- [ ] Two builds from the same scenario and seed are equal except `created_at` — `test_build_run_metadata_reproducible_except_created_at`
- [ ] A generated seed is recorded with `seed_source: "generated"`, a configured one with `"config"` — `test_build_run_metadata_records_seed_source`
- [ ] README documents `run_metadata.json`, the Config Hash rule and how to reuse a generated seed — `check: grep -n "run_metadata.json" README.md`

## 11. Open Questions

- None blocking. F-006/F-007 decide how dataset `version` / `retrieved` are sourced (data/README vs a sidecar).

## 12. Acceptance Criteria

1. Fixed seed reproduces both streams — `test_random_streams_fixed_seed_reproduces_draws`
2. Streams are independent under consumption — `test_random_streams_consumption_is_independent`
3. Streams and seeds differ — `test_random_streams_streams_and_seeds_differ`
4. Null seed generated, recorded, reproducible — `test_resolve_seed_null_generates_reproducible_seed`
5. 128-bit seed validates — `test_config_accepts_128_bit_random_seed`
6. Seed 42 known answer — `test_random_streams_seed_42_known_answer`
7. No global NumPy randomness — `check: grep np.random globals in src/ is empty`
8. Config Hash ignores formatting — `test_config_sha256_ignores_formatting`
9. Config Hash tracks values — `test_config_sha256_changes_with_values`
10. Config Hash ignores data-file location — `test_config_sha256_ignores_data_file_location`
11. Config Hash ignores dropped unknown keys — `test_config_sha256_ignores_dropped_unknown_keys`
12. File hash known answer + missing file — `test_file_sha256_known_answer_and_missing_file`
13. Metadata fields complete — `test_build_run_metadata_has_required_fields`
14. JSON written and round-trips — `test_write_run_metadata_round_trips`
15. Reproducible except `created_at` — `test_build_run_metadata_reproducible_except_created_at`
16. Seed source recorded — `test_build_run_metadata_records_seed_source`
17. README documents metadata — `check: grep -n "run_metadata.json" README.md`
