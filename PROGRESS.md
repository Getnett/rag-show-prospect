# Progress

## 2026-11-04 (Week 0, Day 0: planning)
- **Hours:** _fill in_
- **Done:**
  - Studied both mockups.
  - Verified current free tiers for the VM, LLMs, email, OCR, monitoring and storage.
  - Grilling session settled 29 decisions; see `CLAUDE.md` §12 and `docs/decisions/`.
  - Week 0 curriculum approved (`docs/week0-plan.md`).
  - Repo skeleton and docs seeded.
- **Next:** Day 1 (setup and verification). Oracle signup, accounts, corpus download, messy PDFs.
- **Blockers:** none.
- **Risks:** time (about 63 h available vs a ~76–91 h estimate incl. monitoring; P2 will be thin); Oracle A1 capacity.
- **Spend:** $0.00

## 2026-11-05 (Week 0, Day 1: setup)
- **Hours:** ~4
- **Done:**
  - Repo pushed to github.com/Getnett/rag-show-prospect (public).
  - Day 1 predict answered: garbage output ranked most dangerous (it misleads users); failures should say "can't process this". Critique: right on garbage; per-file predictions missing; silent empty is #2 (my ranking: garbage > silent empty > hang > crash).
  - Public address decided: free DuckDNS name + Caddy HTTPS, no Elastic IP; demo email via Resend's sandbox sender (ADR-015). Vercel domain untouched.
  - Oracle signup failed (virtual card rejected). Switched hosting to the AWS Free plan, EC2 t3.small (2 GB, x86), resized to m7i-flex.large for heavy ingestion: ADR-014.
  - AWS account created; the Free plan offers t3.small, c7i-flex.large and m7i-flex.large (t4g.small turned out not to be allowed).
  - EC2 t3.small instance created and left stopped until Day 7. Checklist done: Ubuntu amd64, disk enlarged, credit mode standard, SSH-only firewall, key outside the repo, termination protection on, no Elastic IP (DuckDNS instead, ADR-015).
  - Corpus downloaded (`spikes/download_corpus.py`): Nextcloud v35 + v33 User/Admin PDFs and 99 HTML pages, robots.txt respected; ~814k tokens. Messy PDFs generated (`spikes/make_messy_pdfs.py`).
  - Naive-parse break test (`spikes/naive_parse.py`): password → loud error, owner-only → opens, oversized → no hang (284 MB RSS), scan → silent empty. Finding: pypdf glues words on 113/333 pages of the clean manual; pypdfium2 doesn't (F20). See `docs/experiments.md`.
  - API keys for OpenAI, Groq and Gemini in `.env` (git-ignored, mode 600); all three verified with a free model-list call. OpenAI hard limit of $5 set in the dashboard (reported by me).
  - Tesseract 5.5.4 installed (eng + osd).
  - Real scan added (`data/messy/scanned-nextcloud-user-manual.pdf`, v35 User manual p. 13): naive parse = empty, no error. Ground truth saved for Day 2 CER.
  - Drill 1 ("how do I know an 'Indexed' doc is readable?"): I wasn't sure; model answer in `docs/client-cheatsheet.md`. Re-try it in my own words on Day 2.
- **Next:** Day 2 (parsing and hybrid OCR). Later: DuckDNS (Day 7), Langfuse (Day 5), Resend + Grafana (build weeks).
- **Blockers:** none.
- **Risks:** 2 GB RAM (Day 7 go/no-go: peak < ~1.7 GB); AWS Free plan ends ~May 2027 (6 months from signup).
- **Spend:** $0.00 (AWS usage comes from free credits only)

## 2026-11-06 → 2026-11-09 (Week 0, Day 2: parsing and hybrid OCR)
- **Hours:** 4
- **Done:**
  - Predict: I said the char-count rule OCRs pages that don't need it (blank pages). Right; missed the more dangerous direction: scans with a typed header or a hidden OCR layer get skipped.
  - Labelled set of 44 pages (`spikes/make_route_set.py`) and harness (`spikes/parse_compare.py`). Baseline: 39/44, 2 scans silently missed, 3 blank pages OCR'd; no N fixes both (sweep).
  - My v1: routing on image coverage > 90% → 44/44. My text_quality had bugs and failed clean pages; I asked for the solution after trying.
  - Reference solution + explanation (ADR-016): 44/44 routing, unreadable OCR pages (CER ≥ 0.5) fail with reasons, blank pages skipped, brochure case kept native. F03 tested, F21 added.
  - Decision: screenshot-heavy pages are not OCR'd (ADR-006 addendum).
  - Drill 2 ("why not OCR every page?"): right core point (OCR adds errors to text that was exact); missed time cost and numbers. Improved answer in `docs/client-cheatsheet.md`.
- **Next:** re-implement `text_quality` from memory as a check of understanding (optional, ~30 min); Day 3 (golden set v1, chunking × embeddings).
- **Blockers:** none.
- **Risks:** quality thresholds tuned on 10 pages (thin margin 0.65 vs 0.46); table fixture too easy. Timeline: no fixed end date (my call, 2026-11-09); the only hard date is the AWS Free plan expiry (~May 2027).
- **Spend:** $0.00

## 2026-11-11 → 2026-11-17 (Week 0, Day 3: golden set v1, chunking × embeddings)
- **Hours:** ~8
- **Done:**
  - Golden set v1: 20 questions written and verified by me (`eval/golden/g20-v1.yaml`), with tools to find pages (`spikes/find_page.py`) and validate quotes (`spikes/check_golden.py`). Review fixed answers that claimed more than their sources (q07, q11, q12, q13).
  - Found F22 through the checker: PDFs hide a line-break hyphen (U+FFFE / U+0002) inside words; stripped at extraction.
  - Predict: I answered about the LLM; the retrieval answer is that follow-ups fail because "it" has nothing to search for. Confirmed: q19 missed by every setup.
  - Harness (`spikes/retrieval_eval.py`), scoring by evidence text. Baselines fixed_512 and LlamaIndex default; heading_aware written together after my draft (timeboxed).
  - Results: bge-base = bge-small recall at 3× the time; bge cuts 74–90% of baseline chunks at 512 tokens (F24); OpenAI 3-small is the only change that raised recall (fixed_512 0.71, heading_aware 0.57 = 2 questions of 14).
  - Decision: heading_aware + OpenAI for Day 4, with a written switch rule (ADR-017). F23 and F24 added.
  - Drill 3 ("why pick the lower score?"): good on sample size and citations; missed the number, the switch rule, and claimed unmeasured hallucination. Model answer in `docs/client-cheatsheet.md`.
- **Next:** Day 4 (Postgres + pgvector, keyword vs vector vs hybrid vs rerank; neighbour expansion for multi_chunk).
- **Blockers:** none.
- **Risks:** 14 scored questions (one = 0.07): conclusions re-checked on 60. Unanswerables score like answerables on similarity alone (q14), so Day 5 needs more than a threshold. Scanned questions use the truth text, not OCR output (no OCR-in-the-loop until build week 1).
- **Spend:** ~$0.03 (OpenAI embeddings, approved; ledger updated). Total ~$0.03.
