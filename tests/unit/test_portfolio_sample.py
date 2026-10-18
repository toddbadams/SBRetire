"""F-030.4 — the synthetic design sample (schema 1.0) and the links between the two pages."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "docs" / "design" / "sample" / "portfolio"
SCHEMA = json.loads((ROOT / "schemas" / "portfolio.schema.json").read_text(encoding="utf-8"))


def test_portfolio_design_sample_and_links() -> None:
    document = json.loads((SAMPLE / "portfolio.json").read_text(encoding="utf-8"))
    jsonschema.validate(document, SCHEMA)
    assert document["schema_version"] == "1.1" and document["synthetic"] is True
    for section in ("exposure", "performance", "frontier", "risk", "rebalance", "income"):
        assert document[section]["available"], section  # the sample shows every part of the page
    script = (SAMPLE / "portfolio.js").read_text(encoding="utf-8")
    prefix = "window.SBRETIRE_PORTFOLIO = "
    assert script.startswith(prefix) and json.loads(script[len(prefix) : -2]) == document
    generator = (ROOT / "scripts" / "build_portfolio_design_sample.py").read_text(encoding="utf-8")
    assert "build_portfolio_document" in generator and "0.1-draft" not in generator

    viewer = (ROOT / "src" / "sbretire" / "web" / "viewer" / "index.html").read_text(encoding="utf-8")
    page = (ROOT / "src" / "sbretire" / "web" / "portfolio" / "portfolio.html").read_text(encoding="utf-8")
    assert 'href="portfolio.html"' in viewer and 'href="index.html"' in page
