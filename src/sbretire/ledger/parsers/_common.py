"""Helpers shared by the provider parsers: decoding, money, dates (F-024)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from pathlib import Path

_EMPTY = {"", "n/a", "--", "N/A"}


def read_text(path: Path) -> str:
    """The file's text: UTF-8 (any number of leading byte-order marks removed), else Windows-1252."""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    return text.lstrip("﻿")


def csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def money(text: str) -> float | None:
    """'-$1,234.56', '£1,234.56', '1234.56' or '(12.00)' → float; empty, 'n/a' or '--' → None."""
    value = text.strip()
    if value in _EMPTY:
        return None
    negative = value.startswith("-") or (value.startswith("(") and value.endswith(")"))
    cleaned = value.strip("()-+").replace("$", "").replace("£", "").replace(",", "").strip()
    number = float(cleaned)
    return -number if negative else number


def day(text: str, fmt: str) -> date:
    return datetime.strptime(text.strip(), fmt).date()
