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
Labelled set `spikes/day2_route_set.json`: 44 pages, 34 native (body, screenshot-heavy, sparse, blank, two-column, table) and 10 needing OCR (real scan, synthetic scans light/medium/heavy, scan + typed header, scan + bad hidden OCR layer). Harness: `spikes/parse_compare.py`. OCR = Tesseract 5.5.4 CLI, eng, 300 dpi, no preprocessing.

| Date | Config | Hardware | Pages routed to OCR correctly | CER (3 pages) | s/page | Table cell accuracy | Notes |
|---|---|---|---|---|---|---|---|
| 2026-11-06 | **Baseline:** OCR if < 50 non-space chars | mac | 39/44; **2 scans missed** (typed header, bad hidden layer), 3 blank pages OCR'd needlessly | real scan **0.008**; light synthetic 0.12; medium synthetic 0.52–0.62 | median 1.7, max 4.2 (OCR pages) | 100% (pypdfium2 lines) / 100% (pdfplumber) | Heavy synthetic scans: CER ≈ 1.0 (5 chars out). Table fixture too easy to tell the extractors apart |
| 2026-11-09 | My v1: OCR if image covers > 90% of the page; text_quality placeholder | mac | **44/44**, 0 missed, 0 needless | (same OCR) | median 1.5 | (same) | Routing right. text_quality bugs (empty scored 1.0, digit check on the whole page, one +1 outside the loop) failed 39/44 pages incl. all clean ones; heavy scan scored 1.0 |
| 2026-11-09 | **Reference (ADR-016):** composition routing + token quality gate + page status | mac | **44/44**, 0 missed, 0 needless | real 0.008; light 0.12; medium 0.52–0.62 → **Failed** | median 1.5, max 3.7 | (same) | Failed = exactly the 5 pages with CER ≥ 0.5; 0 clean pages failed; 3 blank pages skipped. Margin thin: worst readable 0.65 vs best unreadable 0.46 (tuned on these 10 pages) |

Threshold sweep for the baseline rule (routing only), showing the trade-off measured:

| N (OCR if < N chars) | Correct | Missed scans | Needless OCR |
|---|---|---|---|
| 20 | 39/44 | 2 | 3 |
| 50 | 39/44 | 2 | 3 |
| 100 | 27/44 | 2 | 15 |
| 300 | 26/44 | 1 | 17 |
| 1000 | 25/44 | 1 | 18 |
| 2000 | 14/44 | 0 | 30 |

Quality signals vs CER on the 10 pages with ground truth (Tesseract output): noise-fragment share is the best separator. Readable pages (CER ≤ 0.12) have ≤ 14% noise; unreadable pages (CER ≥ 0.52) have ≥ 21%. Common-word share overlaps more (0.22 unreadable vs 0.27 readable), so noise is weighted 1.5× and the common-word damping only starts below 5% (the table page has 6%).

Break-it on synthetic pages (reference routing): brochure with a full-page background + real text → native (my v1: OCR, which would throw away good text); scan + hidden OCR layer → OCR; scan + visible glued layer → OCR (quality 0.0); full-page screenshot → OCR.

Checked: the high CER on synthetic scans is real OCR failure, not reading order (word recall 0.29 on `synthetic_scan.pdf`, 0.17 on a medium page, 0.91 on a light page). The salt-and-pepper noise is harsher than a real phone scan.

## Chunking × embeddings (Day 3)
| Date | Chunker | Embedder | Golden set | recall@5 | MRR@10 | Embed s / 1k chunks | Cost | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-11-13 | fixed_512 (no overlap) | bge-small | g20-v1 (14 scored) | 0.50 | 0.45 | 66.5 | $0 | 941 chunks; 74% at bge's 512-token limit (cut) |
| 2026-11-13 | llamaindex default (1024/200) | bge-small | g20-v1 (14) | 0.57 | 0.48 | 68.9 | $0 | 619 chunks; 90% cut at 512 tokens: the model never sees the second half |
| 2026-11-13 | fixed_512 | bge-base | g20-v1 (14) | 0.50 | 0.41 | 201.7 | $0 | 3x slower, no recall gain |
| 2026-11-13 | llamaindex default | bge-base | g20-v1 (14) | 0.57 | 0.52 | 218.5 | $0 | 3x slower, same recall |
| 2026-11-16 | heading_aware (400 tok, path on top) | bge-small | g20-v1 (14) | 0.57 | 0.52 | 49.2 | $0 | 3405 chunks, median 114 tok, 0% cut; direct 1.00, multi_chunk 0.00 |
| 2026-11-16 | heading_aware | bge-base | g20-v1 (14) | 0.57 | 0.51 | 158.4 | $0 | same questions found as bge-small |
| 2026-11-16 | fixed_512 | openai-3-small | g20-v1 (14) | **0.71** | **0.57** | 15.9 (API) | ~$0.009 | 0% cut (8,191-token limit); table 0.67 |
| 2026-11-16 | llamaindex default | openai-3-small | g20-v1 (14) | 0.64 | 0.53 | 10.6 (API) | ~$0.011 | no truncation now: +0.07 vs bge |
| 2026-11-16 | heading_aware | openai-3-small | g20-v1 (14) | 0.57 | 0.52 | 6.4 (API) | ~$0.010 | multi_chunk 0.00 again; q09 scan at rank 7 |

Setup: Mac (Apple Silicon, CPU), fastembed, cosine top-10, scoring by evidence text (a chunk containing a source's quote is a hit, any file). follow_up searched raw (no rewrite). Command: `uv run spikes/retrieval_eval.py -c fixed_512 llamaindex -e bge-small bge-base`.

**Per category (recall@5, all 4 setups):** direct 0.75, scanned 1.00 (duplicate clean copies count, see q08/q09 notes), multi_chunk 0.33, table 0.33, follow_up 0.00 (fixed) / 0.50 (llamaindex: q20 found, q19 never).

**Misses in every setup:** q02 (upload size: a generic 'Large file uploads' page wins), q06 (file actions: spread over 4 pages), q07 (databases: the release-notes chunk wins over the requirements list), q10 (notification interval: one row of a 55-row config table), q19 ('Could it be set to expired?': no subject to search for).

**Findings:**
- The embedder isn't the bottleneck: bge-base is 3x slower and finds the same questions. The chunks are.
- Silent truncation: bge reads 512 tokens. LlamaIndex's default 1024-token chunks lose their second half without any error; even 512 OpenAI tokens exceed 512 BGE tokens in 74% of chunks.
- Abstain preview (Day 5): top-1 similarity can't separate answerable from unanswerable on its own. q14 'Is Nextcloud free?' scores 0.79 (bge-small) vs answerable median 0.73. Out-of-scope (q15 0.43, q16 0.58) separates; near-domain unanswerables (q03, q04, q14) don't.
- heading_aware (2026-11-16): same recall@5 as LlamaIndex, different profile. Gains: q02 and q20 found (q20's list spans pages 64-65 and is now one chunk under 'Public link shares'), direct 1.00, nothing cut by the model. Losses: multi_chunk 0.00, because small chunks (median 114 tokens) put each half of a two-part answer in a different chunk. q07's top chunk (admin p113, 'The following databases are currently supported') is a correct answer missing from the golden set: a golden-set gap, not a retrieval miss.
- OpenAI text-embedding-3-small (2026-11-16, ~$0.03 total): the only change that moved recall: fixed_512 0.50 -> 0.71, llamaindex 0.57 -> 0.64, heading_aware flat at 0.57. With 14 scored questions, one question = 0.07, so 0.71 vs 0.57 is 2 questions: a direction, not proof. Bigger chunks gain most, likely because OpenAI reads all of each chunk (no 512-token cut).
- Abstain preview with OpenAI: clearer gap. heading_aware: answerable median 0.62, out-of-scope 0.15-0.25, but near-domain unanswerables still close (q14 0.58, q04 0.46). Similarity alone still won't decide 'I don't know'.
- Harness bug found and fixed first: the line-break hyphen arrives as U+0002 when PDF text is read char by char (F22 extended). Before the fix, quotes across hyphenated words could never match.


## Retrieval (Day 4)
| Date | Retriever | Reranker | Golden set | recall@5 | MRR@10 | Rerank p50 / p95 (20 / 50 passages) | Hardware | Notes |
|---|---|---|---|---|---|---|---|---|

## Generation, citations, abstain (Day 5)
| Date | Model | Prompt version | Golden set | Faithfulness | Abstain P / R | TTFT p50 / p95 | $ / answer | Notes |
|---|---|---|---|---|---|---|---|---|

## Break-it drills (Day 6)
| Date | Attack / fault | Before | After | Mitigation | Notes |
|---|---|---|---|---|---|
