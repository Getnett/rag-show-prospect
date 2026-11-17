"""Shared corpus access for Week 0 spikes: which documents are in the index, and the text of each page.

Day 3+ index ("the corpus"): v35 User + Admin manual PDFs, the 99 crawled HTML pages, and three messy files
(the real scan, the two-column PDF, the Acme table PDF). v33 manuals are kept out until Day 6 (conflict test).

Page numbers are **PDF viewer page numbers, 1-based** (what Preview/Acrobat shows), not the number printed
in the page footer. Example: the AI assistant page is printed "13" but is viewer page 17.

Scanned pages have no native text, so their text comes from the hand-checked truth files in data/messy/truth/.
"""

from __future__ import annotations

import json
import re
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "spikes" / "out" / "page_text_cache.json"

PDFS = [
    "data/raw/pdf/v35_user_manual.pdf",
    "data/raw/pdf/v35_admin_manual.pdf",
    "data/messy/scanned-nextcloud-user-manual.pdf",
    "data/messy/two_column.pdf",
    "data/messy/table_heavy.pdf",
]
TRUTH_FOR_SCANS = {("data/messy/scanned-nextcloud-user-manual.pdf", 1): "data/messy/truth/scanned-nextcloud-user-manual.txt"}


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "nav", "footer"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def normalize(text: str) -> str:
    """Lowercase, straight quotes and dashes, single spaces: for matching evidence quotes."""
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("–", "-").replace("—", "-").replace(" ", " ")
    # pypdfium2 returns U+FFFE where the PDF hyphenated a word across a line break ("re￾share");
    # U+00AD is the soft hyphen other tools return. Both are invisible in a viewer, so drop them.
    text = re.sub("[\ufffe\u00ad\x02\uf0c1]", "", text)  # invisible chars, see doc_lines.HIDDEN (F22)
    return re.sub(r"\s+", " ", text).strip().lower()


def _build() -> dict[str, list[str]]:
    pages: dict[str, list[str]] = {}
    for f in PDFS:
        doc = pdfium.PdfDocument(str(ROOT / f))
        texts = []
        for i in range(len(doc)):
            truth = TRUTH_FOR_SCANS.get((f, i + 1))
            texts.append((ROOT / truth).read_text() if truth else doc[i].get_textpage().get_text_range())
        pages[f] = texts
    for h in sorted((ROOT / "data" / "raw" / "html").rglob("*.html")):
        parser = _TextOnly()
        parser.feed(h.read_text(errors="replace"))
        pages[str(h.relative_to(ROOT))] = [" ".join(parser.parts)]  # one "page" per HTML file
    return pages


@cache
def all_pages() -> dict[str, list[str]]:
    """{file: [page 1 text, page 2 text, ...]}. Cached on disk; rebuilt when a source file changes."""
    stamp = {f: (ROOT / f).stat().st_mtime for f in PDFS}
    if CACHE.exists():
        data = json.loads(CACHE.read_text())
        if data.get("stamp") == stamp:
            return data["pages"]
    pages = _build()
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps({"stamp": stamp, "pages": pages}))
    return pages


def page_text(file: str, page: int | None) -> str | None:
    texts = all_pages().get(file)
    if texts is None:
        return None
    index = (page or 1) - 1
    return texts[index] if 0 <= index < len(texts) else None
