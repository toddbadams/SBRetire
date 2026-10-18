"""Account returns from the ledger: what each account actually earned since the first export (F-031; §26–§28).

Month-end values are rebuilt backwards from today's holdings through the ledger and priced with the price
files; time-weighted returns chain Modified Dietz months, money-weighted returns solve the internal rate
of return.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

from sbretire.ledger.holdings import Holding
from sbretire.ledger.model import LedgerRow
from sbretire.ledger.prices import SecuritiesConfig

_TAIL: Final = {
    "acc", "accumulation", "accumulating", "inc", "income", "dist", "distributing", "shares", "share",
    "class",
    "gbp", "usd", "fund",
}  # fmt: skip


def normalise_name(name: str) -> str:
    """Lower case, punctuation removed, trailing share-class words and single letters dropped (§26)."""
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    while tokens and (tokens[-1] in _TAIL or len(tokens[-1]) == 1):
        tokens.pop()
    return " ".join(tokens)


def match_securities(
    rows: Sequence[LedgerRow], holdings: Sequence[Holding], securities: SecuritiesConfig
) -> tuple[dict[tuple[str, str], str], list[tuple[str, str]]]:
    """(account, ledger security key) → series id for every security in ``rows``, and those left unmatched.

    Order (§26): a series' ``ledger_names`` (in the accounts its holdings name); the account's holding with
    the same key; the account's holding with the same normalised name. A matched holding takes the series that
    prices it.
    """
    series_of_ref = {ref: s.id for s in securities.securities for ref in s.holdings}
    overrides: dict[tuple[str, str], str] = {}
    for series in securities.securities:
        for account in {ref.split(":", 1)[0] for ref in series.holdings}:
            for name in series.ledger_names:
                overrides[(account, name)] = series.id
    by_key: dict[tuple[str, str], str] = {}
    by_name: dict[tuple[str, str], str] = {}
    for holding in holdings:
        if holding.kind != "security":
            continue
        ref = f"{holding.account}:{holding.security_key}"
        if ref in series_of_ref:
            by_key[(holding.account, holding.security_key)] = series_of_ref[ref]
            by_name.setdefault((holding.account, normalise_name(holding.security_name)), series_of_ref[ref])
            by_name.setdefault((holding.account, normalise_name(holding.security_key)), series_of_ref[ref])
    matched: dict[tuple[str, str], str] = {}
    unmatched: list[tuple[str, str]] = []
    for row in rows:
        key = (row.account, row.security_key)
        if not row.security_key or key in matched or key in unmatched:
            continue
        found = (
            overrides.get(key)
            or overrides.get((row.account, row.security_name))
            or by_key.get(key)
            or by_name.get((row.account, normalise_name(row.security_key)))
            or by_name.get((row.account, normalise_name(row.security_name)))
        )
        if found is None:
            unmatched.append(key)
        else:
            matched[key] = found
    return matched, unmatched
