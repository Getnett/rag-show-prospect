# ADR-017: Heading-aware chunks with OpenAI text-embedding-3-small
- **Status:** Accepted for Day 4 (Week 0). Revisit after Day 4 retrieval and again on the 60-question golden set (build week 1).
- **Date:** 2026-11-16

## Context
Day 3 measured 3 chunkers × 3 embedders on golden set g20-v1 (14 questions with sources), scoring recall@5 and MRR@10 by evidence text (`spikes/retrieval_eval.py`, numbers in `docs/experiments.md`).

| Chunker | bge-small (local) | bge-base (local) | OpenAI 3-small |
|---|---|---|---|
| fixed_512 (no overlap) | 0.50 | 0.50 | 0.71 |
| LlamaIndex default (1024/200) | 0.57 | 0.57 | 0.64 |
| heading_aware (≤ 400 tokens, heading path on top) | 0.57 | 0.57 | 0.57 |

What the numbers say:
- **The bigger local model gives nothing.** bge-base is 3× slower than bge-small and finds the same questions in every setup.
- **bge cuts input at 512 tokens, silently.** 90% of LlamaIndex default chunks and 74% of fixed_512 chunks lose their tail (F24). OpenAI reads 8,191 tokens.
- **OpenAI is the only change that raised recall.** But one question is worth 0.07, so 0.71 vs 0.57 is **2 questions**: a direction, not proof.
- **heading_aware fixes what it was built for.** A list spread over pages 64–65 is one chunk under its heading (q20). Every direct question is found. No chunk is cut. It **loses** multi-part answers (multi_chunk 0.00): small chunks (median ~110 tokens) put each part in a different chunk, and both rarely make the top 5.

## Options
1. **heading_aware + OpenAI**
2. fixed_512 + OpenAI (best today, by 2 questions)
3. heading_aware + bge-small (free, local; same recall as option 1 today)

## Decision
Option 1 for the Day 4 retrieval work.
- **Structure is worth more than 2 questions on a 14-question set.**
  - A chunk = one section with a heading path, so citations say "5.3.1 File sharing > Public link shares, p. 64–65" instead of an arbitrary 512-token window.
  - The admin's "view source passage" shows a coherent section.
  - Section boundaries are where documents change, so re-ingesting a changed section touches few chunks.
- **Day 4's additions favour small, focused chunks.** Keyword search (exact terms like `notificationRefreshInterval`) and a reranker read short passages better.
- **Multi-part answers get a targeted fix**, not bigger chunks: fetch the neighbouring chunks of the same section (small-to-big expansion) and measure it on Day 4.
- **Embedder: OpenAI text-embedding-3-small.**
  - Cost: ~$0.01 to embed the whole corpus ($0.02/M tokens). Queries cost a negligible amount.
  - Visitor questions already go to OpenAI for generation (ADR-005), so this adds no new privacy exposure.
  - bge-small stays as the **offline fallback**, and as the free choice for CI's retrieval tier if API cost or availability becomes a problem.

## Trade-offs and risks
- **Not proven yet.** Fixed_512 leads by 2 questions. If heading_aware + hybrid + rerank is still behind after Day 4, switch. The rule is written now so we can't move the goalposts later.
- **A paid dependency in ingestion.** Every re-ingest calls the API. Mitigations:
  - cache embeddings by chunk-text hash, so only changed chunks are re-embedded;
  - record model and dimension per index version, because mixing embedders breaks search (F12);
  - fall back to bge-small with a full re-index if the API is unavailable.
- **The PDF heading rules are tuned on Sphinx manuals** (font size + bold). Other clients' PDFs may only use bold or numbering. Running header and footer detection is learned per document (lines repeating on ≥ 5 pages), which carries over better. Unknown layouts fall back to size-limited pieces with no heading path, which is no worse than fixed_512.
- **Small eval set:** 14 scored questions. All conclusions are re-checked on the 60-question set.

## Follow-ups
- Day 4: hybrid (FTS + vector, RRF) and rerank on these chunks; add neighbour expansion for multi_chunk.
- Golden set: q07 needs admin p.113 as a second source; its "miss" is a correct answer (a golden-set gap).
- Build week 1: port `heading_aware` and the hidden-character stripping (F22) into the ingestion worker, with unit tests on pages 55 and 64–65.
