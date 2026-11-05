# ADR-002: Admin UI as a React + Vite single-page app (not Next.js)
- **Status:** Accepted (amends CLAUDE.md §4)
- **Date:** 2026-11-04

## Context
The admin is behind a login and needs no SEO. Full Next.js runs a Node server 24/7 next to the Python API, which creates a second place where login is handled (middleware/SSR) and makes CSP more complex. The free VM has 2 OCPU / 12 GB. *(Update 2026-11-05: the VM is now 2 GB, see ADR-014, which makes a second Node server even less affordable.)*

## Options
1. React + Vite SPA, static files served by Caddy, all auth in FastAPI
2. Next.js static export (no Node server)
3. Full Next.js on the VM
4. Full Next.js on a free host (Vercel/Cloudflare Pages); cross-domain cookies; free-plan terms unverified

## Decision
Option 1, with Tailwind, shadcn/ui, Recharts and TanStack Query.

## Trade-offs and consequences
No server-side rendering (not needed). "Next.js" doesn't appear on the CV, but there's one auth surface and one machine. Static files can move to any static host later without code changes.

## How I'd explain it to a client
"One backend owns security; the dashboard is just files, so there's less to run and less to attack."
