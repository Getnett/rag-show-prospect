# ADR-012: Spend cap triggers sources-only mode
- **Status:** Accepted
- **Date:** 2026-11-04

## Context
The public demo spends real (small) money. The cap must actually stop spending, and the privacy rule forbids silently switching to a free tier that trains on data.

## Options
1. Turn the bot off ("temporarily unavailable")
2. **Sources-only mode:** no LLM call; show the top matching passages with links plus the email follow-up card
3. Fall back to a free tier (rejected: breaks privacy)

## Decision
Option 2. Hard daily cap (~$0.15 to start) and hard total cap, enforced before the call (reserve, then reconcile), plus a hard limit in the provider dashboard.

## Trade-offs and consequences
Visitors get passages, not a written answer. The reserve-then-reconcile pattern must handle concurrent requests (🟥).

## How I'd explain it to a client
"When the budget is reached, the bot keeps helping with the exact passages from your docs; your bill can't run away."
