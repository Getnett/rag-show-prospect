# ADR-008: Two-tier CI eval gate
- **Status:** Accepted (amends "golden set on every code change")
- **Date:** 2026-11-04

## Context
One full run is ~60 questions × (rewrite + answer + judge) ≈ 120+ LLM calls and ~400K tokens. Free tiers (e.g. OpenRouter at 50 requests/day) can't absorb that per push. Provider outages would make CI fail for reasons unrelated to the code.

## Options
1. Full LLM eval on every push
2. **Tier 1 on every push:** lint, types, tests and retrieval eval (recall@k, MRR, retrieval-based abstain), with local embeddings, no LLM and deterministic results. **Tier 2 on PR to main, nightly and manual:** full generation plus judge eval, with response caching and tolerance bands

## Decision
Option 2. Both tiers block (tier 2 blocks the PR). Results are stored and feed the admin Evaluation page.

## Trade-offs and consequences
A generation regression can sit on a branch until the PR. Cache keys must include the prompt, model and context hash, or stale results hide regressions. If OpenAI embeddings win in Week 0, golden-set query embeddings are cached so tier 1 stays deterministic.

## How I'd explain it to a client
"Every change is checked automatically; the expensive AI checks run before anything reaches production."
