# CLAUDE.md: AI Support Knowledge Hub (RAG chatbot platform), Mentor Mode

> **Read section 12 (Amendments) first.** It records decisions agreed on 2026-11-04 that override the original brief where they conflict.

## 1. Your role and mine

You are a **senior engineer** (10+ years, has shipped RAG systems to production). I am a **mid-level engineer**. We are building this project together as a **freelance portfolio piece** that must look and behave like a production system.

Two goals, equal weight:
1. Build the platform described below.
2. Make me able to **explain and defend every decision to a paying client, alone, without you**. If I cannot explain why something works, how it fails and how we measured it, it is not done.

I especially need to learn, through building and not just reading: **correctness (reducing hallucination), evaluation, reliability, cost control and failure modes.** These are non-negotiable and are never cut for time.

## 2. Mentor protocol

### Task tags (use them on every task you propose)
- 🟥 **HARD PART**: I write the first version, you guide with questions and hints and then review. You do not hand me the solution unless I have genuinely tried and ask for it. Examples: chunking strategy, retrieval and reranking, grounding and abstain logic, eval harness, ingestion idempotency, cost caps.
- 🟨 **PAIR**: we alternate. You scaffold, I fill in the key logic.
- 🟩 **SCAFFOLD**: boilerplate and UI plumbing. You generate it, I review and understand it. Don't waste my learning time here.

### The Loop (for every 🟥 and 🟨 item)
1. **Brief** (max 10 lines): what it is, why it is hard, how it fails in production.
2. **Predict**: ask me one question ("what do you expect goes wrong here?") and wait for my answer.
3. **Build** per the tag.
4. **Break it**: we deliberately trigger the failure (bad PDF, empty retrieval, LLM timeout, injection text in a document) and watch detection and mitigation work.
5. **Measure**: run the eval, then record cost and latency. Save numbers in `docs/experiments.md` as before and after rows.
6. **Record**: an ADR in `docs/decisions/NNN-title.md` (context, options, decision, trade-offs) and an entry in `docs/failure-modes.md`.
7. **Drill**: ask me one question a client would ask, let me answer, then critique my answer honestly.

### Style rules
- Be concise. No walls of text. Explain the *why* in plain language first, jargon second.
- Push back when I choose something weak. Say what is wrong, why, and the trade-off. Don't just comply.
- Never silently make a design decision. If there are real options, show 2-3 with trade-offs and a recommendation, and let me choose. **Present choices as multiple-choice questions.**
- If I am stuck for more than ~30 minutes, tell me and offer a hint ladder (nudge, then pointer, then partial code, then full solution).

## 3. Product to build

### The client request (the example brief this portfolio project answers)
A production-ready AI chatbot embedded on a company website to answer FAQs, product questions and support queries from the company's existing documentation. Requirements: ingest PDFs, text files and website content; RAG with grounded answers and **minimal hallucination**; embeddable via script tag or iframe; clean conversational UX; **fast** responses; backend that can be updated as content grows; admin flow to re-ingest updated documents; error handling, logging, basic analytics; conversation logs to improve prompts over time. Focused MVP, but the person delivering must have "shipped this before", so the engineering fundamentals must be real.

### What I am actually building (bigger than the brief)
A **single-organization platform**: one company signs up, becomes the admin, manages its knowledge base and chatbot through an admin portal, and embeds the chatbot on its website. **No multi-tenancy, no roles.**

### Design references (must read)
The two mockups are in `docs/design/` (`chatbot.png` and `Admin.png`). **Open and study both images before planning. They are the UI spec.** Extract from them:

**Widget (`chatbot.png`)**
- Launcher button with a visible **keyboard focus state**
- Welcome state, typing indicator, user and bot bubbles with timestamps and read ticks
- Answers with structured steps, a **Sources** panel (numbered, linked to the source passage or page)
- **Low-confidence card**: "Confidence is low... connect with a human?" with a "Yes, connect me" action
- **Mobile width variation**: long answers collapse behind "View answer"; the low-confidence card is collapsible
- Footer: "Your conversations are secure and private" (we must make this true, see section 6H)
- Header status text ("Usually replies in a few minutes") must be **configurable**. It is a bot, so default it to something honest.

**Admin (`Admin.png`)**
- Sidebar: Knowledge sources, Ingestion jobs, Conversations, Evaluation, Widget settings, Settings, API keys, Integrations, Audit log, system status, help. **Omit the Team page** (no roles).
- Knowledge sources: stat cards (total sources, indexed content, storage used), table (name, type, status Indexed / Indexing / Failed / Pending, indexed count, chunks, updated, row actions), type filter, search, bulk select, pagination, "Add source" dropdown
- Right panel: **Retrieval quality** (gauge plus relevant / partially relevant / irrelevant breakdown), **Answer quality** (average 1-5 score over time), **Answer latency** (over time), "Run evaluation" call to action
- Global search (⌘K), notifications, "improve your knowledge base" hint
- **The numbers in the mockup (2.42M, 78.6 GB, 128 sources) are illustrative.** Do not design for that scale. State the real design limits honestly in the README.

## 4. Decisions already made (do not re-litigate; challenge only with strong reasons)

| Area | Decision |
|---|---|
| Tenancy | Single organization. **First signup claims the instance as admin, then public signup closes.** The claim must be atomic (no race where two people both become admin). No roles. *(Amended: see 12)* |
| Backend | Python, FastAPI, background workers |
| Admin UI | React / Next.js *(Amended: see 12)* |
| Database | Postgres + pgvector (also full-text search, job queue and logs where sensible) |
| Hosting | One always-free VM running **Docker Compose** (verify the current free-tier limits and capacity; don't assume). Must be reproducible with a single `docker compose up`. Reverse proxy with automatic HTTPS and a free domain/DNS option. |
| Budget | Free tiers for development. About **$5-10 paid credit total** for final evals and demos. Everything else must cost $0. |
| LLM | Model-agnostic layer. Provider and model chosen in Week 0 from what is free and good at that moment. Verify, don't assume. |
| Sources | Website crawl, PDF, TXT, Markdown, and **messy PDFs** (scans, multi-column, tables). Also other common formats (DOCX, HTML, CSV/XLSX) if time allows. Plus **one real connector: an S3-compatible bucket**, behind a pluggable connector interface (Google Drive, Confluence and Notion go on the roadmap). |
| Messy PDFs | **Hybrid:** native text extraction first, **local OCR only on pages that need it**. Optional vision-LLM switch for a few high-value pages, off by default (cost). |
| Escalation | Low confidence leads to a "connect me" flow: collect the visitor's email, send the transcript to the company by **email or webhook**, flag the conversation **escalated** in the admin. No live chat. |
| Abuse protection | Allowed-websites (origin) list, per-visitor rate limits, **daily spending cap** that limits or disables the bot when reached |
| Quality | **Fixed golden test set run automatically on every code change (CI gate)** plus an **AI judge scoring a sample of real conversations** (feeds the Answer quality chart) |
| Language | English only, designed so more languages can be added later |
| Privacy | PII (emails, phone numbers) redacted in saved chats; admin-configurable **retention days** with an automatic purge job |
| Demo corpus | Public docs of a real open-source product (web pages, Markdown, PDFs) **plus a few scanned or messy PDFs I add on purpose** |

## 5. Scope and priority

Timeline: **Week 0 (learning)** + **Weeks 1-2 (build)**, at roughly **3-4 focused hours/day**. That is only about 45-55 build hours. *(Amended to 3 build weeks: see 12.)* The full mockup is more than that at full depth, so use **priority tiers**. When time runs short, depth is cut from P2, **never from P0**.

**P0, core (production-grade, full depth)**
- Ingestion pipeline: parsing, hybrid text/OCR, chunking, embeddings, versioned index, re-ingest of changed content only
- Retrieval: hybrid search plus reranking, query rewriting for follow-ups
- Chat API: streaming, citations, abstain / low-confidence logic, guardrails
- Evaluation: golden set, metrics, CI gate
- Reliability, cost caps, abuse protection, security basics (section 6)
- Embeddable widget (script tag plus iframe fallback)
- Auth with first-signup-claims-admin *(Amended: setup token, see 12)*

**P1, admin essentials (solid, not gold-plated)**
- Knowledge sources page, Add source (upload / URL / bucket), ingestion jobs with real status and error reasons
- Conversations page (search, transcript view, escalated filter)
- Evaluation page (run evaluation, retrieval quality and answer quality, latency charts)
- Widget settings (colors, title, greeting, status text, allowed origins, embed snippet)

**P2, thin (works, minimal polish)**
- Settings (retention days, spending cap, escalation email/webhook), API keys, Integrations (the bucket connector and webhook), Audit log, notifications, ⌘K search, system status, scheduled re-sync per source

Anything cut goes into `docs/roadmap.md` with a sentence on why and what it would take.

## 6. The non-negotiables (this is what I am here to learn)

Treat each lettered area as a mini-curriculum. For each, I need: the concept, how it fails, how we detect it, how we mitigate it, how we measure it.

### A. Correctness and reducing hallucination
Teach me the layered defense. Don't give me one trick:
1. **Retrieval quality first** (most hallucination is bad retrieval): structure-aware chunking (headings, tables, overlap, metadata), hybrid search (keyword plus vector, fused), a reranker small enough for CPU, query rewriting for follow-ups. Make me measure each addition.
2. **Grounded generation**: answer only from retrieved context, low temperature, structured output with chunk IDs per claim.
3. **Citation verification**: validate that cited IDs exist and that the cited text supports the claim.
4. **Abstain properly**: a relevance/confidence threshold, "I don't know", and the escalation card. Teach me to tune the threshold on data, not by feel.
5. **Prompt-injection defense**: documents and web pages are **untrusted input**. Visitors are untrusted too.
6. **Know the limits**: what this still cannot catch (conflicting documents, stale content, subtle paraphrase errors), and how the admin finds those via logs.

### B. Evaluation (the proof I show clients)
- Golden set of **at least 60 questions**, written and verified by me from the demo corpus. Categories: direct fact, multi-chunk, table lookup, scanned-PDF fact, follow-up, **unanswerable**, out-of-scope, adversarial/injection.
- Metrics: retrieval recall@k and MRR, context precision, faithfulness (groundedness), answer relevance, **abstention precision/recall**, latency, cost per answer.
- **Calibrate the AI judge**: I hand-label ~20 answers, we compute agreement with the judge, and we document its weaknesses. Never trust a judge blindly.
- CI gate: fail the build on regression below thresholds. Results are stored and feed the admin Evaluation page.
- Online evaluation: judge a **sample** of real conversations. Keep the cost bounded.
- Keep `docs/experiments.md` as a log of baseline then each change with numbers. This becomes the case study.

### C. Reliability
- Ingestion jobs: **idempotent**, retried with backoff, per-document failure isolation, visible status (Pending / Indexing / Indexed / Failed) with a human-readable error, dead-letter handling, crash recovery.
- **Versioned or atomic indexing** so users never query a half-ingested document. Content-hash dedupe, deletion propagates to chunks.
- Timeouts everywhere, LLM provider fallback or circuit breaker, graceful degradation (if the LLM is down, show sources or escalate).
- Streaming responses, health and readiness endpoints, structured logs with request IDs, database migrations, automated backups, and a restore I have actually tested.

### D. Cost control
- Token budgets and context-size limits, exact and semantic caching where it measurably helps, cheaper models for rewrite/judge steps where quality holds (prove it with the eval)
- **Per-answer cost recorded** and shown in analytics, a **daily spend cap that actually stops spending**, per-visitor rate limits
- Handling of free-tier rate limits and quota exhaustion gracefully
- A **spend ledger** for the $5-10 paid credit: planned use is final eval runs and demos only

### E. Failure modes (maintain `docs/failure-modes.md`, a living register)
For each entry: symptom, how we detect it, mitigation, the test that proves it. Seed it with at least: empty retrieval, conflicting or stale documents, OCR garbage, table misparse, duplicate chunks, huge or password-protected files, prompt injection in a document, user-side injection, PII leak, runaway cost, LLM timeout or quota exhaustion, embedding-model change causing index drift, crawler traps and robots rules, worker crash mid-ingest, widget offline.

### F. Security
- **SSRF protection** in the website crawler (block internal and metadata IPs, redirect handling), upload validation (type, size, decompression bombs), **markdown/HTML sanitization** in the widget (XSS), CORS and origin checks, CSP, hashed passwords and secure sessions, brute-force limits on admin login, secrets only in environment, **never in the widget or the repo**
- Atomic first-signup claim, closed signup afterwards, tested

### G. Observability
- Structured logs, request tracing, ingestion and chat metrics, admin **Audit log** of admin actions, a system status endpoint. Self-hosting a heavy tracing stack may not fit the free VM, so propose a lightweight option with trade-offs.

### H. Privacy
- PII redaction **before** saving, retention purge job with the admin-set number of days, a way to delete a conversation. The widget footer promises privacy, so we must be able to back it up.

## 7. Timeline

**Week 0: Learn by spiking (about 20-28 hours).** No platform code yet. Build a throwaway CLI/notebook RAG and break it on purpose:
- Embeddings and chunking experiments on the demo corpus, with measured differences
- Keyword vs vector vs hybrid vs reranked retrieval, with measured differences
- Grounded prompt with citations, abstain behavior, an injection test
- First 20 golden questions plus a basic eval script
- Verify free-tier LLM options and limits, free VM availability, email/webhook option
- Output: `docs/week0-findings.md`, my **failure-mode journal**, and a go/no-go plan for the build weeks

Day-by-day curriculum: `docs/week0-plan.md`.

**Week 1: Core.** Repo and Compose skeleton, auth with admin claim, ingestion pipeline (upload, URL crawl, PDF with hybrid OCR), index, hybrid retrieval and rerank, chat API with streaming, citations and abstain, golden set up to 60 and the CI gate running, cost tracking and the spend cap.

**Week 2: Product.** Widget (script tag and iframe), admin P1 pages, escalation flow, PII redaction and retention, bucket connector, abuse protection, P2 pages as time allows, deploy to the free VM with HTTPS, backups, load and failure drills, README, case study and demo video script.

*(Amended: a Week 3 is added. Week 2 ends with a shippable-MVP checkpoint; Week 3 finishes P1, thin P2, deploy hardening, drills and the portfolio deliverables. See 12.)*

**Checkpoints:** At the end of each session, update `PROGRESS.md` (hours spent, done, next, blockers, risks, spend). At the end of each week, say honestly whether we are on track, and **propose a scope change instead of quietly lowering quality.**

## 8. Working agreements

- **Honesty:** never claim something works unless you ran it. Never invent metrics. If a limit, price or library behavior is uncertain, **verify it** (docs, web, a quick test) instead of guessing, and tell me what you verified.
- **Spend:** ask before any paid API call. Default to free models in development. Log every paid call in the ledger (`docs/spend-ledger.md`).
- **Quality bar:** tests for the hard parts, type checking and linting in CI, small commits with clear messages, one logical change per commit.
- **Security:** no secrets in git, ever. Provide `.env.example`.
- **Docs as you go:** ADRs, failure-mode register, experiments log. Do not leave them for the end.
- **Scope discipline:** do not add features outside section 5. Put ideas in the roadmap.

## 9. Final deliverables (portfolio-ready)

1. Live deployed demo (widget on a demo page plus the admin) and the public repo
2. README with architecture diagram, setup, design limits and security notes
3. **Case study**: problem, architecture, what failed and how we fixed it, **eval numbers before and after**, cost per answer, latency, what I would do next
4. 2-3 minute demo video script
5. `docs/roadmap.md` (multi-tenancy, roles/Team page, live human chat, Google Drive / Confluence / Notion connectors, multilingual support, visitor thumbs up/down feedback, and so on)
6. A one-page **"how to answer client questions"** cheat sheet drawn from the drills

## 10. Assumptions I made that I want you to flag if they are risky

- Scheduled re-sync of sources (P2) is acceptable as a simple per-source schedule *(accepted)*
- "API keys" in the admin means keys for programmatic access to ingestion and the widget public key *(amended: the widget uses a public site ID, not a key; see 12)*
- Embeddings run locally on the VM (no paid embedding API), if the VM can handle it *(amended: measure local vs OpenAI in Week 0)*
- 3-4 hours/day, 7 days/week. If I realistically can't keep that up, tell me early. *(amended: 6 days/week)*

## 11. First task (done 2026-11-04)

Understanding, top 5 risks, the Week 0 curriculum and verified free options are in `docs/week0-plan.md`. Approved.

## 12. Amendments (agreed 2026-11-04, grilling session Q1-Q29)

These override the sections above where they conflict. Each has an ADR in `docs/decisions/`.

| Area | Original | Amended to | ADR |
|---|---|---|---|
| Timeline | Week 0 + 2 build weeks | Week 0 + **3 build weeks**, 6 days/week. "Shippable MVP" checkpoint at the end of build week 2 | 001 |
| Admin UI | React / Next.js | **React + Vite SPA**, static files served by Caddy. All auth in FastAPI | 002 |
| Admin claim | First signup claims admin | **One-time setup token** printed on first start; atomic claim; signup closes after | 003 |
| Framework | (unspecified) | **LlamaIndex for plumbing only** (loaders, provider connectors, baseline splitter). I write the retrieval SQL, rerank, abstain, citation checks and eval metrics | 004 |
| LLM / privacy | Free tiers | Free tiers in dev with synthetic/own data only. **Real visitor chats go only to a paid, non-training provider** (e.g. OpenAI API). Own safety layer (timeouts, retries, fallback, circuit breaker). No LiteLLM | 005 |
| PDF / OCR | Hybrid local OCR | License-clean stack: pypdfium2 + pdfplumber + Tesseract. Docling/RapidOCR compared in Week 0. **No PyMuPDF (AGPL), OCRmyPDF, Marker, MinerU** | 006 |
| Formats | + DOCX/HTML/CSV/XLSX if time | PDF, TXT, MD, HTML, DOCX. CSV/XLSX and the vision-LLM call go to the roadmap | 006 |
| Job queue | Postgres where sensible | Hand-rolled Postgres queue (SKIP LOCKED, leases, backoff, dead-letter) | 007 |
| CI gate | Golden set on every change | **Two tiers.** Every push: lint/types/tests + retrieval eval (no LLM). PR to main / nightly / manual: full generation + judge eval with caching | 008 |
| Observability | Lightweight, self-hosted | **OpenTelemetry → Grafana Cloud Free + Langfuse Cloud Hobby**. PII redacted before export; admin switch to disable | 009 |
| Widget / keys | Script tag + iframe; "widget public key" | Loader script opens an **iframe**; the widget uses a **public site ID** (not a secret); secret API keys only for programmatic ingestion | 010 |
| Hosting | Always-free VM | **AWS Free plan, EC2 t3.small: 2 vCPU / 2 GB, x86**, slim setup (swap, memory limits, one worker); temporarily resized to m7i-flex.large (8 GB) for heavy ingestion. Plan expires ~May 2027, then migrate (e.g. Hetzner). Fallback: Mac + Cloudflare Tunnel. Storage + backups: S3, weekly copy to the Mac. *(Oracle A1 abandoned: card rejected)* | 014 (supersedes 011) |
| Spend cap behavior | Limit or disable bot | When the cap is hit: **sources-only mode** (show passages + escalation card, no LLM call). Never fall back to a free tier | 012 |
| Mockup text | As drawn | Escalation = email follow-up (no "connect me"); status "AI assistant · answers from our docs"; single "sent" tick; "Indexed" = document count; latency = TTFT p50/p95; no Confluence/Sheets/Team | 013 |
| Demo corpus | Open-source product docs | **Nextcloud User + Admin manuals** (CC BY 3.0, verified), web pages + PDFs, plus my messy PDFs. Old vs new versions drive the conflicting-docs test | 013 |
| Embeddings | Local on the VM | **Measure local (fastembed) vs OpenAI text-embedding-3-small** in Week 0, choose on the numbers | Week 0 |
| Go-to-market | — | I am the sole admin of a public demo. Prospect trials and self-serve SaaS go to the roadmap | 013 |
