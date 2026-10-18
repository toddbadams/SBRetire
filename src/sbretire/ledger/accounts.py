"""Accounts config (config/accounts.yaml) for the ledger import (F-024)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class AccountConfig(BaseModel):
    id: str


def load_accounts(path: Path) -> list[AccountConfig]:
    return []
