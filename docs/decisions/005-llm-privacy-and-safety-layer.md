# ADR-005: LLM providers, privacy rule and our own safety layer
- **Status:** Accepted (model choice pending the Week 0 Day 5 bake-off)
- **Date:** 2026-11-04

## Context
Verified 2026-11-04:
- Gemini's free tier uses data for training. Mistral's free tier does by default. Some OpenRouter free models do.
- The OpenAI API doesn't train on API data by default and keeps abuse logs ≤30 days.
- Groq and Cloudflare can't stream with structured output.
- LiteLLM had supply-chain compromises in 2026-03 and 2026-10.

The widget promises "secure and private".

## Options
- Free tiers everywhere (breaks the privacy promise)
- **Free tiers for dev with synthetic/own data only; real chats only to a paid, non-training provider**
- LLM client: LiteLLM pinned with hashes, or provider connectors wrapped in our own safety layer

## Decision
- **Privacy rule:** real visitor chats go only to a non-training provider (OpenAI API is the candidate).
- **Client:** LlamaIndex connectors wrapped in **my** safety layer: timeouts, retries with backoff, fallback provider, circuit breaker (🟥).
- **No LiteLLM.**
- **Streaming:** stream text with `[cN]` markers, then verify citations after the stream.

## Trade-offs and consequences
Real chats cost money (estimated ~$0.0003–0.0007 per answer before reasoning tokens; to be measured). Privacy note must mention the 30-day abuse-log retention.

## How I'd explain it to a client
"Your customers' chats never go to a provider that trains on them, and if the AI provider goes down the bot degrades instead of breaking."
