# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30"]
# ///
"""Corpus size for the experiments log: files, pages, characters and estimated tokens.

Text comes from pypdfium2 (PDF) and a stdlib HTML-to-text pass (HTML, scripts/styles dropped).
Tokens are estimated as characters / 4, a rough rule for English. Real counts come with the embedder on Day 3.

Usage: uv run spikes/corpus_stats.py
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MESSY = ROOT / "data" / "messy"


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "nav"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def pdf_stats(path: Path) -> tuple[int, int]:
    try:
        doc = pdfium.PdfDocument(str(path))
    except pdfium.PdfiumError:
        return 0, 0  # e.g. password-protected
    chars = sum(len(" ".join(doc[i].get_textpage().get_text_range().split())) for i in range(len(doc)))
    return len(doc), chars


def html_chars(path: Path) -> int:
    p = TextOnly()
    p.feed(path.read_text(errors="replace"))
    return len(" ".join(" ".join(p.parts).split()))


def main() -> None:
    rows = []
    for f in sorted((RAW / "pdf").glob("*.pdf")):
        pages, chars = pdf_stats(f)
        rows.append((f"raw/pdf/{f.name}", f.stat().st_size, pages, chars))
    html = sorted((RAW / "html").rglob("*.html"))
    rows.append((f"raw/html ({len(html)} pages)", sum(f.stat().st_size for f in html), len(html), sum(map(html_chars, html))))
    for f in sorted(MESSY.glob("*.pdf")):
        pages, chars = pdf_stats(f)
        rows.append((f"messy/{f.name}", f.stat().st_size, pages, chars))

    print("| Source | MB | Pages | Chars (native text) | ~Tokens |")
    print("|---|---|---|---|---|")
    for name, size, pages, chars in rows:
        print(f"| {name} | {size / 1e6:.1f} | {pages} | {chars:,} | {chars // 4:,} |")
    core = [r for r in rows if not r[0].startswith("messy/oversized")]
    print(
        f"| **Total excl. oversized** | {sum(r[1] for r in core) / 1e6:.1f} | {sum(r[2] for r in core)} "
        f"| {sum(r[3] for r in core):,} | {sum(r[3] for r in core) // 4:,} |"
    )


if __name__ == "__main__":
    main()
