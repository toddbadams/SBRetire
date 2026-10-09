"""YAML loading that refuses silently-overwritten duplicate keys.

PyYAML keeps the last of two identical keys without complaint, so a scenario with ``annual_return``
written twice would quietly use the second. :func:`load_yaml` composes the node tree first, reports every
duplicate with its location, then constructs the document with the safe loader.
"""

from __future__ import annotations

from typing import Any

import yaml

Location = tuple[str | int, ...]


class YamlLoadError(ValueError):
    """The text is not usable YAML; ``problems`` holds (location, message) pairs."""

    def __init__(self, problems: list[tuple[Location, str]]) -> None:
        super().__init__("; ".join(message for _, message in problems))
        self.problems = problems


def _duplicates(node: yaml.Node, location: Location, found: list[tuple[Location, str]]) -> None:
    if isinstance(node, yaml.MappingNode):
        first_line: dict[str, int] = {}
        for key_node, value_node in node.value:
            key = str(key_node.value)
            line = key_node.start_mark.line + 1
            if key in first_line:
                message = f"duplicate key on line {line} (first on line {first_line[key]})"
                found.append(((*location, key), message))
            else:
                first_line[key] = line
            _duplicates(value_node, (*location, key), found)
    elif isinstance(node, yaml.SequenceNode):
        for index, item in enumerate(node.value):
            _duplicates(item, (*location, index), found)


def load_yaml(text: str) -> Any:
    """Parse one YAML document safely; raise :class:`YamlLoadError` on syntax errors or duplicate keys."""
    loader = yaml.SafeLoader(text)
    try:
        node = loader.get_single_node()
        if node is None:
            return None
        found: list[tuple[Location, str]] = []
        _duplicates(node, (), found)
        if found:
            raise YamlLoadError(found)
        return loader.construct_document(node)
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark
        where = f"line {mark.line + 1}, column {mark.column + 1}: " if mark else ""
        raise YamlLoadError([((), f"invalid YAML — {where}{exc.problem}")]) from None
    finally:
        loader.dispose()
