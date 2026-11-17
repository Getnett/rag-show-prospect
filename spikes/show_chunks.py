# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30", "pyyaml>=6.0", "tiktoken", "llama-index-core>=0.12"]
# ///
"""Inspect a chunker without embeddings (works offline once packages are installed).

  uv run spikes/show_chunks.py heading_aware                                        # corpus stats + evidence check
  uv run spikes/show_chunks.py heading_aware data/raw/pdf/v35_user_manual.pdf 64 65  # print chunks on those pages

Evidence check: for every golden source, is its evidence quote INSIDE at least one chunk (any file)?
A quote cut by a chunk boundary can never be retrieved as a hit, whatever the embedder. That's the ceiling
for recall: no embedding model can fix a bad cut.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from chunkers import CHUNKERS, n_tokens  # noqa: E402
from corpus import ROOT, normalize  # noqa: E402
from doc_lines import all_docs  # noqa: E402


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "heading_aware"
    chunk = CHUNKERS[name]
    docs = all_docs()
    if len(sys.argv) > 2:
        file, pages = sys.argv[2], {int(p) for p in sys.argv[3:]} or {1}
        for c in chunk(file, docs[file]):
            if pages & set(c.pages):
                print(f"=== pages {c.pages} | {n_tokens(c.text)} tokens | heading: {c.heading!r}")
                print(c.text, "\n")
        return

    chunks = [c for f, ls in docs.items() for c in chunk(f, ls)]
    sizes = [n_tokens(c.text) for c in chunks]
    print(f"{name}: {len(chunks)} chunks | tokens median {statistics.median(sizes):.0f}, "
          f"max {max(sizes)} | over 512: {sum(s > 512 for s in sizes)} | under 20: {sum(s < 20 for s in sizes)}")
    print(f"with a heading: {sum(bool(c.heading) for c in chunks) / len(chunks):.0%}")

    norm = [normalize(c.text) for c in chunks]
    golden = yaml.safe_load((ROOT / "eval" / "golden" / "g20-v1.yaml").read_text())["questions"]
    total = intact = 0
    for q in golden:
        for s in q.get("sources") or []:
            total += 1
            ev = normalize(s["evidence"])
            if any(ev in t for t in norm):
                intact += 1
            else:
                print(f"  CUT: {q['id']} {s['file'].split('/')[-1]} p{s.get('page', 1)}: {s['evidence'][:60]!r}")
    print(f"evidence quotes intact in some chunk: {intact}/{total}")


if __name__ == "__main__":
    main()
