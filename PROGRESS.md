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
- **Hours:** _fill in_
- **Done:**
  - Oracle signup failed (virtual card rejected). Switched hosting to the AWS Free plan, EC2 t3.small (2 GB, x86), resized to m7i-flex.large for heavy ingestion: ADR-014.
  - AWS account created; the Free plan offers t3.small, c7i-flex.large and m7i-flex.large (t4g.small turned out not to be allowed).
  - EC2 t3.small instance created and left stopped until Day 7. Checklist done: Ubuntu amd64, disk enlarged, credit mode standard, SSH-only firewall, key outside the repo, termination protection on, no Elastic IP yet.
- **Next:** rest of Day 1 (accounts, corpus download, messy PDFs, predict question).
- **Blockers:** none.
- **Risks:** 2 GB RAM (Day 7 go/no-go: peak < ~1.7 GB); AWS Free plan ends ~May 2027 (6 months from signup).
- **Spend:** $0.00 (AWS usage comes from free credits only)
