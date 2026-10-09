from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "scenarios"


@pytest.fixture
def valid_raw() -> dict[str, Any]:
    loaded = yaml.safe_load((FIXTURES / "valid_minimal.yaml").read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture
def fixture_dir() -> Path:
    return FIXTURES
