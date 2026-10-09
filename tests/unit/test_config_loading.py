"""F-001.3 — loading scenario files: duplicates, unknown keys, relative paths (configuration §1–§2)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire.config import Scenario, ScenarioError, load_scenario

from scenario_helpers import set_at

REPO = Path(__file__).resolve().parents[2]


def write_scenario(path: Path, raw: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_load_example_config_returns_typed_scenario() -> None:
    loaded = load_scenario(REPO / "config" / "model.example.yaml")

    scenario = loaded.scenario
    assert isinstance(scenario, Scenario)
    assert loaded.source_path == (REPO / "config" / "model.example.yaml").resolve()
    assert loaded.warnings == ()
    assert scenario.model.as_of_date == date(2026, 10, 1)
    assert scenario.model.unknown_keys == "error"
    assert scenario.model.confidence_levels == (0.90, 0.95, 0.99)
    assert scenario.portfolio.annual_return == 0.05
    assert [p.id for p in scenario.people] == ["person_1", "person_2"]
    assert [s.id for s in scenario.income] == ["social_security", "state_pension", "nhs_pension"]
    assert scenario.income[2].survivor_percentage == 0.5
    assert scenario.mortality.data_file == (REPO / "data" / "ons_mortality.csv").resolve()


def test_unknown_keys_error_by_default(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "extras", {"note": 1})
    raw = set_at(raw, "income[0].frequency", "monthly")
    with pytest.raises(ScenarioError) as exc:
        load_scenario(write_scenario(tmp_path / "s.yaml", raw))
    assert [(i.location, i.message) for i in exc.value.issues] == [
        ("extras", "unknown key"),
        ("income[0].frequency", "unknown key"),
    ]


def test_unknown_keys_warn_mode_returns_warnings(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "model.unknown_keys", "warn")
    raw = set_at(raw, "extras", {"note": 1})
    raw = set_at(raw, "income[0].frequency", "monthly")

    loaded = load_scenario(write_scenario(tmp_path / "s.yaml", raw))

    assert [i.location for i in loaded.warnings] == ["extras", "income[0].frequency"]
    assert all("ignored" in i.message for i in loaded.warnings)
    assert loaded.scenario.income[0].id == "pension_a"


def test_unknown_keys_warn_mode_still_reports_real_errors(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    raw = set_at(valid_raw, "model.unknown_keys", "warn")
    raw = set_at(raw, "extras", 1)
    raw = set_at(raw, "portfolio.annual_return", -5)
    with pytest.raises(ScenarioError) as exc:
        load_scenario(write_scenario(tmp_path / "s.yaml", raw))
    assert [i.location for i in exc.value.issues] == ["portfolio.annual_return"]


def test_duplicate_yaml_keys_rejected(tmp_path: Path, fixture_dir: Path) -> None:
    text = (fixture_dir / "valid_minimal.yaml").read_text(encoding="utf-8")
    text = text.replace("  annual_return: 0.04\n", "  annual_return: 0.04\n  annual_return: 0.06\n")
    text = text.replace("    name: Sam\n", "    name: Sam\n    name: Samantha\n")
    path = tmp_path / "dupes.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ScenarioError) as exc:
        load_scenario(path)

    assert [i.location for i in exc.value.issues] == ["people[1].name", "portfolio.annual_return"]
    assert all("duplicate key" in i.message and "line" in i.message for i in exc.value.issues)


def test_malformed_yaml_reported_with_line(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("model:\n  currency: GBP\n  bad: [unclosed\n", encoding="utf-8")
    with pytest.raises(ScenarioError) as exc:
        load_scenario(path)
    assert "line" in str(exc.value)


def test_top_level_must_be_mapping(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ScenarioError, match="mapping"):
        load_scenario(path)


def test_data_file_resolved_relative_to_config(
    tmp_path: Path, valid_raw: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    config = write_scenario(
        tmp_path / "scenarios" / "s.yaml", set_at(valid_raw, "mortality.data_file", "../data/m.csv")
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    loaded = load_scenario(config)

    assert loaded.scenario.mortality.data_file == (tmp_path / "data" / "m.csv").resolve()


def test_absolute_data_file_kept(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    target = (tmp_path / "abs" / "m.csv").resolve()
    config = write_scenario(tmp_path / "s.yaml", set_at(valid_raw, "mortality.data_file", str(target)))
    assert load_scenario(config).scenario.mortality.data_file == target


def test_missing_data_file_only_when_required(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    config = write_scenario(tmp_path / "s.yaml", set_at(valid_raw, "mortality.data_file", "m.csv"))

    assert load_scenario(config).scenario.mortality.data_file.name == "m.csv"
    with pytest.raises(ScenarioError) as exc:
        load_scenario(config, require_data_files=True)
    assert [i.location for i in exc.value.issues] == ["mortality.data_file"]
    assert "not found" in exc.value.issues[0].message

    (tmp_path / "m.csv").write_text("age,q\n", encoding="utf-8")
    assert load_scenario(config, require_data_files=True).scenario.mortality.data_file.is_file()


def test_unreadable_file_raises_os_error(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        load_scenario(tmp_path / "missing.yaml")
