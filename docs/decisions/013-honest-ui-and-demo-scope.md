# ADR-013: Honest UI text, demo corpus and go-to-market scope
- **Status:** Accepted
- **Date:** 2026-11-04

## Context
Some mockup text would mislead users: "chat with a human", "Usually replies in a few minutes", read ticks, an undefined "Indexed" count, an average latency, and Confluence/Sheets/Team that we don't build. The demo is what prospects will see.

## Decision
- **Escalation:** "Want someone from our team to follow up by email?" and **Yes, contact me**, then email plus consent, then a confirmation.
- **Header:** "AI assistant · answers from our docs" (configurable). One tick means sent; no read ticks.
- **Admin:** "Indexed" = document count. "Indexing %" = documents processed / total. Latency = TTFT p50/p95.
- **Types and pages:** only supported source types shown; no Team page.
- **Confidence bands:** three, with thresholds tuned on the golden set.
- **Corpus:** Nextcloud User + Admin manuals, **CC BY 3.0 (verified)**, web pages + PDFs, plus my messy PDFs. v33 vs v35 for the conflicting-docs test. Attribution on the demo site. BYD manuals were rejected (copyright/brand and safety-critical answers).
- **Go-to-market:** I'm the sole admin of a public demo. Prospect trials and SaaS go to the roadmap.

## How I'd explain it to a client
"The bot never pretends to be a person or promises what it can't do."
