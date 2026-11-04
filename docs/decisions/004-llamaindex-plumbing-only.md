# ADR-004: LlamaIndex for plumbing only
- **Status:** Accepted
- **Date:** 2026-11-04

## Context
I need to explain and defend the hard parts (chunking, retrieval, rerank, abstain, citations, eval) myself. Frameworks speed things up but hide decisions and change between versions.

## Options
1. No framework; small libraries only
2. LlamaIndex for plumbing (loaders, provider connectors, a baseline splitter to compare against); **my own code** for retrieval SQL (Postgres FTS + pgvector, RRF), reranking, confidence/abstain, citation verification, eval metrics
3. LlamaIndex everywhere (built-in retrievers, rerankers, evaluators)

## Decision
Option 2. In Week 0, LlamaIndex's built-in retriever is a measured baseline against mine.

## Trade-offs and consequences
Dependency weight and version churn. Pin exact versions. **Never use PyMuPDF-based readers** (AGPL, see ADR-006). If LlamaIndex fights the custom parts, drop it for that piece.

## How I'd explain it to a client
"I use a framework for the boring connectors and write the parts that decide answer quality, so I can tune and prove them."
