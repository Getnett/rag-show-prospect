# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30", "pyyaml>=6.0"]
# ///
"""Validate a golden set: fields, ids, categories, and that every evidence quote is really on its cited page.

Usage: uv run spikes/check_golden.py [eval/golden/g20-v1.yaml]
Exit code 1 if anything is wrong, so it can run in CI later.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

from corpus import ROOT, normalize, page_text

CATEGORIES = {"direct": 5, "multi_chunk": 3, "table": 2, "scanned": 2, "follow_up": 2,
              "unanswerable": 3, "out_of_scope": 2, "injection": 1}
NO_SOURCES = {"unanswerable", "out_of_scope"}


def check(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    ids = Counter(e.get("id") for e in entries)
    errors += [f"duplicate id {i}" for i, n in ids.items() if n > 1]
    known = set(ids)
    for e in entries:
        qid = e.get("id", "?")
        for field in ("id", "category", "question", "answer"):
            if not str(e.get(field) or "").strip():
                errors.append(f"{qid}: missing {field}")
        cat = e.get("category")
        if cat not in CATEGORIES:
            errors.append(f"{qid}: unknown category {cat!r}")
            continue
        sources = e.get("sources") or []
        if cat in NO_SOURCES and sources:
            errors.append(f"{qid}: {cat} questions should have no sources")
        if cat not in NO_SOURCES and cat != "injection" and not sources:
            errors.append(f"{qid}: needs at least one source")
        if cat == "multi_chunk" and (len(sources) < 2 or not e.get("need_all")):
            errors.append(f"{qid}: multi_chunk needs need_all: true and 2+ sources")
        if cat == "follow_up" and e.get("follows") not in known:
            errors.append(f"{qid}: follow_up must name an existing previous id in `follows`")
        for s in sources:
            text = page_text(s.get("file", ""), s.get("page"))
            where = f"{s.get('file')} p{s.get('page', '-')}"
            if text is None:
                errors.append(f"{qid}: source not in the corpus or page out of range: {where}")
            elif not str(s.get("evidence") or "").strip():
                errors.append(f"{qid}: source {where} has no evidence quote")
            elif normalize(s["evidence"]) not in normalize(text):
                errors.append(f"{qid}: evidence not found on {where}: {s['evidence'][:60]!r}")
    return errors


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "golden" / "g20-v1.yaml"
    entries = (yaml.safe_load(path.read_text()) or {}).get("questions") or []
    errors = check(entries)
    counts = Counter(e.get("category") for e in entries)
    print(f"{path.name}: {len(entries)} questions\n")
    print("| Category | Have | Target |\n|---|---|---|")
    for cat, target in CATEGORIES.items():
        mark = "✓" if counts[cat] >= target else " "
        print(f"| {cat} | {counts[cat]} {mark} | {target} |")
    print()
    if errors:
        print(f"{len(errors)} problem(s):")
        print("\n".join(f"  - {e}" for e in errors))
        sys.exit(1)
    print("All entries valid; every evidence quote was found on its page.")


if __name__ == "__main__":
    main()
