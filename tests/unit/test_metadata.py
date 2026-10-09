"""F-005.2 / F-005.3 — Config Hash, file hash and Run Metadata (F-005 brief §2 #4–#6, configuration §7)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

import sbretire
from sbretire.config import LoadedScenario, Scenario, load_scenario, parse_scenario
from sbretire.metadata import (
    DataFileRecord,
    RunMetadata,
    build_run_metadata,
    config_sha256,
    file_sha256,
    write_run_metadata,
)
from sbretire.randomness import ResolvedSeed, resolve_seed

from scenario_helpers import set_at

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "valid_minimal.yaml"
HEX64 = re.compile(r"[0-9a-f]{64}")


def _scenario(raw: dict[str, Any], base_dir: Path = Path(".")) -> Scenario:
    return parse_scenario(raw, base_dir=base_dir).scenario


def test_config_sha256_ignores_formatting(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    original = FIXTURE.read_text(encoding="utf-8")
    commented = tmp_path / "commented.yaml"
    commented.write_text(
        "# a new comment\n\n" + original.replace("\n", "   # trailing\n", 3), encoding="utf-8"
    )
    reordered = tmp_path / "reordered.yaml"
    reordered.write_text(yaml.safe_dump(valid_raw, sort_keys=True, indent=4), encoding="utf-8")
    flow = tmp_path / "flow.yaml"
    flow.write_text(yaml.safe_dump(valid_raw, default_flow_style=True), encoding="utf-8")

    baseline = config_sha256(_scenario(valid_raw, tmp_path))
    assert HEX64.fullmatch(baseline)
    for path in (commented, reordered, flow):
        assert config_sha256(load_scenario(path).scenario) == baseline, path.name


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("portfolio.starting_balance", 500001),
        ("model.random_seed", 8),
        ("income[0].annual_amount_today", 12001),
        ("people[0].date_of_birth", "1958-04-01"),
        ("budget.survivor_budget_factor", 0.71),
        ("model.random_seed", None),
    ],
)
def test_config_sha256_changes_with_values(valid_raw: dict[str, Any], path: str, value: object) -> None:
    assert config_sha256(_scenario(set_at(valid_raw, path, value))) != config_sha256(_scenario(valid_raw))


def test_config_sha256_ignores_data_file_location(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    first = tmp_path / "a" / "deep" / "model.yaml"
    second = tmp_path / "b" / "model.yaml"
    for path in (first, second):
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
    one = load_scenario(first).scenario
    two = load_scenario(second).scenario
    assert one.mortality.data_file != two.mortality.data_file
    assert config_sha256(one) == config_sha256(two)


def test_config_sha256_ignores_dropped_unknown_keys(valid_raw: dict[str, Any]) -> None:
    warn = set_at(valid_raw, "model.unknown_keys", "warn")
    with_extras = set_at(set_at(warn, "portfolio.colour", "blue"), "notes", "anything")
    loaded = parse_scenario(with_extras, base_dir=Path("."))
    assert loaded.warnings
    assert config_sha256(loaded.scenario) == config_sha256(_scenario(warn))


def test_file_sha256_known_answer_and_missing_file(tmp_path: Path) -> None:
    content = b"age,sex,year,qx\n65,male,2026,0.0123\n"
    path = tmp_path / "table.csv"
    path.write_bytes(content)
    digest = file_sha256(path)
    assert digest == hashlib.sha256(content).hexdigest()
    assert HEX64.fullmatch(digest)
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    assert file_sha256(empty) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    missing = tmp_path / "nope.csv"
    with pytest.raises(FileNotFoundError, match=r"nope.csv"):
        file_sha256(missing)


NOW = datetime(2026, 10, 9, 14, 3, 0, tzinfo=UTC)
MORTALITY = DataFileRecord("mortality", "data/ons_mortality.csv", "ab" * 32, "2024-based", "2026-10-09")


def _loaded() -> LoadedScenario:
    return load_scenario(FIXTURE)


def test_build_run_metadata_has_required_fields() -> None:
    loaded = _loaded()
    meta = build_run_metadata(loaded, ResolvedSeed(7, "config"), [MORTALITY], now=NOW)

    assert meta.metadata_schema == 1
    assert meta.software_version == sbretire.__version__
    assert meta.created_at == "2026-10-09T14:03:00Z"
    assert meta.config_path == str(FIXTURE)
    assert meta.config_sha256 == config_sha256(loaded.scenario)
    assert meta.seed == 7
    assert meta.seed_source == "config"
    assert meta.simulation_count == loaded.scenario.model.simulation_count
    assert meta.horizon_years == loaded.scenario.model.horizon_years
    assert meta.data_files == (MORTALITY,)
    assert meta.python_version == platform.python_version()
    assert meta.numpy_version == np.__version__
    assert meta.platform == platform.platform()


def test_build_run_metadata_requires_utc_now() -> None:
    with pytest.raises(ValueError, match="UTC"):
        build_run_metadata(_loaded(), ResolvedSeed(7, "config"), now=datetime(2026, 10, 9, 14, 3))


def test_write_run_metadata_round_trips(tmp_path: Path) -> None:
    seed = ResolvedSeed(2**128 - 3, "generated")
    meta = build_run_metadata(_loaded(), seed, [MORTALITY], now=NOW)

    written = write_run_metadata(meta, tmp_path / "out")
    assert written == tmp_path / "out" / "run_metadata.json"
    text = written.read_text(encoding="utf-8")
    assert text.endswith("\n")
    loaded = json.loads(text)
    assert list(loaded) == sorted(loaded)
    assert loaded["seed"] == 2**128 - 3
    assert loaded["data_files"] == [dataclasses.asdict(MORTALITY)]
    restored = RunMetadata(
        **{**loaded, "data_files": tuple(DataFileRecord(**record) for record in loaded["data_files"])}
    )
    assert restored == meta


def test_build_run_metadata_reproducible_except_created_at() -> None:
    first = build_run_metadata(_loaded(), ResolvedSeed(7, "config"), [MORTALITY], now=NOW)
    second = build_run_metadata(_loaded(), ResolvedSeed(7, "config"), [MORTALITY])
    assert first.created_at != second.created_at
    assert dataclasses.replace(second, created_at=first.created_at) == first


def test_build_run_metadata_records_seed_source() -> None:
    generated = resolve_seed(None)
    meta = build_run_metadata(_loaded(), generated, now=NOW)
    assert (meta.seed, meta.seed_source) == (generated.value, "generated")
    configured = build_run_metadata(_loaded(), resolve_seed(7), now=NOW)
    assert (configured.seed, configured.seed_source) == (7, "config")
    assert configured.data_files == ()
