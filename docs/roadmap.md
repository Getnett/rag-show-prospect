# Roadmap (not in this build)

Each item says why it was left out and what it would take. Effort figures are rough estimates, not measurements.

| Item | Why not now | What it would take |
|---|---|---|
| **Prospect trials: one private copy per prospect** | The demo-only model covers selling for now (decided 2026-11-04) | A script that creates a Compose project with its own DB, subdomain and setup token; spend and file caps; auto-delete. ~4–6 h |
| **Self-serve multi-tenant SaaS** | Changes every table, query, cap and quota; one bug leaks one company's data to another. Too large for 3 weeks | Tenant ID everywhere plus Postgres row-level security, per-tenant caps and quotas, abuse review for uploads, terms and DPA. ~20–30 h+ |
| Demo on my own domain + own email sender | DuckDNS and Resend's sandbox are free and enough for the demo (ADR-015) | One A record on my domain, one Caddyfile line, Resend domain verification (SPF/DKIM records). ~30 min |
| Multiple admins / roles / Team page | Single admin by design | Users table, invites, roles and permission checks, audit per user |
| Live human chat | Escalation is by email/webhook only | Agent inbox, presence, WebSocket handoff |
| Google Drive / Confluence / Notion connectors | One real connector (S3) proves the interface | One `Connector` implementation each, plus OAuth flows |
| CSV / XLSX ingestion | Tables need their own chunking and answering strategy | Row-wise chunking with header context; maybe text-to-SQL for large sheets |
| Vision-LLM for hard PDF pages | Cost; local OCR first | Implement the provider call behind the existing flag; per-page cost cap |
| Multilingual support | English only for the MVP | Multilingual embedder/reranker, language detection, translated widget strings, per-language golden set |
| Visitor thumbs up/down feedback | Not in the brief's MVP | Feedback endpoint plus admin view; feed the eval set |
| Self-hosted Prometheus/Grafana/Jaeger | Too heavy for a 2 GB free VM | Separate monitoring host, or a paid VM |
| OpenTelemetry export to other backends | Grafana Cloud + Langfuse cover the demo | Swap the OTLP endpoint (vendor-neutral by design) |
