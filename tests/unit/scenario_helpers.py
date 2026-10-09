"""Helpers for editing raw scenario mappings in tests."""

from __future__ import annotations

import copy
from typing import Any


def _parse_path(path: str) -> list[str | int]:
    """'income[0].recipient' -> ['income', 0, 'recipient']."""
    parts: list[str | int] = []
    for chunk in path.split("."):
        name, _, rest = chunk.partition("[")
        if name:
            parts.append(name)
        while rest:
            index, _, rest = rest.partition("]")
            parts.append(int(index))
            rest = rest.removeprefix("[")
    return parts


def set_at(raw: dict[str, Any], path: str, value: object) -> dict[str, Any]:
    """Return a deep copy of ``raw`` with ``path`` set to ``value``."""
    out = copy.deepcopy(raw)
    *parents, last = _parse_path(path)
    node: Any = out
    for part in parents:
        node = node[part]
    node[last] = value
    return out


def delete_at(raw: dict[str, Any], path: str) -> dict[str, Any]:
    """Return a deep copy of ``raw`` with the key at ``path`` removed."""
    out = copy.deepcopy(raw)
    *parents, last = _parse_path(path)
    node: Any = out
    for part in parents:
        node = node[part]
    del node[last]
    return out
