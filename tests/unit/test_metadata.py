"""F-005.2 / F-005.3 — Config Hash, file hash and Run Metadata (F-005 brief §2 #4–#6, configuration §7)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire.config import Scenario, load_scenario, parse_scenario
from sbretire.metadata import config_sha256, file_sha256

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
