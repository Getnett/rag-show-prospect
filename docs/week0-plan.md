# AI Support Knowledge Hub: pre-build plan and Week 0 curriculum

## Context
This is a freelance portfolio piece: a production-grade RAG support chatbot platform, built in mentor mode (spec in `~/Desktop/CLAUDE.md`).

You are the single admin. You ingest an openly licensed knowledge base and publish a demo website with the chat widget. Prospects chat with it and see the admin via screen-share or video.

This plan answers CLAUDE.md §11: understanding, top 5 risks, the Week 0 curriculum, and verified free options. It also records every decision settled in the grilling session (Q1–Q29).

**No platform code is written in Week 0.**

---

## 1. Understanding (restated)
1. **Product:** one company per installation. The admin manages sources, ingestion, conversations, evals and widget settings. Visitors chat through an embeddable widget.
2. **What matters most:** grounded answers with verified citations, honest abstain/escalation, measured evals, reliability, cost caps and security. P0 is never cut. P2 is cut first.
3. **The demo:** the Nextcloud User and Admin manuals, website pages plus PDFs. Verified: **CC BY 3.0**, with PDFs for many versions. You add 4–5 deliberately messy PDFs on top.
   - **Bonus:** old and new manual versions conflict, which gives us a real "stale/conflicting docs" test.
4. **Mockup ambiguities resolved:**
   - The "chat with a human" text becomes an email follow-up.
   - "Usually replies in a few minutes" becomes "AI assistant · answers from our docs".
   - One tick means sent; there are no read ticks.
   - "Indexed" means a document count.
   - Latency is shown as time-to-first-token (TTFT) p50/p95.
   - Only the source types we build are listed. There is no Team page.
5. **Contradictions in the brief that we fixed:**
   - "First signup claims admin" is unsafe on a public URL, so it becomes a **one-time setup link**.
   - The "widget key" can't be a secret, so it becomes a **public site ID** plus separate **secret API keys**.
   - Free LLM tiers that train on data contradict the "secure and private" footer, so **real chats go only to a paid, non-training provider**.
6. **Scale:** the mockup's numbers (2.42M, 78.6 GB) are illustrative. The README will state the real limits: one ingestion worker on a 2 vCPU / 2 GB server, with sizes to be measured.
7. **Roadmap, not this build:** prospect trials with their own documents (one private copy per prospect), self-serve multi-tenant SaaS, multiple admins, CSV/XLSX, the vision-LLM call, and self-hosted Prometheus/Grafana.

## 2. Decisions settled in grilling
| # | Decision |
|---|---|
| Q1 | **Week 0 plus 3 build weeks**, 6 days/week. Checkpoint at the end of build week 2: a shippable MVP |
| Q2/Q3 | Escalation is an email follow-up card. **Three confidence bands** (answer / answer plus card / abstain plus card), with thresholds tuned on the golden set |
| Q4 | The honesty fixes above |
| Q5 | Retrieval quality = latest golden-set eval (judge-labelled context precision, with recall@k and MRR on the Eval page). Answer quality = online judge on sampled real chats. Each card shows its source and sample size |
| Q6 | Two-tier CI. **Every push:** lint, types, tests and retrieval eval (no LLM). **PR to main, nightly or manual:** full generation plus judge eval with response caching |
| Q7 | Admin = **React + Vite SPA**, static files served by Caddy on the VM. All auth lives in FastAPI. Tailwind, shadcn/ui, Recharts, TanStack Query |
| Q8 | Widget = a vanilla loader `<script>` that opens an **iframe** from our domain. The iframe can also be embedded directly. Built with Preact and Vite |
| Q9 | **LlamaIndex for plumbing only**: loaders, provider connectors, and a baseline splitter to compare against. **You write:** retrieval SQL (FTS plus pgvector, RRF), rerank, abstain, citation verification and eval metrics. No PyMuPDF-based readers |
| Q10 | Hand-rolled Postgres job queue (SKIP LOCKED, lease and heartbeat, attempts with backoff, dead-letter) 🟥 |
| Q11/Q29 | One admin. Server-side sessions (HttpOnly, Secure, SameSite=Lax), argon2id, CSRF protection, login throttling, password reset by CLI. **One-time setup token**, claimed atomically; signup then closes |
| Q12/Q28 | Nextcloud corpus. Demo-only access for prospects; trials go on the roadmap |
| Q13 | Formats: PDF (native and OCR), TXT, MD, HTML, DOCX. CSV/XLSX and the vision-LLM call go on the roadmap; we keep only the interface and flag for the latter |
| Q14 | Monorepo: `api/ worker/ admin/ widget/ eval/ infra/ docs/ spikes/`. Tooling: uv, ruff, mypy, pytest, SQLAlchemy 2 plus Alembic, GitHub Actions. **Public repo from day 1** with gitleaks scanning |
| Q15 | Week 0 = Python scripts in `spikes/`, run on your Mac, with results in markdown |
| Q16 | ~~Oracle Always Free A1~~ (card rejected). **AWS Free plan, t4g.small (2 vCPU / 2 GB, arm64)**, slim setup; see ADR-014. Fallback: Cloudflare Tunnel from your Mac |
| Q17/Q18 | A subdomain of your own domain. Email via Resend free tier over port 587, behind a `Notifier` interface, plus an HMAC-signed webhook with retries (Discord in the demo) |
| Q19 | Free tiers in dev with synthetic or your own data only. Real chats go to a paid tier that doesn't train on data. Verified: the **OpenAI API doesn't train on API data by default** and keeps abuse logs ≤30 days. Primary and fallback models are chosen by a Day 5 bake-off |
| Q20 | Stream text with `[c3]` markers, verify citations after the stream, then send a final "verified" event that can downgrade the band |
| Q21 | LlamaIndex provider connectors **wrapped in your safety layer**: timeouts, retries, fallback and circuit breaker 🟥. No LiteLLM (two supply-chain compromises in 2026) |
| Q22 | PDF/OCR: pypdfium2, pdfplumber and Tesseract (all permissive licenses). Docling and RapidOCR are compared in Week 0 |
| Q23 | Embeddings: **local (fastembed) vs OpenAI `text-embedding-3-small`**, chosen on the numbers. Each index version records model and dimension. Avoid non-commercial models |
| Q24 | Hard daily and total spend caps. When hit, switch to **sources-only mode** (no LLM call). Never silently fall back to a free tier |
| Q25 | **OpenTelemetry → Grafana Cloud Free** (logs, metrics, traces, alerts) **plus Langfuse Cloud Hobby** (LLM traces). PII is redacted before export. The admin can turn export off. Postgres still feeds the admin charts |
| Q26 | AWS S3 for the connector demo and nightly `pg_dump`, with a weekly copy pulled to the Mac. A local S3 emulator for tests |
| Q27 | Public site ID for the widget. Secret API keys (shown once, stored hashed) for programmatic ingestion |

## 3. Top 5 risks and mitigations
1. **Time.**
   - **Risk:** 3 build weeks × 6 days × ~3.5 h ≈ 63 h. My estimate is 70–85 h for P0 + P1 + deploy, plus about 6 h for monitoring and the setup token. P2 is not in that estimate. These are estimates, not measurements.
   - **Mitigation:** P2 stays thin or moves to the roadmap. Hard checkpoint at the end of build week 2. Every spike is timeboxed. 🟩 scaffolding is generated fast. Hint ladder after 30 minutes stuck. Scope changes are proposed explicitly, never by quietly lowering quality.
2. **Free VM availability and performance.**
   - **Risk (updated 2026-11-05):** the AWS t4g.small has only 2 GB RAM and a burstable CPU, and the Free plan ends ~6 months after signup. arm64 builds may break. OCR plus rerank may be too slow or too big.
   - **Mitigation:** sign up on Day 1 and pick the home region carefully. Cloudflare Tunnel as fallback. Benchmark embed, rerank and OCR **on the VM** by Day 7. Multi-arch (arm64) image builds in CI. OCR pages are processed one at a time in a queue.
3. **Answer quality on messy content** (OCR garbage, tables, conflicting versions) leading to hallucination.
   - **Mitigation:** per-category metrics from Day 2, OCR page routing, citation verification, abstain thresholds tuned on data, and honest table limits. Conflicting versions are tested deliberately.
4. **LLM limits, cost and churn.**
   - **Risk:** free-tier quotas break CI. Deprecations are coming (Gemini 2.5 Flash is rerouted on 2026-12-01; Gemini 3.x prices double on 2027-01-01).
   - **Mitigation:** two-tier CI with caching. Pinned model IDs. The safety layer with fallback. A hard usage limit set in the OpenAI dashboard **plus** the in-app cap. A spend ledger, and you approve every paid call.
5. **Public demo abuse and security.**
   - **Risks:** budget burn, prompt injection in documents and from visitors, the admin-claim race, SSRF, XSS in rendered answers.
   - **Mitigation:** setup token, origin allowlist, per-visitor rate limits, spend cap with sources-only mode, and injection and SSRF cases in the golden set and tests. Markdown is sanitized and the iframe has a CSP.

## 4. Week 0 curriculum (about 4 h/day, 6 days plus a light Day 7)
Every 🟥 or 🟨 item runs the Loop: brief → predict → build → break → measure → record → drill. Numbers go into `docs/experiments.md`.

| Day | Spike | Failure you trigger on purpose | Number we measure |
|---|---|---|---|
| **1** 🟩/🟨 Setup and verification | AWS Free plan signup (Oracle rejected the card; ADR-014). Create the S3 bucket, Resend DNS on your subdomain, Grafana and Langfuse accounts. Get free LLM keys plus an OpenAI key with a hard $5 limit. Download Nextcloud v35 and v33 PDFs and crawl about 100 HTML pages. Build 4–5 messy PDFs: phone scan, 2-column, table-heavy, password-protected, oversized | Feed the password-protected and oversized PDFs to a naive parser and watch it fail | Corpus size (pages, tokens), parse failures, $ spent |
| **2** 🟥 Parsing and hybrid OCR | Native extraction (pypdfium2 / pdfplumber) vs Docling. Detect pages that need OCR (chars/page, garbage ratio). Tesseract vs RapidOCR | Run native extraction on a scanned page (empty or garbage); a 2-column page with scrambled reading order; a flattened table | Share of pages correctly routed to OCR, character error rate on 3 hand-typed pages, seconds per page, table cell accuracy on 1 table |
| **3** 🟥 Golden set v1, chunking and embeddings | **You write 20 golden questions** (direct, multi-chunk, table, scanned, follow-up, unanswerable, out-of-scope, injection) with expected source pages. Compare fixed-512 chunking, heading-aware chunking and the LlamaIndex baseline. bge-small vs one larger local model vs OpenAI `text-embedding-3-small` (I ask before the paid call; under $0.10) | A chunk boundary that splits a numbered step list or table, causing a retrieval miss | recall@5 and MRR@10 per chunker × embedder, embed time per 1k chunks |
| **4** 🟥 Retrieval | Local Postgres + pgvector. Keyword (FTS) vs vector vs hybrid RRF vs hybrid + rerank (MiniLM-L6 vs bge-reranker-base) | An exact-term query (`occ files:scan`, a config key) where vector search fails; a paraphrase where keyword search fails | recall@5 and MRR for the 4 setups, rerank latency p50/p95 for 20 and 50 passages on CPU |
| **5** 🟥 Grounded generation, citations and abstain | LLM bake-off on the 20 questions (Gemini free, Groq free, OpenAI nano/mini paid with your OK). Prompt with chunk IDs, inline `[c3]`, and a post-hoc citation check. Plot retrieval scores for answerable vs unanswerable questions to set the 2 thresholds | Ask unanswerable questions before abstain exists; force a citation to an ID that doesn't exist | Faithfulness (your labels), abstention precision/recall, TTFT p50/p95, $ per answer per model |
| **6** 🟥 Break-it day and eval script | Plant injection text in a document plus a visitor-side injection. Fake a slow or 429 provider. Load v33 and v35 conflicting pages. Consolidate everything into **one command** that runs the 20 questions and prints the metrics table. Optionally cross-check one metric with RAGAS | All of the above | Injection success rate before and after mitigation, behavior under timeout/429, conflict-detection outcome |
| **7** (light, about 2–3 h) Write-up and go/no-go | If the VM is up, rerun the embed/rerank/OCR benchmarks **on the VM** and measure **peak RAM of the whole stack** (ingest a large PDF while chatting). Write `docs/week0-findings.md`, the failure-mode journal, draft ADRs, a Week 1 task list with tags, and `PROGRESS.md`. Client drill | — | VM latency vs Mac, go/no-go criteria met or not |

**Go/no-go for build week 1:**
- Hybrid + rerank beats vector-only recall@5 by a measured margin.
- Abstain thresholds come from data.
- The VM, or the tunnel fallback, is confirmed, and the stack peaks **under ~1.7 GB RAM** on the t4g.small.
- The LLM primary and fallback are chosen.
- Spend so far is ≤ $1.

## 5. Verified free options (2026-11-04) and what's uncertain
- **VM (superseded 2026-11-05 by ADR-014: AWS t4g.small).** Verified on Oracle's docs: Oracle A1 is **2 OCPU / 12 GB**, 200 GB block storage, 10 TB egress, home region only. Idle reclaim happens when CPU p95, network and memory are all under 20% for 7 days. A card is required.
  - GCP is too small (1 GB egress). AWS is 6 months only. Azure is 12 months only.
  - **Uncertain:** whether capacity is actually available (anecdotal waits of weeks) and whether PAYG is exempt from reclaim.
- **DNS/HTTPS.** Your own domain works with Caddy and Let's Encrypt. DuckDNS can't host email DNS records. nip.io shares one Let's Encrypt rate limit across all users.
- **LLM.**
  - Gemini free trains on data. Groq's free tier offers zero retention but can't stream with structured outputs.
  - OpenRouter free allows 50 requests/day. Cerebras is a 30-day trial. GitHub Models is retired. Cohere's trial bans commercial use.
  - OpenAI verified today:
    - `text-embedding-3-small` costs $0.02/M tokens.
    - `gpt-5-nano` costs $0.05 in / $0.40 out per M tokens, and `gpt-4o-mini` $0.15 / $0.60.
    - That's about $0.0003–0.0007 per answer, before reasoning tokens.
  - **Uncertain:** exact free-tier rate limits (only shown in consoles), and how far reasoning tokens inflate cost.
- **Email and webhooks.**
  - Resend: 100/day, 3k/month. Oracle Email Delivery: 3k/month. SendGrid's free plan has ended.
  - Port 25 is blocked on the clouds, so we use 587.
  - webhook.site exposes data publicly, so tests use a local receiver.
  - **Uncertain:** whether Resend requires a card.
- **OCR and PDF.**
  - Tesseract 5.5.4 (Apache), RapidOCR (Apache, ONNX, arm64), pypdfium2, pdfplumber and Docling (MIT) are all permissively licensed.
  - **Avoid:** PyMuPDF (AGPL), OCRmyPDF (needs Ghostscript, likely AGPL, unverified), Marker and MinerU (restrictive terms). PaddleOCR has no arm64 wheel.
- **Monitoring.**
  - Grafana Cloud Free: 10k series, 50 GB logs, 50 GB traces, 14 days, 3 users, no card.
  - Langfuse Hobby: 50k units/month, 30 days, 2 users, no card.
  - **Uncertain:** free-tier OTLP ingestion details and the shape of the LlamaIndex↔Langfuse integration. Both get verified in Week 1.

## 6. First actions after approval
1. Create the repo skeleton for docs and spikes only (no platform code):
   - `docs/experiments.md`, `docs/failure-modes.md` (seeded with the §6E list) and `docs/decisions/`
   - `docs/roadmap.md`, `docs/spend-ledger.md`, `PROGRESS.md`
   - `spikes/`, `.gitignore`, `.env.example`
   - a project `CLAUDE.md` = your brief plus an **"Amendments"** section listing the re-decided items (Vite instead of Next.js, setup token, 3 build weeks, LlamaIndex plumbing, OpenAI paid for real chats, OTel/Grafana/Langfuse)
2. Write ADR-001 through ADR-00x, recording the grilling decisions above.
3. Save memory notes: you prefer plain-language explanations and multiple-choice questions.
4. Start Day 1 with its brief and the predict question.

## 7. How we verify Week 0 is done
- `spikes/eval.py` runs the 20 golden questions in one command and prints recall@5, MRR, abstention P/R, faithfulness, TTFT and $ per answer.
- `docs/experiments.md` has before/after rows for each of Days 2–6.
- The failure journal has ≥10 entries, each with symptom, detection, mitigation and the test that proves it.
- `docs/week0-findings.md` contains the go/no-go verdict.
- Spend ledger ≤ $1.
