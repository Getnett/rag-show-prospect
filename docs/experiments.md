# Experiments log

Each row is one measured run. Numbers come only from runs that actually happened. A baseline comes first, then each change.
This log becomes the case study ("before → after").

Conventions:
- **Golden set:** state the version and size (e.g. `g20-v1`).
- **Hardware:** `mac` or `vm-a1` (2 OCPU / 12 GB arm64). Latency numbers on different hardware are not comparable.
- **Cost:** $ per answer, from provider token counts × the published price on that date.

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
