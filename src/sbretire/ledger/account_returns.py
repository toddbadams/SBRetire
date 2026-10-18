"""Account returns from the ledger: what each account actually earned since the first export (F-031; §26–§28).

Month-end values are rebuilt backwards from today's holdings through the ledger and priced with the price
files; time-weighted returns chain Modified Dietz months, money-weighted returns solve the internal rate
of return.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from typing import Final

from sbretire.ledger.holdings import Holding
from sbretire.ledger.model import LedgerRow
from sbretire.ledger.prices import SecuritiesConfig
from sbretire.ledger.returns import add_months

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


def month_end(month: dt.date) -> dt.date:
    """The last day of ``month`` (given as its first day)."""
    return add_months(month, 1) - dt.timedelta(days=1)


def units_at(
    rows: Sequence[LedgerRow],
    matched: Mapping[tuple[str, str], str],
    today: Mapping[str, float],
    month: dt.date,
) -> dict[str, float]:
    """Series → units at the end of ``month``: today's units less every later ``quantity_change`` (§27)."""
    end = month_end(month)
    units = dict(today)
    for row in rows:
        series = matched.get((row.account, row.security_key))
        if series is not None and row.date > end and row.quantity_change:
            units[series] = units.get(series, 0.0) - row.quantity_change
    return units


def cash_at(rows: Sequence[LedgerRow], today: float, month: dt.date) -> float:
    """Cash at the end of ``month``: today's cash less every later ``cash_change`` (§27)."""
    end = month_end(month)
    return today - sum(row.cash_change for row in rows if row.date > end)


def price_in(account_currency: str, quote: str, close: float, usd_gbp: float) -> float:
    """A month-end price in the account's currency: GBX ÷ 100; USD × GBP-per-USD into GBP, and back (§27)."""
    pounds = close / 100.0 if quote == "GBX" else close
    major = "GBP" if quote == "GBX" else quote
    if major == account_currency:
        return pounds
    if major == "USD" and account_currency == "GBP":
        return pounds * usd_gbp
    if major == "GBP" and account_currency == "USD":
        return pounds / usd_gbp
    raise ValueError(f"no conversion from {quote} to {account_currency}")


def rebuild(
    rows: Sequence[LedgerRow],
    matched: Mapping[tuple[str, str], str],
    today_units: Mapping[str, float],
    today_cash: float,
    months: Sequence[dt.date],
    closes: Mapping[str, Mapping[dt.date, float]],
    quotes: Mapping[str, str],
    currency: str,
    usd_gbp: Mapping[dt.date, float],
) -> tuple[list[tuple[dt.date, float | None]], list[str]]:
    """Month-end values of one account in its own currency, and what stops any month being valued (§27).

    A ledger security with no matched series, or a held series without a price (or a needed USD rate) at a
    month-end, is listed; that month's value is ``None``.
    """
    missing: list[str] = []
    for row in rows:
        if row.security_key and (row.account, row.security_key) not in matched:
            label = f"{row.security_key} (no price series matched)"
            if label not in missing:
                missing.append(label)
    values: list[tuple[dt.date, float | None]] = []
    for month in months:
        total: float | None = cash_at(rows, today_cash, month)
        for series, units in units_at(rows, matched, today_units, month).items():
            if abs(units) < 1e-9:
                continue
            close = closes.get(series, {}).get(month)
            quote = quotes.get(series, currency)
            needs_rate = ("GBP" if quote == "GBX" else quote) != currency
            rate = usd_gbp.get(month)
            if close is None:
                missing.append(f"{series} ({month:%Y-%m})")
                total = None
            elif needs_rate and rate is None:
                missing.append(f"{series} ({month:%Y-%m}: no USD rate)")
                total = None
            elif total is not None:
                total += units * price_in(currency, quote, close, rate or 1.0)
        values.append((month, total))
    return values, missing


def modified_dietz(*a: object) -> object:
    raise NotImplementedError


def returns_for(*a: object) -> object:
    raise NotImplementedError


def to_gbp(*a: object) -> object:
    raise NotImplementedError


def xirr(*a: object) -> object:
    raise NotImplementedError
