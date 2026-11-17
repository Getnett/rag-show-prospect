"""Chunkers for the Day 3 comparison. Each one turns a document's lines into chunks.

Signature (all chunkers):  chunk(file: str, lines: list[Line]) -> list[Chunk]
- `lines` come from doc_lines.all_docs(): page, text, font size/bold (PDF) or heading level (HTML).
- `Chunk.text` is exactly what gets embedded AND what the eval searches for the evidence quote.
  If you prepend a heading path to the text, that's fine: the evidence check is "contains".

Baselines (scaffolded):
- fixed_512:   naive. Glue the whole document together, cut every 512 tokens, no overlap, no structure.
- llamaindex:  LlamaIndex SentenceSplitter with its defaults (1024 tokens, 200 overlap, sentence-aware).
Yours (🟥):
- heading_aware: see the docstring below.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import tiktoken

from doc_lines import Line

ENC = tiktoken.get_encoding("cl100k_base")  # token counter for chunk sizes (OpenAI's tokenizer)


@dataclass
class Chunk:
    file: str
    pages: list[int]  # viewer pages this chunk covers (first..last); HTML = [1]
    text: str  # embedded + matched against evidence quotes
    heading: str = ""  # optional: heading path, e.g. "5.3 Sharing > Public link shares"
    meta: dict = field(default_factory=dict)


def n_tokens(text: str) -> int:
    return len(ENC.encode(text))


def _join(lines: list[Line]) -> tuple[str, list[tuple[int, int]]]:
    """Whole document as one string (lines joined by newlines) + (start offset, page) per line."""
    parts, starts, pos = [], [], 0
    for ln in lines:
        starts.append((pos, ln.page))
        parts.append(ln.text)
        pos += len(ln.text) + 1
    return "\n".join(parts), starts


def _pages_for(starts: list[tuple[int, int]], a: int, b: int) -> list[int]:
    """Pages of the lines that overlap character span [a, b)."""
    pages = [p for i, (s, p) in enumerate(starts) if s < b and (starts[i + 1][0] if i + 1 < len(starts) else 10**12) > a]
    return list(range(min(pages), max(pages) + 1)) if pages else [1]


def fixed_512(file: str, lines: list[Line], size: int = 512) -> list[Chunk]:
    text, starts = _join(lines)
    tokens = ENC.encode(text)
    chunks, char_pos = [], 0
    for i in range(0, len(tokens), size):
        piece = ENC.decode(tokens[i: i + size])
        a = text.find(piece[:50], char_pos)
        a = a if a >= 0 else char_pos
        chunks.append(Chunk(file, _pages_for(starts, a, a + len(piece)), piece))
        char_pos = a + max(1, len(piece) - 50)
    return chunks


def llamaindex(file: str, lines: list[Line]) -> list[Chunk]:
    from llama_index.core import Document
    from llama_index.core.node_parser import SentenceSplitter

    text, starts = _join(lines)
    nodes = SentenceSplitter().get_nodes_from_documents([Document(text=text)])  # defaults on purpose
    out = []
    for n in nodes:
        a = n.start_char_idx if n.start_char_idx is not None else max(0, text.find(n.text[:50]))
        b = n.end_char_idx if n.end_char_idx is not None else a + len(n.text)
        out.append(Chunk(file, _pages_for(starts, a, b), n.text))
    return out


MAX_TOKENS = 400  # cl100k tokens per chunk, heading path included. ~400 cl100k ≈ 450-500 BGE tokens: stays under 512.
ADMONITIONS = {"Note", "Tip", "Warning", "Important", "Hint", "Caution", "Attention", "Danger", "Error", "Seealso"}
REPEATS = 5  # a first/last line seen on >= 5 pages (digits ignored) is a running header/footer


def _strip_digits(text: str) -> str:
    return "".join(ch for ch in text if not ch.isdigit()).strip()


def _running_lines(lines: list[Line]) -> set[str]:
    """Running headers/footers of a PDF: first or last lines of a page that repeat on many pages (page numbers vary,
    so digits are ignored). Learned from the document itself, so it works for any PDF without hard-coded titles."""
    first_last: dict[int, list[Line]] = defaultdict(list)
    for ln in lines:
        first_last[ln.page].append(ln)
    counts: dict[str, int] = defaultdict(int)
    for page_lines in first_last.values():
        for ln in {page_lines[0].text, page_lines[-1].text}:
            counts[_strip_digits(ln)] += 1
    return {t for t, n in counts.items() if t and n >= REPEATS}  # "" = a bare page number; keep numeric body lines


def heading_level(line: Line) -> int | None:
    """1 = chapter, 2 = section, 3 = subsection, 4 = minor heading. None = body text."""
    if line.level:  # HTML: explicit <h1>-<h4>
        return line.level
    if not line.bold or line.size is None:  # body text, or a scanned page (no font info)
        return None
    t = line.text
    if line.size >= 14:
        return 1 if t.isupper() else 2  # "FILES & SYNCHRONIZATION" vs "5.2 Managing your files"
    if line.size >= 11.5:
        return 3  # "5.2.1 Deleted files"
    # Minor headings are body-sized bold lines. Exclude the bold things that aren't headings.
    if t.split()[-1] in ADMONITIONS and len(t) < 15:
        return None  # "® Note", "b Tip": Sphinx callout boxes, not sections
    if len(t) < 60 and t[-1] not in ".:,;" and not t[-1].isdigit() and t[0] not in "•–-®(" and any(c.isalpha() for c in t):
        return 4  # "Public link shares"
    return None


def _pieces(body: list[Line], path: str, max_tokens: int = MAX_TOKENS) -> list[tuple[str, list[int]]]:
    """Pack whole lines into pieces of <= max_tokens, each starting with the heading path. Never cuts a line,
    except a single line that alone is too long (rare: long code/URLs), which is cut by tokens."""
    budget = max_tokens - n_tokens(path) - 1
    out, cur, cur_tok = [], [], 0
    def emit() -> None:
        if cur:
            out.append(("\n".join([path, *[ln.text for ln in cur]]).strip(), sorted({ln.page for ln in cur})))
    for ln in body:
        t = n_tokens(ln.text) + 1
        if t > budget:  # one oversized line: emit what we have, then hard-split the line
            emit(); cur, cur_tok = [], 0
            toks = ENC.encode(ln.text)
            for i in range(0, len(toks), budget):
                out.append((path + "\n" + ENC.decode(toks[i:i + budget]), [ln.page]))
            continue
        if cur_tok + t > budget:
            emit(); cur, cur_tok = [], 0
        cur.append(ln); cur_tok += t
    emit()
    return out


def heading_aware(file: str, lines: list[Line]) -> list[Chunk]:
    """One chunk per section (split further if long), heading path on top, page breaks ignored.

    Steps: drop noise lines (running header/footer, TOC dot leaders) -> walk the lines keeping a heading path
    -> at each heading, flush the previous section's body into chunks -> pack long sections into <= MAX_TOKENS pieces.
    """
    running = _running_lines(lines) if file.endswith(".pdf") else set()
    path: dict[int, str] = {}  # level -> heading text, e.g. {2: "5.2 Managing your files", 3: "5.2.1 Deleted files"}
    body: list[Line] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        heading = " > ".join(path[k] for k in sorted(path))
        for text, pages in _pieces(body, heading):
            chunks.append(Chunk(file, pages, text, heading))
        body.clear()

    for ln in lines:
        if _strip_digits(ln.text) in running or ". . . ." in ln.text or ln.text == "Edit on GitHub":
            continue  # header/footer, table-of-contents line, HTML page chrome
        lvl = heading_level(ln)
        if lvl is None:
            body.append(ln)
            continue
        flush()  # the previous section ends here
        for k in [k for k in path if k >= lvl]:
            del path[k]  # a new section closes its old subsections
        path[lvl] = ln.text
    flush()
    return chunks


CHUNKERS = {"fixed_512": fixed_512, "llamaindex": llamaindex, "heading_aware": heading_aware}
