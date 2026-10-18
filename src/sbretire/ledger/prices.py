"""Price series: the securities map and the household's price files (F-026)."""

from __future__ import annotations

from pathlib import Path


def load_securities(path: Path) -> object:
    raise NotImplementedError


def read_price_file(path: Path) -> object:
    raise NotImplementedError
