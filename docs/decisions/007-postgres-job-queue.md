# ADR-007: Hand-rolled Postgres job queue
- **Status:** Accepted
- **Date:** 2026-11-04

## Context
Ingestion must be idempotent, retried with backoff, isolated per document and crash-safe. Postgres is already in the stack, and the VM is small.

## Options
1. Hand-rolled: `SELECT … FOR UPDATE SKIP LOCKED`, lease + heartbeat, attempts with backoff, dead-letter status (~150–200 lines)
2. Procrastinate (Postgres-backed library)
3. Celery/arq + Redis

## Decision
Option 1 (🟥). It's exactly the reliability skill I'm here to learn, and it adds no extra service.

## Trade-offs and consequences
I own the bugs. It needs tests for lease expiry, double-claim and crash mid-job. It's fine for this scale (one worker); the README says so.

## How I'd explain it to a client
"Jobs live in the same database as your data, so a crash never loses or double-processes a document."
