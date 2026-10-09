"""F-015.3 — ``sbretire preview``: banner, table, summary and preview.csv (F-015 brief §2 #7–#9)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire.__main__ import main
from sbretire.config import load_scenario
from sbretire.preview import run_preview

from scenario_helpers import set_at

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios" / "valid_minimal.yaml"
HEADER = (
    "year,months,age_person_1,age_person_2,income,spending,investment_return,net_withdrawal,"
    "balance_end,balance_end_today,price_index"
)


def exit_code(argv: list[str]) -> int:
    try:
        return main(argv)
    except SystemExit as exc:  # argparse errors
        return int(exc.code or 0)


def test_cli_preview_prints_table_and_writes_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["preview", "--config", str(FIXTURE), "--death-ages", "90,90", "--output-dir", str(tmp_path)])

    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0].startswith("DETERMINISTIC ILLUSTRATION")
    assert "not a sustainability estimate" in out
    for column in ("year", "income", "spending", "balance_end", "balance_end_today"):
        assert column in out
    assert "2026" in out and "2027" in out
    assert "Money runs out" in out or "Money lasts" in out
    assert "Household end" in out and "Final balance" in out
    assert (tmp_path / "preview.csv").is_file()
    assert out.isascii()


def test_preview_csv_format(tmp_path: Path) -> None:
    assert (
        main(["preview", "--config", str(FIXTURE), "--death-ages", "90,90", "--output-dir", str(tmp_path)])
        == 0
    )
    raw = (tmp_path / "preview.csv").read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()

    assert lines[0] == HEADER
    expected_rows = run_preview(load_scenario(FIXTURE).scenario, (90, 90)).rows
    assert len(lines) - 1 == len(expected_rows)
    assert "£" not in text and "GBP" not in text
    for record in csv.DictReader(lines):
        assert len(record) == 11
        int(record["year"])
        int(record["months"])
        for name in ("income", "spending", "investment_return", "net_withdrawal", "balance_end"):
            assert "," not in record[name]
            float(record[name])
        assert record["age_person_1"] == "" or record["age_person_1"].isdigit()


@pytest.mark.parametrize(
    ("ages", "fragment"),
    [("90", "two"), ("90,abc", "whole"), ("90,90,90", "two"), ("60,90", "current age")],
)
def test_cli_preview_rejects_bad_arguments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], ages: str, fragment: str
) -> None:
    code = exit_code(
        ["preview", "--config", str(FIXTURE), "--death-ages", ages, "--output-dir", str(tmp_path)]
    )
    assert code == 2
    assert fragment in capsys.readouterr().err
    assert not (tmp_path / "preview.csv").exists()


def test_cli_preview_config_errors(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(set_at(valid_raw, "model.currency", "EUR")), encoding="utf-8")
    assert (
        exit_code(["preview", "--config", str(bad), "--death-ages", "90,90", "--output-dir", str(tmp_path)])
        == 2
    )
    missing = tmp_path / "nope.yaml"
    assert exit_code(["preview", "--config", str(missing), "--death-ages", "90,90"]) == 1
