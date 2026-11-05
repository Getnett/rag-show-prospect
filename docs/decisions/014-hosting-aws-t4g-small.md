# ADR-014: Hosting on AWS Free plan, t4g.small (2 vCPU / 2 GB, arm64)
- **Status:** Accepted (supersedes ADR-011)
- **Date:** 2026-11-05

## Context
ADR-011 chose Oracle Always Free A1 (2 OCPU / 12 GB). Oracle rejected my card at signup: its FAQ excludes virtual, prepaid and PIN-only debit cards.

AWS Free plan, from the AWS Free Tier FAQ, checked 2026-11-05:
- $100 in credits at signup, plus up to $100 more for onboarding tasks. Usage is charged only to credits, never to a card.
- A payment method "isn't required to sign up for most new customers".
- The plan lasts **up to 6 months or until the credits run out**, whichever comes first. The account is then suspended, and erased if not upgraded within 90 days.

My account's EC2 launch page offers only **t4g.micro (1 GB)** and **t4g.small (2 GB)** on the Free plan.

## Options
1. t4g.small with a slim setup (swap, per-container memory limits, one worker)
2. t4g.small with OpenAI embeddings instead of a local embedder, to save RAM
3. Mac + Cloudflare Tunnel now, choose a server in build week 3
4. Hetzner CAX11, 2 vCPU / 4 GB, about €6/month by PayPal

## Decision
Option 1. Mac + Cloudflare Tunnel stays the fallback, and Hetzner is the paid exit when the AWS plan expires.

Memory plan for 2 GB:
- A 4 GB swap file on the EBS disk. Swap is a safety net against out-of-memory crashes, not a performance plan.
- `mem_limit` on every Compose service, so one runaway service can't take the box down.
- One ingestion worker. OCR runs one page at a time.
- Embedding and rerank models are loaded once per process.
- Postgres tuned small (`shared_buffers` ≈ 256 MB).
- T4g burstable CPU in **standard** credit mode, so a CPU spike slows down instead of burning credits. To verify on Day 7.

Storage and backups: an S3 bucket in the same account for the connector demo and nightly `pg_dump`. A weekly copy of the dump is pulled to my Mac, because an expired account takes its buckets with it.

## Trade-offs and consequences
- **Hard expiry.** The demo can live until about May 2027 (6 months from signup). Then I migrate: `docker compose up` on the new host plus a restore from backup. That doubles as our tested-restore drill.
- **2 GB is tight.** Go/no-go on Day 7: the full stack (Postgres, API, worker, Caddy) must peak **under ~1.7 GB RAM** while ingesting a PDF and answering a chat. If it doesn't, apply Option 2 (only if the Day 3 quality numbers allow it), or move to Hetzner.
- **Rough monthly cost against credits** (on-demand list prices, re-check before launch): t4g.small ≈ $12, 30 GB gp3 ≈ $2.40, public IPv4 ≈ $3.60, so about $18/month.
- **Burstable CPU.** OCR and reranking are bursty, which suits T-class servers. Sustained ingestion of a big corpus will be slow. The README states the measured limits.

## How I'd explain it to a client
"The demo runs on a deliberately small 2 GB server to prove the stack is lean. For your production we size the server from the measured peak memory and latency numbers, and moving hosts is one command plus a backup restore."
