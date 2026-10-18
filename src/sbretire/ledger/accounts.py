"""Accounts config: which export files belong to which account, owner and wrapper (F-024).

``config/accounts.yaml`` is personal and git-ignored; ``config/accounts.example.yaml`` shows the layout.
Errors are reported like scenario errors: every problem, each with its YAML location (portfolio-data §1).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from sbretire._yaml import YamlLoadError, load_yaml
from sbretire.config import ScenarioError, ScenarioIssue, _format_location, _issue, _text

Provider = Literal["schwab", "hl", "vanguard", "ii"]
Wrapper = Literal["taxable", "isa", "pension", "sipp"]
Text = Annotated[str, BeforeValidator(_text), Field(min_length=1)]
Patterns = Annotated[tuple[Text, ...], Field(min_length=1)]


class AccountConfig(BaseModel):
    """One account: its export file patterns (matched inside each month folder) and who owns it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Text
    name: Text
    provider: Provider
    owner: Text
    """A person id from the model config."""
    wrapper: Wrapper
    currency: Annotated[str, BeforeValidator(_text), Field(pattern=r"^[A-Z]{3}$")]
    transactions: Patterns
    holdings: Patterns
    filter: Text | None = None
    """Keep only transaction rows whose Account column equals this (for shared provider files)."""


class _AccountsFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accounts: Annotated[tuple[AccountConfig, ...], Field(min_length=1)]


def load_accounts(path: Path) -> list[AccountConfig]:
    """Read and validate an accounts file; ``ScenarioError`` lists every problem with its location."""
    try:
        raw = load_yaml(path.read_text(encoding="utf-8"))
    except YamlLoadError as exc:
        raise ScenarioError(
            [ScenarioIssue(_format_location(loc), msg) for loc, msg in exc.problems]
        ) from None
    if not isinstance(raw, Mapping):
        raise ScenarioError(
            [ScenarioIssue("(accounts)", "top level must be a mapping with an accounts list")]
        )
    try:
        parsed = _AccountsFile.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError([_issue(error) for error in exc.errors()]) from None
    seen: dict[str, int] = {}
    issues = []
    for index, account in enumerate(parsed.accounts):
        if account.id in seen:
            issues.append(
                ScenarioIssue(
                    f"accounts[{index}].id",
                    f"duplicate id {account.id!r} (also accounts[{seen[account.id]}])",
                )
            )
        seen.setdefault(account.id, index)
    if issues:
        raise ScenarioError(issues)
    return list(parsed.accounts)
