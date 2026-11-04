# ADR-009: OpenTelemetry → Grafana Cloud Free + Langfuse Hobby
- **Status:** Accepted (integration details verified in build week 1)
- **Date:** 2026-11-04

## Context
Monitoring is a client-facing skill. The VM can't host a heavy stack. Verified 2026-11-04, no card needed for either:
- **Grafana Cloud Free:** 10k series, 50 GB logs, 50 GB traces, 14 days, 3 users.
- **Langfuse Hobby:** 50k units/month, 30 days, 2 users.

## Options
1. Lightweight only (logs + Postgres metrics + health endpoints)
2. OTel + Grafana Cloud
3. **OTel + Grafana Cloud + Langfuse** (LLM traces: prompt, retrieved chunks, tokens, cost, latency per step)
4. Self-hosted Prometheus/Grafana on the VM

## Decision
Option 3. Postgres still feeds the admin charts. Plus `/healthz`, `/readyz`, `/status` and an external uptime pinger.

## Trade-offs and consequences
Data leaves the VM, so **PII is redacted before export**, the privacy note discloses it, and the admin can switch export off. Vendor-neutral OTLP keeps the backends swappable. Free quotas cap volume; sampling is used if needed.

## How I'd explain it to a client
"I can see every step of every answer: what was searched, what the AI saw, how long it took and what it cost, without storing your customers' personal data elsewhere."
