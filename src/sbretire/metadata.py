"""Config Hash, data-file hashes and Run Metadata (SPEC §10.3; configuration §7)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sbretire.config import Scenario

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
