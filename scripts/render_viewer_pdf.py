"""Render the results viewer to PDF with headless Edge or Chrome, for reviewing the print layout (F-023).

Usage:
    uv run python scripts/render_viewer_pdf.py [--runs DIR] [--out DIR]

Copies the viewer (``sbretire.results_json.copy_viewer``) and a runs folder (default: the example-config
sample in docs/design/sample/runs) into a temporary folder, then prints ``viewer-single.pdf`` (the newest run)
and ``viewer-compare.pdf`` (the two newest runs) into ``--out`` (default output/pdf-check). The PDFs are what
the "Save as PDF" button produces: black and white, A4. ``--runs output/runs`` renders your own runs, which
hold personal data, so keep the output folder private.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from sbretire.results_json import copy_viewer

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RUNS = ROOT / "docs" / "design" / "sample" / "runs"
BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def find_browser() -> Path | None:
    """``SBRETIRE_BROWSER`` if set, else the first installed Edge or Chrome; None when there is none."""
    configured = os.environ.get("SBRETIRE_BROWSER")
    candidates = (configured,) if configured else BROWSERS
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _print(browser: Path, page: Path, fragment: str, pdf: Path) -> bool:
    """Print ``page#fragment`` to ``pdf``, with a fresh profile per attempt (a reused one can exit early)."""
    url = page.as_uri() + "#" + quote(fragment, safe="=&-_")
    for _ in range(3):
        with tempfile.TemporaryDirectory(prefix="sbretire-browser-") as profile:
            subprocess.run(
                [
                    str(browser),
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--no-pdf-header-footer",
                    "--virtual-time-budget=10000",
                    f"--user-data-dir={profile}",
                    f"--print-to-pdf={pdf}",
                    url,
                ],
                capture_output=True,
                timeout=180,
                check=False,
            )
        if pdf.is_file() and pdf.stat().st_size > 0:
            return True
    return False


def render(runs: Path, out: Path, browser: Path) -> list[Path]:
    """Print the single-run and compare views of ``runs`` into ``out``; the PDFs actually written."""
    index = json.loads((runs / "index.json").read_text(encoding="utf-8"))["runs"]
    names = [entry["name"] for entry in index]
    views = {"viewer-single.pdf": f"run={names[0]}"}
    if len(names) > 1:
        views["viewer-compare.pdf"] = f"run={names[0]}&compare={names[1]}"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory(prefix="sbretire-viewer-") as stage:
        stage_dir = Path(stage)
        shutil.copytree(runs, stage_dir / "runs")
        copy_viewer(stage_dir)
        for file_name, fragment in views.items():
            pdf = out / file_name
            pdf.unlink(missing_ok=True)
            if _print(browser, stage_dir / "index.html", fragment, pdf):
                written.append(pdf)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, default=SAMPLE_RUNS, help="folder with index.json and runs.js")
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "pdf-check", help="where the PDFs go")
    args = parser.parse_args()
    browser = find_browser()
    if browser is None:
        print("error: no Edge or Chrome found; set SBRETIRE_BROWSER to a Chromium-based browser")
        return 1
    written = render(args.runs, args.out, browser)
    for pdf in written:
        print(f"Wrote {pdf}")
    if not written:
        print(
            f"error: {browser.name} printed nothing. Close every window of it (a pending update can block "
            "headless printing) and try again, or set SBRETIRE_BROWSER to another Chromium-based browser."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
