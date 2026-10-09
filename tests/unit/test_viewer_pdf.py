"""F-023.4 — the viewer prints to A4 portrait PDFs (headless Edge or Chrome; skipped when neither can print).

Renders docs/design/sample/runs (example config only) with scripts/render_viewer_pdf.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import render_viewer_pdf

A4_POINTS = (595.0, 842.0)


def _page_sizes(pdf: Path) -> list[tuple[float, float]]:
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf.read_bytes())
    return [(float(width), float(height)) for width, height in boxes]


@pytest.mark.slow
def test_viewer_pdf_pages_are_a4(tmp_path: Path) -> None:
    browser = render_viewer_pdf.find_browser()
    if browser is None:
        pytest.skip("no Edge or Chrome installed to print the viewer")
    written = render_viewer_pdf.render(render_viewer_pdf.SAMPLE_RUNS, tmp_path, browser)
    if not written:
        pytest.skip(f"{browser} did not print headlessly here (close it if an update is pending)")
    assert {path.name for path in written} == {"viewer-single.pdf", "viewer-compare.pdf"}
    for pdf in written:
        sizes = _page_sizes(pdf)
        assert len(sizes) >= 5, pdf.name
        for width, height in sizes:
            assert abs(width - A4_POINTS[0]) < 2 and abs(height - A4_POINTS[1]) < 2, (pdf.name, width, height)
