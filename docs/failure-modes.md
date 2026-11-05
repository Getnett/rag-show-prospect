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
| F19 | Demo address unreachable (added 2026-11-05) | Prospect's link times out or shows a certificate error | External uptime check on the public URL; DuckDNS updater exit code logged on boot; Caddy certificate errors in logs | Updater runs before Caddy on boot; Caddy keeps certs on a persistent volume; fallback A record on my Vercel domain (~10 min) | Stop/start the instance and confirm the name follows the new IP and HTTPS still works | planned |
| F20 | Extractor drops word spaces (added 2026-11-05, found on Day 1) | Native text is "Listmessagesinatalkconversation": keyword search misses, embeddings degrade, on a *clean* PDF | Per-page glued-token share (letters-only tokens ≥ 25 chars) above a threshold | Use pypdfium2 for native text (0% glued vs 4.4% with pypdf); flag pages above the threshold | `spikes/naive_parse.py` glued % column; Day 2 per-page check | planned |

## Drill log
Record each deliberate trigger: date, what we did, what we saw, what changed.

| Date | Failure | What we did | What we observed | Change made |
|---|---|---|---|---|
| 2026-11-05 | F06, F03 | Fed password, owner-only, 2,050-page/116 MB and image-only PDFs to naive pypdf | Password → loud error; owner-only → opens fine; oversized → no hang on the Mac, 284 MB RSS, 2.2 s; scan → **empty text, no error** | Day 2: route near-empty pages to OCR; empty after OCR = Failed with a reason; size and page caps before parsing |
| 2026-11-05 | F20 | Measured pypdf vs pypdfium2 on the clean v35 User manual | pypdf glued words on 113/333 pages; pypdfium2 0% glued | Native extraction = pypdfium2; F20 added |
| 2026-11-05 | F05, F13 | Crawled 100 pages of `/server/stable/` | `.../en/` and `.../en/index.html` are the same page under two URLs (100 fetches → 99 files) | Crawler must normalize `/` ↔ `/index.html` and dedupe on content hash |
