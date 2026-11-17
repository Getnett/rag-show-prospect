"""Structured lines for chunking: every line of the corpus with its page, font size, weight and (HTML) heading level.

Chunkers need more than flat page text: a heading-aware chunker must know which lines are headings.
- HTML: headings are explicit (<h1>..<h4>), so `level` is set and font fields are None.
- PDF:  headings are NOT marked. Each line carries its font `size` and `bold` so a chunker can infer them.
        (Body text in the Nextcloud manuals is ~10 pt; headings are larger and/or bold.)
- Scanned page with a truth file: plain lines, size None (no font info in an image).

Page numbers are PDF viewer pages, 1-based (HTML = page 1). Cached in spikes/out/doc_lines_cache.json.
Run directly to print the lines of one page:  uv run spikes/doc_lines.py data/raw/pdf/v35_user_manual.pdf 64
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30"]
# ///

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import asdict, dataclass
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from corpus import PDFS, ROOT, TRUTH_FOR_SCANS

CACHE = ROOT / "spikes" / "out" / "doc_lines_cache.json"
CACHE_VERSION = 2


# Invisible characters to drop at extraction (F22): the line-break hyphen arrives as U+0002 when read char by char
# (U+FFFE via get_text_range); U+00AD soft hyphen; U+F0C1 is the Sphinx permalink icon in the HTML headings.
HIDDEN = {"\x02", "\ufffe", "\u00ad", "\uf0c1"}


@dataclass
class Line:
    page: int  # 1-based viewer page (HTML: 1)
    text: str
    size: float | None = None  # median font size of the line's visible characters (PDF only)
    bold: bool | None = None  # most visible characters have font weight >= 600 (PDF only)
    level: int | None = None  # HTML heading level 1-4; None = not a heading / unknown


def _pdf_lines(path: str) -> list[Line]:
    doc = pdfium.PdfDocument(str(ROOT / path))
    out: list[Line] = []
    for p in range(len(doc)):
        truth = TRUTH_FOR_SCANS.get((path, p + 1))
        if truth:
            out += [Line(p + 1, t.strip()) for t in (ROOT / truth).read_text().splitlines() if t.strip()]
            continue
        tp = doc[p].get_textpage()
        chars, sizes, weights = [], [], []

        def flush() -> None:
            text = "".join(chars).strip()
            if text:
                out.append(Line(p + 1, text, round(statistics.median(sizes), 1) if sizes else None,
                                sum(w >= 600 for w in weights) > len(weights) / 2 if weights else None))
            chars.clear(), sizes.clear(), weights.clear()

        for i in range(pdfium_c.FPDFText_CountChars(tp.raw)):
            ch = chr(pdfium_c.FPDFText_GetUnicode(tp.raw, i))
            if ch == "\n":
                flush()
                continue
            if ch == "\r" or ch in HIDDEN:
                continue
            chars.append(ch)
            if not ch.isspace():
                sizes.append(pdfium_c.FPDFText_GetFontSize(tp.raw, i))
                weights.append(pdfium_c.FPDFText_GetFontWeight(tp.raw, i))
        flush()
    return out


class _HtmlLines(HTMLParser):
    SKIP = {"script", "style", "nav", "footer"}
    BLOCK = {"p", "li", "tr", "pre", "div", "dt", "dd", "br", "table", "ul", "ol", "section", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[Line] = []
        self.buf: list[str] = []
        self.skip = 0
        self.level: int | None = None

    def _flush(self) -> None:
        text = " ".join("".join(ch for ch in "".join(self.buf) if ch not in HIDDEN).split())
        if text:
            self.lines.append(Line(1, text, level=self.level))
        self.buf = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP:
            self.skip += 1
        elif tag in ("h1", "h2", "h3", "h4"):
            self._flush()
            self.level = int(tag[1])
        elif tag in self.BLOCK:
            self._flush()
        elif tag in ("td", "th"):
            self.buf.append(" | ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in ("h1", "h2", "h3", "h4"):
            self.buf = [b for b in self.buf if b != "¶"]  # Sphinx permalink anchors
            self._flush()
            self.level = None
        elif tag in self.BLOCK:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.buf.append(data)


def _html_lines(path: str) -> list[Line]:
    parser = _HtmlLines()
    parser.feed((ROOT / path).read_text(errors="replace"))
    parser._flush()
    return parser.lines


def _sources() -> list[str]:
    html = sorted(str(h.relative_to(ROOT)) for h in (ROOT / "data" / "raw" / "html").rglob("*.html"))
    return PDFS + html


@cache
def all_docs() -> dict[str, list[Line]]:
    """{file: [Line, ...]} for every corpus document, in reading order."""
    stamp = {"v": CACHE_VERSION, **{f: (ROOT / f).stat().st_mtime for f in PDFS}}
    if CACHE.exists():
        data = json.loads(CACHE.read_text())
        if data.get("stamp") == stamp:
            return {f: [Line(**ln) for ln in lines] for f, lines in data["docs"].items()}
    docs = {f: (_pdf_lines(f) if f.endswith(".pdf") else _html_lines(f)) for f in _sources()}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps({"stamp": stamp, "docs": {f: [asdict(ln) for ln in ls] for f, ls in docs.items()}}))
    return docs


if __name__ == "__main__":
    file, page = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for ln in all_docs()[file]:
        if ln.page == page:
            tag = f"h{ln.level}" if ln.level else f"{ln.size or '-':>5} {'B' if ln.bold else ' '}"
            print(f"{tag:>8} | {ln.text}")
