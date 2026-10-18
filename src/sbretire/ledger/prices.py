"""Price series: the securities map and the household's price files (F-026; portfolio-data §11–§12).

Files are read, never fetched: Yahoo Finance "Historical data" downloads as they are, or any CSV with
``Date``, ``Close`` and an optional ``Dividend`` column. The last row in each calendar month is its value.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from sbretire._yaml import YamlLoadError, load_yaml
from sbretire.config import ScenarioError, ScenarioIssue, _format_location, _text
from sbretire.ledger.accounts import validation_issues
from sbretire.ledger.parsers._common import csv_rows, read_text
from sbretire.ledger.taxonomy import NAMES, Dimension, canonical

Quote = Literal["GBP", "GBX", "USD"]
Basis = Literal["adjusted", "dividends", "price"]
Text = Annotated[str, BeforeValidator(_text), Field(min_length=1)]
HoldingRef = Annotated[str, BeforeValidator(_text), Field(pattern=r"^[^:]+:.+$")]


def _named(dimension: Dimension) -> Callable[[object], object]:
    """A before-validator mapping a label to its fixed name, or failing with the allowed names."""

    def check(value: object) -> object:
        if value is None:
            return None
        found = canonical(dimension, str(value))
        if found is None:
            raise ValueError(
                f"unknown {dimension.replace('_', ' ')} {value!r}; use one of {', '.join(NAMES[dimension])}"
            )
        return found

    return check


class SeriesConfig(BaseModel):
    """One price series and the holdings (``<account id>:<security key>``) it prices."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Text
    name: Text
    file: Text
    """File name inside the prices folder."""
    quote: Quote
    """Currency the file's prices are in: GBP, GBX (pence) or USD."""
    holdings: Annotated[tuple[HoldingRef, ...], Field(min_length=1)]
    factsheet: Text | None = None
    """A fund's factsheet file in the factsheets folder (F-028)."""
    sector: Annotated[str, BeforeValidator(_named("sector"))] | None = None
    """A single stock's sector (one of the fixed names, or an alias)."""
    region: Annotated[str, BeforeValidator(_named("region"))] | None = None
    asset_class: Annotated[str, BeforeValidator(_named("asset_class"))] | None = None
    """A single stock's asset class; ``None`` means equity."""
    currency: Annotated[str, BeforeValidator(_named("currency"))] | None = None
    """A single stock's currency exposure; ``None`` means the region's currency."""


class SecuritiesConfig(BaseModel):
    """``data/prices/securities.yaml``: the FX file per non-GBP quote currency, and every price series."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_weight: Annotated[float, Field(gt=0.0, le=1.0)] = 0.25
    """Largest share of the priced sleeve any one series may take in the frontier (F-029)."""
    risk_free_rate: Annotated[float, Field(ge=0.0, lt=0.2)] | None = None
    """Annual risk-free rate (UK Bank Rate) as a fraction, for Sharpe ratios (F-027)."""
    fx: dict[Literal["USD"], Text] = Field(default_factory=dict)
    """Quote currency → file of GBP per unit of it (e.g. Yahoo ``GBP=X`` for USD)."""
    securities: Annotated[tuple[SeriesConfig, ...], Field(min_length=1)]


def load_securities(path: Path) -> SecuritiesConfig:
    """Read and validate the securities map; ``ScenarioError`` lists every problem with its YAML location."""
    try:
        raw = load_yaml(path.read_text(encoding="utf-8"))
    except YamlLoadError as exc:
        raise ScenarioError(
            [ScenarioIssue(_format_location(loc), msg) for loc, msg in exc.problems]
        ) from None
    if not isinstance(raw, Mapping):
        raise ScenarioError(
            [ScenarioIssue("(securities)", "top level must be a mapping with a securities list")]
        )
    try:
        parsed = SecuritiesConfig.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError(validation_issues(exc)) from None
    issues = []
    ids: dict[str, int] = {}
    mapped: dict[str, str] = {}
    for index, series in enumerate(parsed.securities):
        if series.id in ids:
            issues.append(
                ScenarioIssue(
                    f"securities[{index}].id",
                    f"duplicate id {series.id!r} (also securities[{ids[series.id]}])",
                )
            )
        ids.setdefault(series.id, index)
        for position, holding in enumerate(series.holdings):
            if holding in mapped:
                issues.append(
                    ScenarioIssue(
                        f"securities[{index}].holdings[{position}]",
                        f"{holding!r} is already priced by series {mapped[holding]!r}",
                    )
                )
            mapped.setdefault(holding, series.id)
    if issues:
        raise ScenarioError(issues)
    return parsed


class PriceFileError(ValueError):
    """A price file with no usable layout or no prices; names the file."""

    def __init__(self, path: Path, problem: str) -> None:
        super().__init__(f"{path.name}: {problem}")


@dataclass(frozen=True)
class MonthEnd:
    """A month's last price and the dividends paid in it, in the file's quote units (GBX not yet divided)."""

    month: dt.date
    """First day of the month."""
    close: float
    dividend: float


@dataclass(frozen=True)
class PriceFile:
    """A price file reduced to month-ends, with its provenance."""

    path: Path
    basis: Basis
    months: list[MonthEnd]
    first: dt.date
    last: dt.date
    rows: int
    """Rows with a usable price."""
    sha256: str


def _number(text: str) -> float | None:
    value = text.strip().replace(",", "")
    if not value or value.lower() in {"null", "nan", "n/a", "-"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_price_file(path: Path) -> PriceFile:
    """Month-ends from a Yahoo download (``Adj Close``) or a ``Date,Close[,Dividend]`` file.

    Basis: ``adjusted`` when ``Adj Close`` is present (dividends already in the price), ``dividends`` when a
    ``Dividend`` column is, else ``price``. Rows with no usable price are skipped; dividends on such rows
    still count. Raises ``PriceFileError`` when neither price column exists or no row has a price.
    """
    data = path.read_bytes()
    table = csv_rows(read_text(path))
    if not table:
        raise PriceFileError(path, "empty file")
    col = {name.strip(): index for index, name in enumerate(table[0])}
    if "Date" not in col or not ({"Adj Close", "Close"} & col.keys()):
        raise PriceFileError(path, "needs a Date column and a Close or Adj Close column")
    price_column = "Adj Close" if "Adj Close" in col else "Close"
    basis: Basis = (
        "adjusted" if price_column == "Adj Close" else "dividends" if "Dividend" in col else "price"
    )
    closes: dict[dt.date, tuple[dt.date, float]] = {}
    dividends: dict[dt.date, float] = {}
    dates = []
    for number, record in enumerate(table[1:], start=2):
        if not any(cell.strip() for cell in record):
            continue
        try:
            day = dt.date.fromisoformat(record[col["Date"]].strip()[:10])
        except ValueError:
            raise PriceFileError(
                path, f"row {number}: date {record[col['Date']]!r} is not YYYY-MM-DD"
            ) from None
        month = day.replace(day=1)
        if basis == "dividends":
            paid = _number(record[col["Dividend"]]) if col["Dividend"] < len(record) else None
            dividends[month] = dividends.get(month, 0.0) + (paid or 0.0)
        price = _number(record[col[price_column]]) if col[price_column] < len(record) else None
        if price is None or price <= 0:
            continue
        dates.append(day)
        if month not in closes or day >= closes[month][0]:
            closes[month] = (day, price)
    if not dates:
        raise PriceFileError(path, "no rows with a price")
    months = [MonthEnd(month, closes[month][1], dividends.get(month, 0.0)) for month in sorted(closes)]
    return PriceFile(
        path=path,
        basis=basis,
        months=months,
        first=min(dates),
        last=max(dates),
        rows=len(dates),
        sha256=hashlib.sha256(data).hexdigest(),
    )
