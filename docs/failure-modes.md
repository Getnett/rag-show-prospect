# Failure-mode register

A living register. Each entry lists the symptom, how we detect it, the mitigation and **the test that proves it**.
Status: `planned` (designed, not tested) → `tested` (a test exists and passes) → `drilled` (triggered on purpose, with the result recorded).

Seeded from CLAUDE.md §6E on 2026-11-04. Detection and mitigation are **plans** until a test is linked.

| # | Failure | Symptom | Detection (planned) | Mitigation (planned) | Proving test | Status |
|---|---|---|---|---|---|---|
| F01 | Empty retrieval | Bot answers anyway or rambles | Top retrieval/rerank score below threshold; zero hits after fusion | Abstain band: "not in our docs" plus escalation card | — | planned |
| F02 | Conflicting or stale docs | Answer mixes Nextcloud v33 and v35 behavior | Retrieved chunks from different doc versions or dates disagree | Version metadata on chunks, prefer newest, flag conflict in the answer and the admin log | — | planned |
| F03 | OCR garbage | Nonsense text indexed; wrong or empty answers about scanned pages | Garbage ratio / dictionary-word ratio per page; OCR confidence | Skip or flag low-quality pages; show "Failed: unreadable scan" per page | — | planned |
| F04 | Table misparse | Numbers attached to the wrong row or column | Table-cell spot check in the golden set (table category) | pdfplumber table extraction to row-wise text; keep tables as whole chunks | — | planned |
| F05 | Duplicate chunks | Same passage cited twice; skewed ranking | Content hash collisions at ingest | Content-hash dedupe; re-ingest only changed content | — | planned |
| F06 | Huge or password-protected files | Worker hangs, runs out of memory or crashes | Size and page limits before parsing; encryption check | Reject with a human-readable error; per-document failure isolation | — | planned |
| F07 | Prompt injection in a document | Bot follows instructions planted in a doc | Injection cases in the golden set; output policy checks | Context marked as untrusted data; instruction hierarchy; no tools or actions from context | — | planned |
| F08 | User-side injection | Visitor makes the bot drop its rules or leak the system prompt | Adversarial golden questions | System prompt boundaries; refuse off-scope requests; nothing secret in the prompt | — | planned |
| F09 | PII leak | Emails or phone numbers stored in logs, traces or exports | Regex scan of stored transcripts and exported traces in tests | Redact **before** saving or exporting; retention purge | — | planned |
| F10 | Runaway cost | Spend climbs from abuse or loops | Per-answer cost ledger; daily total vs cap | Hard daily and total cap → sources-only mode; per-visitor rate limits; OpenAI dashboard hard limit | — | planned |
| F11 | LLM timeout or quota exhaustion | Chat hangs or errors | Timeouts; 429/5xx counters; circuit breaker state | Retry with backoff → fallback provider → sources-only mode | — | planned |
| F12 | Embedding-model change causes index drift | Recall collapses after a model swap | Each index version records model and dimension; query vs index mismatch check | Versioned index; re-embed into a new version, then switch atomically | — | planned |
| F13 | Crawler traps and robots rules | Infinite URL space; crawling disallowed pages; SSRF | Page/depth caps hit; robots.txt check; IP allow/deny check | Max pages/depth, URL normalization, robots respect, block internal/metadata IPs incl. after redirects | — | planned |
| F14 | Worker crash mid-ingest | Document stuck in "Indexing"; half-indexed doc visible | Expired job lease; heartbeat gap | Lease reclaim; idempotent steps; atomic index-version switch | — | planned |
| F15 | Widget offline / API down | Blank widget or endless typing dots | Health check from the loader; request timeout | Friendly offline state with email fallback; launcher still renders | — | planned |
| F16 | Admin-claim race (added) | A stranger or a second request becomes admin | Concurrent-claim test | One-time setup token, claimed atomically in one transaction | — | planned |
| F17 | Free-tier training on chats (added) | Visitor data sent to a provider that trains on it | Config check: real-chat provider must be on an allowlist of non-training providers | Paid, non-training provider for real chats; free tiers only in dev | — | planned |
| F18 | Out of memory on the 2 GB VM (added 2026-11-05) | Containers killed (OOMKilled), 502s from Caddy, ingestion jobs restart in a loop | `docker inspect` OOMKilled flag, container restart count, host memory/swap metrics and alerts | Per-service `mem_limit`, 4 GB swap, one worker, OCR one page at a time, models loaded once; job lease expiry re-queues the killed job; resize to m7i-flex.large for big imports | Day 7: ingest a large PDF while chatting, record peak RSS | planned |

## Drill log
Record each deliberate trigger: date, what we did, what we saw, what changed.

| Date | Failure | What we did | What we observed | Change made |
|---|---|---|---|---|
