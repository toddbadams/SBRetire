"""Config Hash, data-file hashes and Run Metadata (SPEC §10.3; configuration §7)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import numpy as np

import sbretire
from sbretire.config import LoadedScenario, Scenario
from sbretire.randomness import ResolvedSeed, SeedSource

_CHUNK = 1 << 20
METADATA_SCHEMA = 1
"""Version of the ``run_metadata.json`` layout; bump when fields change meaning or are removed."""
RUN_METADATA_FILE = "run_metadata.json"


_OPTIONS_HASHED_ONLY_WHEN_SET: Final[tuple[tuple[str, str, object], ...]] = (
    ("budget", "end_reserve_months", 0),
)
"""Options added after V1, left out of the hash at their default so every V1 config keeps its hash."""


def config_sha256(scenario: Scenario) -> str:
    """SHA-256 (lowercase hex) of the validated Scenario as canonical JSON, without data-file paths.

    Comments, key order and YAML formatting never reach the validated Scenario, so cannot change the hash;
    the data-file path is machine-specific and its content is hashed separately (configuration §7).
    """
    excluded: dict[str, set[str]] = {"mortality": {"data_file"}, "inflation": {"data_file"}}
    for section, field, default in _OPTIONS_HASHED_ONLY_WHEN_SET:
        if getattr(getattr(scenario, section), field) == default:
            excluded.setdefault(section, set()).add(field)
    payload = scenario.model_dump(mode="json", exclude=excluded)
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
    """One input data file as recorded in Run Metadata; ``version``/``retrieved`` come from F-006/F-007."""

    role: str
    path: str
    sha256: str
    version: str | None = None
    retrieved: str | None = None


@dataclass(frozen=True)
class RunMetadata:
    """Everything needed to reproduce and audit a run (SPEC §10.3); written as ``run_metadata.json``.

    ``created_at`` is the only field expected to differ between two runs of the same inputs and seed.
    """

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
    """Assemble Run Metadata for a loaded Scenario and its resolved seed; ``now`` (UTC) defaults to now."""
    moment = datetime.now(UTC) if now is None else now
    if moment.utcoffset() != timedelta(0):
        raise ValueError(f"now must be a UTC datetime, got {moment!r}")
    model = loaded.scenario.model
    return RunMetadata(
        metadata_schema=METADATA_SCHEMA,
        software_version=sbretire.__version__,
        created_at=moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        config_path=None if loaded.source_path is None else str(loaded.source_path),
        config_sha256=config_sha256(loaded.scenario),
        seed=seed.value,
        seed_source=seed.source,
        simulation_count=model.simulation_count,
        horizon_years=model.horizon_years,
        data_files=tuple(data_files),
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        platform=platform.platform(),
    )


def write_run_metadata(metadata: RunMetadata, output_dir: Path) -> Path:
    """Write ``output_dir/run_metadata.json`` (UTF-8, sorted keys, 2-space indent); return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / RUN_METADATA_FILE
    text = json.dumps(dataclasses.asdict(metadata), indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path
