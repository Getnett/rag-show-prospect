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
