"""Config Hash, data-file hashes and Run Metadata (SPEC §10.3; configuration §7)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sbretire.config import LoadedScenario, Scenario
from sbretire.randomness import ResolvedSeed, SeedSource

_CHUNK = 1 << 20


def config_sha256(scenario: Scenario) -> str:
    """SHA-256 (lowercase hex) of the validated Scenario as canonical JSON, without ``mortality.data_file``.

    Comments, key order and YAML formatting never reach the validated Scenario, so cannot change the hash;
    the data-file path is machine-specific and its content is hashed separately (configuration §7).
    """
    payload = scenario.model_dump(mode="json", exclude={"mortality": {"data_file"}})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def file_sha256(path: Path) -> str:
    """SHA-256 (lowercase hex) of a file's bytes; ``FileNotFoundError`` naming the path if it is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"data file not found: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class DataFileRecord:
    role: str
    path: str
    sha256: str
    version: str | None = None
    retrieved: str | None = None


@dataclass(frozen=True)
class RunMetadata:
    metadata_schema: int
    software_version: str
    created_at: str
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


def build_run_metadata(
    loaded: LoadedScenario,
    seed: ResolvedSeed,
    data_files: Sequence[DataFileRecord] = (),
    *,
    now: datetime | None = None,
) -> RunMetadata:
    raise NotImplementedError


def write_run_metadata(metadata: RunMetadata, output_dir: Path) -> Path:
    raise NotImplementedError
