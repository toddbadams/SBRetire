"""Config Hash, data-file hashes and Run Metadata (SPEC §10.3; configuration §7)."""

from __future__ import annotations

from pathlib import Path

from sbretire.config import Scenario


def config_sha256(scenario: Scenario) -> str:
    raise NotImplementedError


def file_sha256(path: Path) -> str:
    raise NotImplementedError
