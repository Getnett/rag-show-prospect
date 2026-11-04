# ADR-011: Hosting on Oracle Always Free A1 (2 OCPU / 12 GB, arm64)
- **Status:** Accepted (capacity not yet obtained)
- **Date:** 2026-11-04

## Context
Verified 2026-11-04:
- **Oracle A1:** 2 OCPU / 12 GB, 200 GB block storage, 10 TB egress, home region only. Reclaimed when CPU p95, network and memory are all <20% for 7 days. Card required.
- **GCP e2-micro:** 1 GB egress/month, unusable.
- **AWS:** free plan ends after 6 months or when credits run out.
- **Azure:** free VMs last 12 months.
- **Render free:** sleeps after 15 min (~1 min cold start), local files wiped, free Postgres deleted after 30 days.

## Options
1. Oracle A1 (one VM)
2. Mac + Cloudflare Tunnel only
3. Render/other PaaS free tiers (rejected: sleep, ephemeral disk, DB expiry)

## Decision
Option 1, with Option 2 as the fallback. Caddy auto-HTTPS on a subdomain of my own domain. Oracle Object Storage (S3 API) for the connector demo and nightly `pg_dump` (quota to verify on Day 1).

## Trade-offs and consequences
arm64 images are needed (pgvector, torch CPU, tesseract and node all have arm64 builds). One ingestion worker; OCR is serialized. The home region is permanent. 2026 reports describe capacity waits. Real limits get stated in the README after measurement.

## How I'd explain it to a client
"The demo runs on a free cloud VM; for production we'd size the server on the measured numbers."
