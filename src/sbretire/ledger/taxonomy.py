"""Fixed names for look-through exposures, with aliases for factsheet wording (F-028; portfolio-data §18).

Matching ignores case, spaces and punctuation: "Europe ex-UK", "europe ex uk" and "Europe ex UK" are one
region.
"""

from __future__ import annotations

import re
from typing import Final, Literal

Dimension = Literal["asset_class", "sector", "region", "currency"]

SECTORS: Final = (
    "Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy", "Financials",
    "Health Care", "Industrials", "Information Technology", "Materials", "Real Estate", "Utilities", "Other",
)  # fmt: skip
REGIONS: Final = (
    "UK", "North America", "Europe ex UK", "Japan", "Asia Pacific ex Japan", "Emerging Markets", "Other",
)  # fmt: skip
ASSET_CLASSES: Final = ("equity", "bond", "cash", "property", "other")
CURRENCIES: Final = ("GBP", "USD", "EUR", "JPY", "Other")
NAMES: Final[dict[Dimension, tuple[str, ...]]] = {
    "asset_class": ASSET_CLASSES,
    "sector": SECTORS,
    "region": REGIONS,
    "currency": CURRENCIES,
}

_ALIASES: Final[dict[Dimension, dict[str, str]]] = {
    "sector": {
        "technology": "Information Technology",
        "it": "Information Technology",
        "tech": "Information Technology",
        "healthcare": "Health Care",
        "telecommunications": "Communication Services",
        "telecommunication services": "Communication Services",
        "communication": "Communication Services",
        "communications": "Communication Services",
        "consumer cyclical": "Consumer Discretionary",
        "consumer cyclicals": "Consumer Discretionary",
        "consumer defensive": "Consumer Staples",
        "basic materials": "Materials",
        "financial services": "Financials",
        "financial": "Financials",
        "property": "Real Estate",
        "bonds": "Other",
        "fixed income": "Other",
        "government bonds": "Other",
        "cash": "Other",
    },
    "region": {
        "united kingdom": "UK",
        "uk": "UK",
        "great britain": "UK",
        "united states": "North America",
        "us": "North America",
        "usa": "North America",
        "europe": "Europe ex UK",
        "europe ex uk": "Europe ex UK",
        "developed europe ex uk": "Europe ex UK",
        "asia pacific": "Asia Pacific ex Japan",
        "pacific ex japan": "Asia Pacific ex Japan",
        "developed asia": "Asia Pacific ex Japan",
        "emerging": "Emerging Markets",
        "emerging markets": "Emerging Markets",
    },
    "asset_class": {
        "equities": "equity",
        "shares": "equity",
        "stocks": "equity",
        "bonds": "bond",
        "fixed income": "bond",
        "fixed interest": "bond",
        "money market": "cash",
        "real estate": "property",
    },
    "currency": {},
}


def _key(label: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", label.lower()).split())


def canonical(dimension: Dimension, label: str) -> str | None:
    """The fixed name ``label`` stands for in ``dimension``; ``None`` if it is neither a name nor an alias."""
    key = _key(label)
    for name in NAMES[dimension]:
        if _key(name) == key:
            return name
    return _ALIASES[dimension].get(key)


def region_currency(region: str) -> str:
    """The currency a region's assets are taken to be in when a factsheet gives no currencies (§19)."""
    return {"UK": "GBP", "North America": "USD", "Europe ex UK": "EUR", "Japan": "JPY"}.get(region, "Other")
