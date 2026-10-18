"""Valuing the newest month folder's holdings in GBP: the household's ``starting_balance`` (F-025).

Every account is valued at its own export's date; ii, which states none, takes the newest date the other
exports state (portfolio-data §8). USD is converted at the rate given with ``--usd-gbp`` (GBP per USD, §9).
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import fnmatch
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import HOLDING_COLUMNS, Holding, HoldingsError, HoldingsExport
from sbretire.ledger.merge import PARSERS, month_folders
from sbretire.ledger.parsers import hl, ii, schwab, vanguard

HOLDINGS_PARSERS: Final = {
    "schwab": schwab.parse_holdings,
    "hl": hl.parse_holdings,
    "vanguard": vanguard.parse_holdings,
    "ii": ii.parse_holdings,
}
DATE_SPREAD_DAYS: Final = 7
FX_TOLERANCE: Final = 0.02


class ValuationError(ValueError):
    """The holdings cannot be valued as asked (e.g. a USD account without ``--usd-gbp``)."""


@dataclass(frozen=True)
class Valuation:
    """The newest folder's holdings with dates assigned, and the rate used for USD."""

    folder: str
    holdings: list[Holding]
    usd_gbp: float | None
    stated_fx: list[tuple[str, float, dt.date]]
    """(file, GBP per USD, date) for every export that states its own rate."""
    warnings: list[str]

    def rate(self, currency: str) -> float:
        """GBP per unit of ``currency``."""
        if currency == "GBP":
            return 1.0
        if currency == "USD" and self.usd_gbp is not None:
            return self.usd_gbp
        raise ValuationError(f"no rate for {currency}")

    def value_gbp(self, holding: Holding) -> float:
        return round(holding.value * self.rate(holding.currency), 2)

    def by_account(self) -> dict[str, tuple[float, float]]:
        """Account id → (securities, cash) in GBP, in export order."""
        totals: dict[str, list[float]] = {}
        for holding in self.holdings:
            entry = totals.setdefault(holding.account, [0.0, 0.0])
            entry[holding.kind == "cash"] += self.value_gbp(holding)
        return {account: (round(s, 2), round(c, 2)) for account, (s, c) in totals.items()}

    def by_owner(self) -> dict[str, float]:
        """Owner (person id) → GBP."""
        totals: dict[str, float] = defaultdict(float)
        for holding in self.holdings:
            totals[holding.owner] += self.value_gbp(holding)
        return {owner: round(value, 2) for owner, value in totals.items()}

    def total_gbp(self) -> float:
        return round(sum(self.value_gbp(holding) for holding in self.holdings), 2)

    def dates(self) -> dict[str, tuple[dt.date, bool]]:
        """Account id → (valuation date, whether the export stated it)."""
        found: dict[str, tuple[dt.date, bool]] = {}
        for holding in self.holdings:
            if holding.valuation_date is not None:
                found.setdefault(holding.account, (holding.valuation_date, holding.date_stated))
        return found


def read_holdings(root: Path, accounts: Sequence[AccountConfig]) -> tuple[str, list[HoldingsExport]]:
    """Every account's holdings from the newest ``<mon>-<yy>`` folder under ``root`` (portfolio-data §7).

    Where a pattern matches several files the last by name is used (provider names carry the date). An export
    without a cash line (ii) takes its cash from the newest running balance in the account's transactions
    export in the same folder. Raises ``HoldingsError`` for a missing export, a shared file read by accounts
    without ``holdings_filter``, or an export that does not add up.
    """
    folders = month_folders(root)
    if not folders:
        raise HoldingsError(root / "<mon>-<yy>", "no month folders")
    folder = folders[-1][1]
    names = sorted(path.name for path in folder.iterdir() if path.is_file())

    def matching(patterns: Sequence[str]) -> list[str]:
        return [name for name in names if any(fnmatch.fnmatch(name, pattern) for pattern in patterns)]

    chosen: dict[str, str] = {}
    for account in accounts:
        found = matching(account.holdings)
        if not found:
            problem = f"no holdings export for {account.id} in {folder.name}"
            raise HoldingsError(folder / account.holdings[0], problem)
        chosen[account.id] = found[-1]
    readers: dict[str, list[AccountConfig]] = defaultdict(list)
    for account in accounts:
        readers[chosen[account.id]].append(account)
    for name, sharing in readers.items():
        unfiltered = [account.id for account in sharing if account.holdings_filter is None]
        if len(sharing) > 1 and unfiltered:
            problem = f"read by {len(sharing)} accounts; set holdings_filter for {', '.join(unfiltered)}"
            raise HoldingsError(folder / name, problem)

    exports = []
    for account in accounts:
        path = folder / chosen[account.id]
        export = HOLDINGS_PARSERS[account.provider](path, account)
        holdings = list(export.holdings)
        if not any(holding.kind == "cash" for holding in holdings):
            transactions = [folder / name for name in matching(account.transactions)]
            rows = [row for file in transactions for row in PARSERS[account.provider](file, account)]
            named = transactions[-1] if transactions else path
            holdings.append(ii.cash_from_transactions(rows, account, named))
        where = {
            holding.source_file: f"{folder.name}/{holding.source_file}" for holding in holdings
        }  # both the holdings file and, for ii's cash, the transactions file
        exports.append(
            dataclasses.replace(
                export,
                holdings=[dataclasses.replace(h, source_file=where[h.source_file]) for h in holdings],
            )
        )
    return folder.name, exports


def value_holdings(folder: str, exports: Sequence[HoldingsExport], usd_gbp: float | None) -> Valuation:
    """Assign missing dates, check the rate and the date spread; the valuation (portfolio-data §8–§9).

    Raises ``ValuationError`` when an account is in a currency with no rate (USD needs ``usd_gbp``).
    """
    holdings = [holding for export in exports for holding in export.holdings]
    stated = sorted({h.valuation_date for h in holdings if h.date_stated and h.valuation_date is not None})
    if not stated:
        raise ValuationError("no holdings export states a valuation date")
    assumed = stated[-1]
    holdings = [
        dataclasses.replace(h, valuation_date=assumed, date_stated=False) if h.valuation_date is None else h
        for h in holdings
    ]
    for currency in sorted({holding.currency for holding in holdings} - {"GBP"}):
        if currency != "USD":
            raise ValuationError(f"no rate for {currency}; only GBP and USD (with --usd-gbp) are supported")
        if usd_gbp is None:
            accounts = sorted({h.account for h in holdings if h.currency == "USD"})
            raise ValuationError(f"--usd-gbp is required: {', '.join(accounts)} is valued in USD")
    stated_fx = []
    for export in exports:
        if export.stated_fx is not None and export.holdings:
            stated_fx.append((export.holdings[0].source_file, *export.stated_fx))
    warnings = []
    if (stated[-1] - stated[0]).days > DATE_SPREAD_DAYS:
        warnings.append(
            f"valuation dates span {stated[0].isoformat()} to {stated[-1].isoformat()} "
            f"(more than {DATE_SPREAD_DAYS} days)"
        )
    for source, rate, on in stated_fx:
        if usd_gbp is not None and abs(usd_gbp - rate) / rate > FX_TOLERANCE:
            warnings.append(
                f"--usd-gbp {usd_gbp:.4f} differs by more than {FX_TOLERANCE:.0%} from the {rate:.4f} "
                f"stated in {source} on {on.isoformat()}"
            )
    return Valuation(folder, holdings, usd_gbp, stated_fx, warnings)


def write_holdings_csv(valuation: Valuation, path: Path) -> None:
    """UTF-8, LF; the ``Holding`` fields then ``fx_rate`` and ``value_gbp``; ``None`` written empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow((*HOLDING_COLUMNS, "fx_rate", "value_gbp"))
        for holding in valuation.holdings:
            values = ("" if value is None else value for value in dataclasses.astuple(holding))
            writer.writerow((*values, valuation.rate(holding.currency), valuation.value_gbp(holding)))


def format_valuation(valuation: Valuation, accounts: Sequence[AccountConfig]) -> str:
    """The per-account table, per-person and household totals, warnings and the line to paste."""
    rate = "" if valuation.usd_gbp is None else f" at {valuation.usd_gbp:.4f} GBP per USD (--usd-gbp)"
    lines = [f"Valuation of {valuation.folder}{rate}"]
    for source, fx, on in valuation.stated_fx:
        lines.append(f"  {source} states {fx:.4f} GBP per USD on {on.isoformat()}")
    head = ("account", "owner", "date", "securities", "cash", "total GBP")
    lines.append("  {:<18} {:<10} {:<18} {:>14} {:>12} {:>14}".format(*head))
    dates = valuation.dates()
    owners = {account.id: account.owner for account in accounts}
    for account, (securities, cash) in valuation.by_account().items():
        on, stated = dates[account]
        when = on.isoformat() + ("" if stated else " (assumed)")
        lines.append(
            f"  {account:<18} {owners.get(account, ''):<10} {when:<18} {securities:>14,.2f} {cash:>12,.2f} "
            f"{securities + cash:>14,.2f}"
        )
    lines += [f"  {owner}: {value:,.2f} GBP" for owner, value in valuation.by_owner().items()]
    total = valuation.total_gbp()
    lines.append(f"Household total: {total:,.2f} GBP")
    lines += [f"warning: {warning}" for warning in valuation.warnings]
    span = sorted(on for on, _ in dates.values())
    lines += [
        "Paste into config/model.yaml:",
        "portfolio:",
        f"  starting_balance: {round(total)}  # sbretire portfolio value: {valuation.folder}, "
        f"{span[0].isoformat()} to {span[-1].isoformat()}",
    ]
    return "\n".join(lines)
