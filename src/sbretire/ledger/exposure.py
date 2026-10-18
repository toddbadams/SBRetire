"""Look-through exposures: what the household's money is invested in (F-028; portfolio-data §18–§20).

A fund's factsheet (``data/factsheets/<file>.yaml``) gives its asset-class, sector, region and currency
weights as shares of the fund's whole value; a single stock's series carries its sector and region.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Final

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from sbretire._yaml import YamlLoadError, load_yaml
from sbretire.config import ScenarioError, ScenarioIssue, _format_location, _issue, _text
from sbretire.ledger.taxonomy import NAMES, Dimension, canonical, region_currency

Weight = Annotated[float, Field(ge=0.0)]
Weights = dict[str, Weight]
_MAPS: Final[tuple[tuple[str, Dimension], ...]] = (
    ("asset_classes", "asset_class"),
    ("sectors", "sector"),
    ("regions", "region"),
    ("currencies", "currency"),
)
_FRACTION: Final = (0.98, 1.02)
_PERCENT: Final = (98.0, 102.0)


class _FactsheetFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: dt.date
    source: Annotated[str, BeforeValidator(_text), Field(min_length=1)]
    asset_classes: Weights | None = None
    sectors: Weights | None = None
    regions: Weights | None = None
    currencies: Weights | None = None
    top_holdings: Weights = Field(default_factory=dict)


@dataclass(frozen=True)
class Factsheet:
    """A fund's look-through weights, each dimension rescaled to sum to 1."""

    path: Path
    as_of: dt.date
    source: str
    weights: dict[Dimension, dict[str, float]]
    """Dimension → fixed name → share of the fund; a dimension the factsheet leaves out is absent."""
    currency_derived: bool = False
    """True when the currencies were derived from the regions (§19)."""
    top_holdings: dict[str, float] = field(default_factory=dict)
    """Underlying holding → share of the fund (only the largest are published)."""


def load_factsheet(path: Path) -> Factsheet:
    """Read a factsheet; ``ScenarioError`` lists every problem with its YAML location (portfolio-data §18).

    Each weight map may be fractions (summing to 0.98–1.02) or percentages (98–102) and is rescaled to 1.
    Names are mapped to the fixed lists through their aliases; aliases of one name are added together.
    """
    try:
        raw = load_yaml(path.read_text(encoding="utf-8"))
    except YamlLoadError as exc:
        raise ScenarioError(
            [ScenarioIssue(_format_location(loc), msg) for loc, msg in exc.problems]
        ) from None
    if not isinstance(raw, Mapping):
        raise ScenarioError([ScenarioIssue("(factsheet)", "top level must be a mapping")])
    try:
        parsed = _FactsheetFile.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError([_issue(error) for error in exc.errors()]) from None

    issues: list[ScenarioIssue] = []
    weights: dict[Dimension, dict[str, float]] = {}
    percent = False
    for key, dimension in _MAPS:
        given: Weights | None = getattr(parsed, key)
        if given is None:
            continue
        merged: dict[str, float] = {}
        for label, weight in given.items():
            name = canonical(dimension, label)
            if name is None:
                allowed = ", ".join(NAMES[dimension])
                issues.append(
                    ScenarioIssue(f"{key}.{label}", f"unknown name {label!r}; use one of {allowed}")
                )
                continue
            merged[name] = merged.get(name, 0.0) + weight
        total = sum(given.values())
        if _PERCENT[0] <= total <= _PERCENT[1]:
            percent = True
        elif not _FRACTION[0] <= total <= _FRACTION[1]:
            issues.append(
                ScenarioIssue(
                    key, f"weights sum to {total:g}; expected about 1 (fractions) or 100 (percentages)"
                )
            )
            continue
        known = sum(merged.values())
        weights[dimension] = {name: weight / known for name, weight in merged.items()} if known else {}
    if issues:
        raise ScenarioError(issues)

    derived = False
    if "currency" not in weights and "region" in weights:
        currencies: dict[str, float] = {}
        for region, weight in weights["region"].items():
            currency = region_currency(region)
            currencies[currency] = currencies.get(currency, 0.0) + weight
        weights["currency"] = currencies
        derived = True
    if not weights:
        percent = any(weight > 1.0 for weight in parsed.top_holdings.values())
    scale = 0.01 if percent else 1.0
    top = {name: weight * scale for name, weight in parsed.top_holdings.items()}
    return Factsheet(path, parsed.as_of, parsed.source, weights, derived, top)
