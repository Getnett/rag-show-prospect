# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30", "pyyaml>=6.0", "tiktoken", "numpy", "fastembed>=0.4",
#                 "llama-index-core>=0.12", "openai>=1.40"]
# ///
"""Day 3: retrieval-only eval. For each chunker x embedder, embed the whole corpus, run the golden questions,
score recall@5 and MRR@10 per category. No LLM involved.

Usage:
  uv run spikes/retrieval_eval.py                                  # fixed_512 + llamaindex, bge-small
  uv run spikes/retrieval_eval.py -c heading_aware -e bge-small bge-base
  uv run spikes/retrieval_eval.py -e openai-3-small --paid-ok      # PAID: prints a cost estimate first
  uv run spikes/retrieval_eval.py --show-misses                    # list each missed question + its top chunk

SCORING (by evidence text, decided 2026-11-13):
  A retrieved chunk is a HIT for a question if its normalized text contains a source's evidence quote,
  whichever file it came from (so duplicate copies in HTML/PDF count). multi_chunk (need_all) questions
  need every source's evidence covered somewhere in the top k.
  recall@5 = share of answerable questions with a hit in the top 5.
  MRR@10   = mean of 1/rank of the first hit in the top 10 (0 if none). For need_all: the rank at which the
             last piece is covered.
  Questions without sources (unanswerable, out_of_scope, injection) are not scored for recall. We log their
  top-1 similarity instead: Day 5 uses the gap vs answerable questions to set the "I don't know" threshold.
  follow_up questions are searched RAW (no rewriting yet), on purpose: that's the baseline query rewriting must beat.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from chunkers import CHUNKERS, Chunk  # noqa: E402
from corpus import ROOT, normalize  # noqa: E402
from doc_lines import all_docs  # noqa: E402

OUT = ROOT / "spikes" / "out"
EMB_CACHE = OUT / "emb"
GOLDEN = ROOT / "eval" / "golden" / "g20-v1.yaml"

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBEDDERS = {
    # name: (provider, model id, max input tokens, query prefix)
    "bge-small": ("fastembed", "BAAI/bge-small-en-v1.5", 512, BGE_QUERY_PREFIX),
    "bge-base": ("fastembed", "BAAI/bge-base-en-v1.5", 512, BGE_QUERY_PREFIX),
    "openai-3-small": ("openai", "text-embedding-3-small", 8191, ""),
}
OPENAI_USD_PER_M_TOKENS = 0.02  # text-embedding-3-small, verified 2026-11-04 (docs/week0-plan.md)


# ---------- embedding ----------

class Embedder:
    def __init__(self, name: str, paid_ok: bool) -> None:
        self.name = name
        self.provider, self.model, self.max_tokens, self.prefix = EMBEDDERS[name]
        if self.provider == "fastembed":
            from fastembed import TextEmbedding
            self._m = TextEmbedding(self.model, cache_dir=str(OUT / "models"))  # survives reboots; git-ignored
            self._tok = self._m.model.tokenizer  # the model's own tokenizer (WordPiece for BGE)
        else:
            if not paid_ok:
                sys.exit(f"{name} is a PAID API. Re-run with --paid-ok after approving the estimate.")
            from openai import OpenAI
            self._client = OpenAI(api_key=_env("OPENAI_API_KEY"))

    def count_tokens(self, text: str) -> int:
        if self.provider == "fastembed":
            enc = self._tok.encode(text)  # fastembed's tokenizer truncates; we detect "at the limit"
            return len(enc.ids)
        from chunkers import n_tokens
        return n_tokens(text)

    def embed(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if is_query and self.prefix:
            texts = [self.prefix + t for t in texts]
        if self.provider == "fastembed":
            vecs = np.array(list(self._m.embed(texts, batch_size=32)))
        else:
            vecs = []
            for i in range(0, len(texts), 256):
                r = self._client.embeddings.create(model=self.model, input=texts[i: i + 256])
                vecs += [d.embedding for d in r.data]
            vecs = np.array(vecs)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def _env(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key]
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit(f"{key} not set (environment or .env)")


def embed_chunks(emb: Embedder, chunker: str, chunks: list[Chunk]) -> tuple[np.ndarray, float]:
    """Embeddings for all chunks, cached on disk by (chunker, model, chunk texts). Returns (vectors, seconds)."""
    h = hashlib.sha256("\x00".join(c.text for c in chunks).encode()).hexdigest()[:16]
    path = EMB_CACHE / f"{chunker}__{emb.name}__{h}.npy"
    meta = path.with_suffix(".json")
    if path.exists() and meta.exists():
        return np.load(path), json.loads(meta.read_text())["seconds"]
    t0 = time.perf_counter()
    vecs = emb.embed([c.text for c in chunks])
    secs = time.perf_counter() - t0
    EMB_CACHE.mkdir(parents=True, exist_ok=True)
    np.save(path, vecs)
    meta.write_text(json.dumps({"seconds": secs, "n": len(chunks)}))
    return vecs, secs


# ---------- scoring ----------

def evidence_hits(q: dict, chunk_text: str) -> set[int]:
    """Indexes of the question's sources whose evidence quote appears in this chunk."""
    norm = normalize(chunk_text)
    return {i for i, s in enumerate(q.get("sources") or []) if normalize(s["evidence"]) in norm}


def score_question(q: dict, ranked: list[Chunk], k_recall: int = 5, k_mrr: int = 10) -> tuple[bool, float, int | None]:
    """(hit in top k_recall, reciprocal rank within k_mrr, rank of first/complete hit or None)."""
    need = set(range(len(q["sources"]))) if q.get("need_all") else None
    covered: set[int] = set()
    rank = None
    for r, c in enumerate(ranked[:k_mrr], start=1):
        hits = evidence_hits(q, c.text)
        if not hits:
            continue
        covered |= hits
        if need is None or covered >= need:
            rank = r
            break
    return (rank is not None and rank <= k_recall), (1 / rank if rank else 0.0), rank


def run(chunker: str, emb: Embedder, questions: list[dict], show_misses: bool) -> dict:
    t0 = time.perf_counter()
    chunks: list[Chunk] = []
    for file, lines in all_docs().items():
        chunks += CHUNKERS[chunker](file, lines)
    chunk_secs = time.perf_counter() - t0

    vecs, embed_secs = embed_chunks(emb, chunker, chunks)
    sizes = [emb.count_tokens(c.text) for c in chunks]
    truncated = sum(s >= emb.max_tokens for s in sizes)

    qvecs = emb.embed([q["question"] for q in questions], is_query=True)
    sims = qvecs @ vecs.T

    per_cat: dict[str, list[tuple[bool, float]]] = defaultdict(list)
    top1_answerable, top1_none, misses = [], [], []
    for qi, q in enumerate(questions):
        order = np.argsort(-sims[qi])[:10]
        ranked = [chunks[i] for i in order]
        top1 = float(sims[qi][order[0]])
        if not q.get("sources"):
            top1_none.append((q["id"], q["category"], top1))
            continue
        hit, rr, rank = score_question(q, ranked)
        per_cat[q["category"]].append((hit, rr))
        top1_answerable.append(top1)
        if not hit:
            misses.append((q, ranked[0], rank))

    rows = {cat: (sum(h for h, _ in v) / len(v), sum(r for _, r in v) / len(v), len(v)) for cat, v in per_cat.items()}
    all_scored = [x for v in per_cat.values() for x in v]
    result = {
        "chunker": chunker, "embedder": emb.name, "chunks": len(chunks),
        "median_tokens": statistics.median(sizes), "truncated": truncated,
        "chunk_secs": chunk_secs, "embed_secs": embed_secs,
        "secs_per_1k": embed_secs / len(chunks) * 1000,
        "recall5": sum(h for h, _ in all_scored) / len(all_scored),
        "mrr10": sum(r for _, r in all_scored) / len(all_scored),
        "n": len(all_scored), "per_cat": rows,
        "top1_answerable_median": statistics.median(top1_answerable),
        "top1_none": top1_none, "misses": [(q["id"], q["category"], rank) for q, _, rank in misses],
    }
    if show_misses:
        print(f"\n### Misses: {chunker} x {emb.name}")
        for q, top, rank in misses:
            where = f"rank {rank}" if rank else "not in top 10"
            print(f"- {q['id']} ({q['category']}, {where}): {q['question']!r}\n"
                  f"    top chunk: {top.file.split('/')[-1]} p{top.pages}: {' '.join(top.text.split())[:140]!r}")
    return result


def print_tables(results: list[dict]) -> None:
    print("\n| Chunker | Embedder | Chunks | Median tok | Truncated | recall@5 | MRR@10 | Embed s/1k chunks |")
    print("|---|---|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['chunker']} | {r['embedder']} | {r['chunks']} | {r['median_tokens']:.0f} | "
              f"{r['truncated']} ({r['truncated'] / r['chunks']:.0%}) | {r['recall5']:.2f} | {r['mrr10']:.2f} | "
              f"{r['secs_per_1k']:.1f} |")
    cats = sorted({c for r in results for c in r["per_cat"]})
    print("\nrecall@5 per category (n questions):\n")
    print("| Chunker x Embedder | " + " | ".join(f"{c} ({results[0]['per_cat'].get(c, (0, 0, 0))[2]})" for c in cats) + " |")
    print("|---|" + "---|" * len(cats))
    for r in results:
        print(f"| {r['chunker']} x {r['embedder']} | " +
              " | ".join(f"{r['per_cat'][c][0]:.2f}" if c in r["per_cat"] else "-" for c in cats) + " |")
    print("\nTop-1 similarity: answerable median vs questions with no answer (Day 5 abstain threshold input):\n")
    for r in results:
        none = ", ".join(f"{qid} {s:.3f}" for qid, _, s in r["top1_none"])
        print(f"- {r['chunker']} x {r['embedder']}: answerable median {r['top1_answerable_median']:.3f} | {none}")
    print("\nMissed (id, category, rank or None):")
    for r in results:
        print(f"- {r['chunker']} x {r['embedder']}: {r['misses']}")


def paid_estimate(chunkers: list[str]) -> None:
    from chunkers import n_tokens
    for ch in chunkers:
        toks = sum(n_tokens(c.text) for f, ls in all_docs().items() for c in CHUNKERS[ch](f, ls))
        print(f"{ch}: {toks:,} tokens -> ${toks / 1e6 * OPENAI_USD_PER_M_TOKENS:.4f} with text-embedding-3-small")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--chunkers", nargs="+", default=["fixed_512", "llamaindex"], choices=list(CHUNKERS))
    ap.add_argument("-e", "--embedders", nargs="+", default=["bge-small"], choices=list(EMBEDDERS))
    ap.add_argument("--paid-ok", action="store_true", help="allow the paid OpenAI embedder")
    ap.add_argument("--estimate", action="store_true", help="print the OpenAI cost estimate and exit")
    ap.add_argument("--show-misses", action="store_true")
    ap.add_argument("--golden", default=str(GOLDEN))
    args = ap.parse_args()

    if args.estimate:
        return paid_estimate(args.chunkers)
    questions = yaml.safe_load(Path(args.golden).read_text())["questions"]
    results = []
    for e in args.embedders:
        emb = Embedder(e, args.paid_ok)
        for c in args.chunkers:
            print(f"running {c} x {e} ...", flush=True)
            results.append(run(c, emb, questions, args.show_misses))
    print_tables(results)
    OUT.mkdir(exist_ok=True)
    (OUT / "day3_results.json").write_text(json.dumps(results, indent=1, default=str))


if __name__ == "__main__":
    main()
