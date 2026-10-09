"""F-001.4 — ``sbretire validate`` and ``sbretire run`` (brief §5 CLI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from scenario_helpers import set_at

from sbretire import __version__
from sbretire.__main__ import main

EXAMPLE = Path(__file__).resolve().parents[2] / "config" / "model.example.yaml"


def write(path: Path, raw: dict[str, Any]) -> str:
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return str(path)


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_cli_validate_example_config_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "--config", str(EXAMPLE)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("OK ")
    for fragment in ("2 people", "3 income streams", "as-of 2026-10-01", "100000 paths", "horizon 100 y"):
        assert fragment in out


def test_cli_validate_invalid_exits_two_lists_issues(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(valid_raw, "portfolio.annual_return", -3)
    raw = set_at(raw, "income[0].survivor_percentage", 4)
    assert main(["validate", "--config", write(tmp_path / "bad.yaml", raw)]) == 2
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    issue_lines = [line for line in err_lines if line.lstrip().startswith(("income[0]", "portfolio"))]
    assert len(issue_lines) == 2
    assert "income[0].survivor_percentage:" in issue_lines[0]
    assert "portfolio.annual_return:" in issue_lines[1]


def test_cli_validate_missing_file_exits_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.yaml"
    assert main(["validate", "--config", str(missing)]) == 1
    assert "nope.yaml" in capsys.readouterr().err


def test_cli_validate_prints_warnings(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(set_at(valid_raw, "model.unknown_keys", "warn"), "notes", "hello")
    assert main(["validate", "--config", write(tmp_path / "warn.yaml", raw)]) == 0
    captured = capsys.readouterr()
    assert "notes: unknown key (ignored)" in captured.out + captured.err


def test_cli_validate_require_data_files(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = write(tmp_path / "s.yaml", set_at(valid_raw, "mortality.data_file", "absent.csv"))
    assert main(["validate", "--config", config]) == 0
    assert main(["validate", "--config", config, "--require-data-files"]) == 2
    assert "mortality.data_file" in capsys.readouterr().err


def test_cli_run_validates_then_reports_engine_pending(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    bad = write(tmp_path / "bad.yaml", set_at(valid_raw, "model.currency", "EUR"))
    assert main(["run", "--config", bad, "--output-dir", str(tmp_path / "out")]) == 2
    assert main(["run", "--config", str(EXAMPLE), "--output-dir", str(tmp_path / "out")]) == 1
    assert "not implemented" in capsys.readouterr().err
