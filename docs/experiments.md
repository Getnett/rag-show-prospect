# Experiments log

Each row is one measured run. Numbers come only from runs that actually happened. A baseline comes first, then each change.
This log becomes the case study ("before → after").

Conventions:
- **Golden set:** state the version and size (e.g. `g20-v1`).
- **Hardware:** `mac` or `vm-aws` (AWS t3.small, 2 vCPU / 2 GB x86, burstable) or `vm-aws-m7i` (m7i-flex.large, 8 GB, when resized for ingestion). Latency numbers on different hardware are not comparable.
- **Cost:** $ per answer, from provider token counts × the published price on that date.

## Corpus and naive parse (Day 1)
Corpus (2026-11-05, `spikes/corpus_stats.py`, native text via pypdfium2, tokens ≈ chars / 4):

| Source | MB | Pages | ~Tokens |
|---|---|---|---|
| Nextcloud v35 User + Admin manuals (PDF) | 47.3 | 1,037 | 389,553 |
| Nextcloud v33 User + Admin manuals (PDF) | 43.2 | 875 | 316,074 |
| 99 HTML pages under `/server/stable/` (robots.txt allows only this path) | 2.7 | 99 | 104,529 |
| Messy PDFs (excl. oversized) | 0.7 | 6 | 3,743 |
| **Total excl. oversized** | **93.9** | **2,017** | **~814k** |

At $0.02/M tokens, embedding the whole corpus once with `text-embedding-3-small` would cost ≈ $0.02 (estimate, not run).

Naive parser = `pypdf` `extract_text()` with no checks (`spikes/naive_parse.py`, hardware `mac`, timeout 120 s):

| Date | File | Outcome | Chars/page | Seconds | Peak RSS MB | Notes |
|---|---|---|---|---|---|---|
| 2026-11-05 | password_user.pdf | **error** (`FileNotDecryptedError`) | – | 0.0 | 37 | Loud failure, the safe case |
| 2026-11-05 | password_owner_only.pdf | ok | 3,552 | 0.01 | 37 | Permissions-only password: opens without one |
| 2026-11-05 | oversized.pdf (2,050 pages, 116.5 MB) | ok | 1,415 | 2.24 | 284 | No hang on the Mac. RSS 284 MB for *one* file matters on a 2 GB VM |
| 2026-11-05 | synthetic_scan.pdf (image-only page) | **empty**, no error | 0 | 0.0 | 36 | Silent failure: would be marked "Indexed" with 0 chunks |
| 2026-11-05 | scanned-nextcloud-user-manual.pdf (real scan, v35 p. 13) | **empty**, no error | 0 | 0.0 | 35 | Same silent failure on a real scan; truth text saved for Day 2 CER |
| 2026-11-05 | v35_user_manual.pdf (clean) | **glued words** | 791 | 2.0 | 144 | 113 of 333 pages have >5% glued tokens ("Listmessagesinatalkconversation") |
| 2026-11-05 | two_column.pdf / table_heavy.pdf | ok | – | 0.0 | 35 | Reading order and table cells are judged on Day 2, not here |

pypdf vs pypdfium2 on the v35 User manual body pages (20–333): word-like tokens 63% vs 88%; glued tokens 4.37% vs 0.00%; tokens found 17,472 vs 44,571. **pypdfium2 confirmed as the native extractor (ADR-006).**
Also found: plain `pip install pypdf` can't open AES-encrypted PDFs at all (`DependencyError`); it needs `pypdf[crypto]`.

## Parsing and OCR (Day 2)
| Date | Config | Hardware | Pages routed to OCR correctly | CER (3 pages) | s/page | Table cell accuracy | Notes |
|---|---|---|---|---|---|---|---|

## Chunking × embeddings (Day 3)
| Date | Chunker | Embedder | Golden set | recall@5 | MRR@10 | Embed s / 1k chunks | Cost | Notes |
|---|---|---|---|---|---|---|---|---|

## Retrieval (Day 4)
| Date | Retriever | Reranker | Golden set | recall@5 | MRR@10 | Rerank p50 / p95 (20 / 50 passages) | Hardware | Notes |
|---|---|---|---|---|---|---|---|---|

## Generation, citations, abstain (Day 5)
| Date | Model | Prompt version | Golden set | Faithfulness | Abstain P / R | TTFT p50 / p95 | $ / answer | Notes |
|---|---|---|---|---|---|---|---|---|

## Break-it drills (Day 6)
| Date | Attack / fault | Before | After | Mitigation | Notes |
|---|---|---|---|---|---|
