# Week 0 spikes

Throwaway Python scripts, run on the Mac. They exist to **measure** things, not to ship. Results go into `docs/experiments.md`.

Rules:
- One script per question. Day 1: `download_corpus.py`, `make_messy_pdfs.py`, `naive_parse.py`, `corpus_stats.py`. Later: `parse_compare.py`, `chunk_embed.py`, `retrieval.py`, `generate.py`, `eval.py`.
- Run with `uv run spikes/<script>.py`; dependencies are declared inline at the top of each script.
- Every script prints a results table that can be pasted into the experiments log.
- No secrets in code. Read keys from `.env` (see `.env.example`).
- Paid API calls are approved first and logged in `docs/spend-ledger.md`.
- Corpus and outputs live in `data/` and `spikes/out/` (both git-ignored).
