# ADR-001: Add a third build week
- **Status:** Accepted
- **Date:** 2026-11-04

## Context
The brief planned 2 build weeks (~45–55 h). My estimate for P0 + P1 + deploy/docs is ~70–85 h, before monitoring (~5 h) and the setup token (~1 h). P0 can't be cut. These are estimates, not measurements.

## Options
1. 3 build weeks, 6 days/week, MVP checkpoint at end of week 2
2. Keep 2 weeks; P1 thin, P2 mostly roadmap
3. Keep 2 weeks and also cut the S3 connector

## Decision
Option 1. At ~3.5 h/day that is ~63 h, which is still below the estimate. **P2 will be thin or on the roadmap**, and the week-2 checkpoint decides what's left.

## Trade-offs and consequences
A later finish. The risk of under-delivering P2 is accepted explicitly rather than quietly lowering quality. One rest day a week guards against burnout.

## How I'd explain it to a client
"I size work against real hours and protect the core first; polish is cut before reliability is."
