# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30"]
# ///
"""Find which corpus pages contain a phrase, to fill in `sources` in the golden set.

Usage:
  uv run spikes/find_page.py "group folders"          # every page containing the phrase (case-insensitive)
  uv run spikes/find_page.py "group folders" --all    # show more than 15 hits

Also use it to prove an "unanswerable" question really has no answer: search its key terms and expect 0 hits.
Page numbers are PDF viewer pages (1-based). HTML files count as one page.
"""

from __future__ import annotations

import argparse

from corpus import all_pages, normalize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phrase")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    needle = normalize(args.phrase)
    hits = []
    for file, texts in all_pages().items():
        for i, text in enumerate(texts):
            norm = normalize(text)
            pos = norm.find(needle)
            if pos >= 0:
                hits.append((file, i + 1, norm.count(needle), norm[max(0, pos - 80): pos + len(needle) + 80]))
    print(f'{len(hits)} page(s) contain "{args.phrase}"\n')
    for file, page, n, snippet in hits if args.all else hits[:15]:
        where = file if file.endswith(".html") else f"{file}  page {page}"
        print(f"{where}  ({n}x)\n    ...{snippet}...\n")
    if len(hits) > 15 and not args.all:
        print(f"(+{len(hits) - 15} more; use --all)")


if __name__ == "__main__":
    main()
