# ADR-010: Widget = loader script + iframe; public site ID vs secret API keys
- **Status:** Accepted (amends the CLAUDE.md §10 "widget public key" assumption)
- **Date:** 2026-11-04

## Context
The widget runs on third-party pages. Anything in the embed snippet is public (visible via View Source).

## Options
- In-page Shadow DOM widget (host page JS can read the chat; CSS bleed)
- **Loader script (~5 KB) that opens an iframe from our domain**, with direct iframe embed as the fallback
- Keys: one "widget key" type vs **public site ID + secret API keys**

## Decision
Iframe-based widget (Preact + Vite). The widget uses a **public site ID** that only selects which bot. **Secret API keys** (shown once, stored hashed) are only for programmatic ingestion. Real abuse protection = origin allowlist + per-visitor rate limits + spend cap.

## Trade-offs and consequences
An iframe needs postMessage for resize/open state, and the origin check relies on browser headers (non-browser clients can spoof them, hence rate limits and the cap).

## How I'd explain it to a client
"The chat runs in a sealed box from our server, so your site can't break it and nothing on your page can read your visitors' chats."
