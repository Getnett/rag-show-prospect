# ADR-014: Hosting on AWS Free plan, EC2 t3.small (2 vCPU / 2 GB, x86), resized when needed
- **Status:** Accepted (supersedes ADR-011)
- **Date:** 2026-11-05

## Context
ADR-011 chose Oracle Always Free A1 (2 OCPU / 12 GB). Oracle rejected my card at signup: its FAQ excludes virtual, prepaid and PIN-only debit cards.

AWS Free plan, from the AWS Free Tier FAQ, checked 2026-11-05:
- $100 in credits at signup, plus up to $100 more for onboarding tasks. Usage is charged only to credits, never to a card.
- A payment method "isn't required to sign up for most new customers".
- The plan lasts **up to 6 months or until the credits run out**, whichever comes first. The account is then suspended, and erased if not upgraded within 90 days.

My account's EC2 launch page (Free plan) offers these types. Ubuntu prices as shown in my console:

| Type | vCPU / RAM | $/hour | ≈ $/month 24/7 incl. 30 GB gp3 + public IPv4 |
|---|---|---|---|
| t3.small | 2 / 2 GB | 0.0143 | ~$16.50 |
| c7i-flex.large | 2 / 4 GB | 0.09427 | ~$75 |
| m7i-flex.large | 2 / 8 GB | 0.10525 | ~$83 |

A first check suggested t4g.small (arm64) was offered. It is not.

## Options
1. t3.small 24/7 with a slim setup, temporarily resized to m7i-flex.large for heavy ingestion
2. m7i-flex.large 24/7: comfortable, but $200 of credits lasts ~2.4 months
3. m7i-flex.large started only for demos and benchmarks: cheap, but the demo link isn't always live
4. Mac + Cloudflare Tunnel, or Hetzner (~€6/month by PayPal)

c7i-flex.large was dropped: m7i-flex.large gives double the RAM for ~11% more.

## Decision
Option 1. Mac + Cloudflare Tunnel stays the fallback. Hetzner is the paid exit when the AWS plan expires.

Memory plan for 2 GB:
- A 4 GB swap file on the EBS disk. Swap is a safety net against out-of-memory crashes, not a performance plan.
- `mem_limit` on every Compose service, so one runaway service can't take the box down.
- One ingestion worker. OCR runs one page at a time.
- Embedding and rerank models are loaded once per process.
- Postgres tuned small (`shared_buffers` ≈ 256 MB).
- t3 credit specification set to **standard** (AWS defaults t3 to unlimited), so a CPU spike slows down instead of spending credits.

Resize for heavy work: stop the instance → change the type to m7i-flex.large → start → ingest → switch back. Both types are x86, so the same disk boots on either. That costs roughly $0.10 per hour while resized. An **Elastic IP** keeps the public address, and therefore DNS, stable across stop/start.

Storage and backups: an S3 bucket in the same account for the connector demo and nightly `pg_dump`. A weekly copy of the dump is pulled to my Mac, because an expired account takes its buckets with it.

## Provisioned (2026-11-05, as reported by me from the console)
- EC2 t3.small, Ubuntu, x86_64 (amd64). Created and **stopped** until Day 7.
- Root disk enlarged from the default: ~28 GB free on a fresh Ubuntu install (consistent with a 30 GB volume). Rough budget: 4 GB swap, ~5 GB Docker images, ~1 GB models, the rest for Postgres, uploads and local backups.
- Credit specification: **standard**.
- Security group: SSH (22) only, from my IP. Ports 80/443 open on deploy day.
- Key pair stored outside the repo. Termination protection on.
- No Elastic IP yet: an unattached Elastic IP is billed hourly, so it's created on Day 7.

## Trade-offs and consequences
- **Hard expiry.** The demo can live until about May 2027 (6 months from signup); ~$16.50 × 6 ≈ $99 fits even the base $100 credit. Then I migrate: `docker compose up` on the new host plus a restore from backup. That doubles as our tested-restore drill.
- **2 GB is tight.** Go/no-go on Day 7: serving (Postgres, API, Caddy, idle worker) must peak **under ~1.7 GB RAM** while answering chats. Heavy ingestion may exceed that and is what the resize is for. If plain serving doesn't fit, switch to OpenAI embeddings (only if the Day 3 quality numbers allow it) or move to Hetzner.
- **x86, not arm64.** The server is Intel; my Mac is Apple Silicon (arm64). Images for the server are built as `linux/amd64` in CI (GitHub runners are x86). This removes the arm64-wheel risk on the server; local dev on the Mac stays arm64.
- **Burstable CPU.** In standard mode the CPU drops to its baseline when burst credits run out, so sustained ingestion is slow. The README states the measured limits.
- **Resizing is manual** and causes a few minutes of downtime. That's acceptable for a demo, not for a client's production.

## How I'd explain it to a client
"The demo runs on a deliberately small 2 GB server to prove the stack is lean. Heavy one-off jobs like a first big import run on a temporarily larger server. For your production we size the server from the measured peak memory and latency numbers, and moving hosts is one command plus a backup restore."
