"""F-021.2 — named runs: ``--name``/``--overwrite``, run folders, index.json, runs.js (F-021 brief §2 #3–#7).

Fixture tests/fixtures/scenarios/valid_minimal.yaml cut to 200 paths and one target so each run is quick.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire.__main__ import main
from sbretire.results_json import check_run_name

from scenario_helpers import set_at

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"
RUN_FILES = {
    "inputs.csv",
    "annual_results.csv",
    "sustainability_results.csv",
    "lifestyle_results.csv",
    "run_metadata.json",
    "results_guide.md",
    "results.json",
}


def _config(tmp_path: Path, **changes: Any) -> Path:
    raw: dict[str, Any] = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    raw = set_at(raw, "mortality.data_file", str(ROOT / "data" / "ons_mortality.csv"))
    raw = set_at(raw, "inflation.data_file", str(ROOT / "data" / "uk_cpi.csv"))
    raw = set_at(set_at(raw, "model.simulation_count", 200), "model.confidence_levels", [0.9])
    for key, value in changes.items():
        raw = set_at(raw, key.replace("__", "."), value)
    path = tmp_path / f"scenario_{len(changes)}.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _run(config: Path, out: Path, *extra: str) -> int:
    return main(["run", "--config", str(config), "--output-dir", str(out), *extra])


def test_run_name_rule(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for good in ("base-4pct", "A_1", "x", "a" * 64):
        assert check_run_name(good) is None, good
    for bad in ("", "-x", "_x", "a b", "../x", "a/b", "a\\b", "a.b", "a" * 65, "näme"):
        assert check_run_name(bad), bad
    assert _run(_config(tmp_path), tmp_path / "out", "--name", "a b") == 2
    err = capsys.readouterr().err
    assert "a b" in err and "letters, digits" in err
    assert not (tmp_path / "out" / "runs").exists()


def test_cli_named_run_writes_run_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out"
    assert _run(_config(tmp_path), out, "--name", "base") == 0
    run_dir = out / "runs" / "base"
    assert {path.name for path in run_dir.iterdir()} == RUN_FILES
    assert {path.name for path in out.iterdir()} == {"runs", *VIEWER_FILES}
    assert {path.name for path in (out / "runs").iterdir()} == {"base", "index.json", "runs.js"}
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert results["run"]["name"] == "base"
    printed = capsys.readouterr().out
    assert f"Wrote {run_dir / 'results.json'}" in printed and f"Wrote {out / 'runs' / 'runs.js'}" in printed


def test_cli_named_run_refuses_existing_unless_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    assert _run(_config(tmp_path, budget__end_reserve_months=12), out, "--name", "base") == 0
    run_dir = out / "runs" / "base"
    assert (run_dir / "lifestyle_reserve_results.csv").is_file()
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}
    capsys.readouterr()

    assert _run(_config(tmp_path), out, "--name", "base") == 2
    captured = capsys.readouterr()
    assert "already exists" in captured.err and "--overwrite" in captured.err
    # refused before computing anything
    assert "SBRetire Monte Carlo" not in captured.out and "Inputs (" not in captured.out
    assert {path.name: path.read_bytes() for path in run_dir.iterdir()} == before

    assert _run(_config(tmp_path), out, "--name", "base", "--overwrite") == 0
    assert {path.name for path in run_dir.iterdir()} == RUN_FILES  # stale reserve CSV removed
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert results["run"]["options"]["end_reserve_months"] == 0


def _runs_js_payload(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    prefix, suffix = "window.SBRETIRE_RUNS = ", ";\n"
    assert text.startswith(prefix) and text.endswith(suffix)
    return json.loads(text[len(prefix) : -len(suffix)])


def test_runs_index_and_runs_js(tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert _run(_config(tmp_path), out, "--name", "alpha") == 0
    assert _run(_config(tmp_path, portfolio__annual_return=0.03), out, "--name", "beta") == 0
    runs_dir = out / "runs"
    index = json.loads((runs_dir / "index.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == "1.0"
    entries = index["runs"]
    assert {entry["name"] for entry in entries} == {"alpha", "beta"}
    by_name = sorted(entries, key=lambda e: e["name"])
    assert entries == sorted(by_name, key=lambda e: e["created_at"], reverse=True)  # newest first, then name
    results = {
        name: json.loads((runs_dir / name / "results.json").read_text(encoding="utf-8"))
        for name in ("alpha", "beta")
    }
    for entry in entries:
        run = results[entry["name"]]
        assert entry == {
            "name": entry["name"],
            "created_at": run["run"]["created_at"],
            "config_file": run["run"]["config_file"],
            "paths": 200,
            "monthly_budget_today": run["run"]["monthly_budget_today"],
            "annual_return": run["run"]["annual_return"],
            "conservative_success_rate": run["summary"]["conservative_success_rate"],
            "conservative_standard_error": run["summary"]["conservative_standard_error"],
            "first_target_probability": run["budgets"][0]["target_probability"],
            "first_target_maximum_monthly_budget_today": run["budgets"][0]["maximum_monthly_budget_today"],
        }
    expected = {"schema_version": "1.0", "index": entries, "runs": results}
    assert _runs_js_payload(runs_dir / "runs.js") == expected

    shutil.rmtree(runs_dir / "alpha")
    assert _run(_config(tmp_path), out, "--name", "gamma") == 0
    index = json.loads((runs_dir / "index.json").read_text(encoding="utf-8"))
    assert {entry["name"] for entry in index["runs"]} == {"beta", "gamma"}
    assert set(_runs_js_payload(runs_dir / "runs.js")["runs"]) == {"beta", "gamma"}


def test_run_name_rejects_windows_reserved_names() -> None:
    for reserved in ("CON", "nul", "Com1", "lpt9", "PRN", "aux"):
        problem = check_run_name(reserved)
        assert problem and "reserved" in problem, reserved
    for fine in ("console", "com10", "nul-run", "auxiliary"):
        assert check_run_name(fine) is None, fine


def test_cli_overwrite_keeps_old_run_when_computation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "out"
    assert _run(_config(tmp_path), out, "--name", "base") == 0
    run_dir = out / "runs" / "base"
    before = {path.name: path.read_bytes() for path in run_dir.iterdir()}

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated failure during the computation")

    monkeypatch.setattr("sbretire.__main__.draw_random_inputs", broken)
    with pytest.raises(RuntimeError):
        _run(_config(tmp_path), out, "--name", "base", "--overwrite")
    assert {path.name: path.read_bytes() for path in run_dir.iterdir()} == before


VIEWER_FILES = ("index.html", "theme.css", "viewer.css", "viewer.js")


def test_cli_named_run_copies_viewer(tmp_path: Path) -> None:
    web = ROOT / "src" / "sbretire" / "web"
    sources = {
        "index.html": web / "viewer" / "index.html",
        "theme.css": web / "theme.css",
        "viewer.css": web / "viewer" / "viewer.css",
        "viewer.js": web / "viewer" / "viewer.js",
    }
    out = tmp_path / "out"
    assert _run(_config(tmp_path), out, "--name", "base") == 0
    for name in VIEWER_FILES:
        assert (out / name).read_bytes() == sources[name].read_bytes(), name
    unnamed = tmp_path / "plain"
    assert _run(_config(tmp_path), unnamed) == 0
    assert not any((unnamed / name).exists() for name in VIEWER_FILES)
