# ADR-003: One-time setup token instead of "first signup wins"
- **Status:** Accepted (amends CLAUDE.md §4 Tenancy)
- **Date:** 2026-11-04

## Context
"First signup becomes admin" on a public URL lets a stranger or a bot claim a fresh deployment before the owner does. The claim must still be atomic.

## Options
1. First signup wins (original)
2. A one-time setup token, printed on first start (or set via env), required to create the admin; claimed atomically; signup closed afterwards
3. Admin created only via CLI

## Decision
Option 2. Same pattern as GitLab and Grafana initial setup. The atomic claim design is a 🟥 for build week 1.

## Trade-offs and consequences
One extra step for the owner (copying the link from the logs). The token must never be logged to external sinks, so it gets excluded from OTel export.

## How I'd explain it to a client
"Only the person holding the setup link can become admin, even if the server is public from minute one."
