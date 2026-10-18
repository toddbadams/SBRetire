"""F-024.1 — accounts config (config/accounts.yaml) and monthly export folders."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire.config import ScenarioError
from sbretire.ledger.accounts import load_accounts
from sbretire.ledger.merge import month_folders

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "config" / "accounts.example.yaml"


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "accounts.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _example_raw() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    return loaded


def _locations(path: Path) -> list[str]:
    with pytest.raises(ScenarioError) as caught:
        load_accounts(path)
    return [issue.location for issue in caught.value.issues]


def test_load_accounts_validates(tmp_path: Path) -> None:
    accounts = load_accounts(EXAMPLE)
    assert [a.provider for a in accounts] == ["schwab", "hl", "vanguard", "vanguard", "ii"]
    assert {a.wrapper for a in accounts} == {"taxable", "sipp", "isa", "pension"}
    assert all(a.transactions and a.holdings for a in accounts)

    raw = _example_raw()
    raw["accounts"][1]["id"] = raw["accounts"][0]["id"]
    assert _locations(_write(tmp_path, raw)) == ["accounts[1].id"]

    raw = _example_raw()
    raw["accounts"][0]["provider"] = "fidelity"
    raw["accounts"][2]["wrapper"] = "lisa"
    assert _locations(_write(tmp_path, raw)) == ["accounts[0].provider", "accounts[2].wrapper"]

    raw = _example_raw()
    del raw["accounts"][3]["transactions"]
    raw["accounts"][4]["holdings"] = []
    assert _locations(_write(tmp_path, raw)) == ["accounts[3].transactions", "accounts[4].holdings"]

    raw = _example_raw()
    raw["accounts"][0]["colour"] = "blue"
    with pytest.raises(ScenarioError) as caught:
        load_accounts(_write(tmp_path, raw))
    assert [(i.location, i.message) for i in caught.value.issues] == [("accounts[0].colour", "unknown key")]


def test_month_folders_parse_and_sort(tmp_path: Path) -> None:
    for name in ("oct-26", "jan-27", "sep-26", "notes", "2026-10", "Oct-26x"):
        (tmp_path / name).mkdir()
    (tmp_path / "nov-26").write_text("a file, not a folder", encoding="utf-8")
    found = month_folders(tmp_path)
    assert [(month, folder.name) for month, folder in found] == [
        (date(2026, 9, 1), "sep-26"),
        (date(2026, 10, 1), "oct-26"),
        (date(2027, 1, 1), "jan-27"),
    ]


def test_accounts_example_is_synthetic() -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    owners = {account.owner for account in load_accounts(EXAMPLE)}
    assert owners == {"person_1", "person_2"}
    assert not re.search(r"\d{5,}", text), "no account or client numbers"
    assert "@" not in text
    assert "Example" in text  # names are visibly placeholders
