# Week 0 spikes

Throwaway Python scripts, run on the Mac. They exist to **measure** things, not to ship. Results go into `docs/experiments.md`.

Rules:
- One script per question (`parse_compare.py`, `chunk_embed.py`, `retrieval.py`, `generate.py`, `eval.py`).
- Every script prints a results table that can be pasted into the experiments log.
- No secrets in code. Read keys from `.env` (see `.env.example`).
- Paid API calls are approved first and logged in `docs/spend-ledger.md`.
- Corpus and outputs live in `data/` and `spikes/out/` (both git-ignored).
