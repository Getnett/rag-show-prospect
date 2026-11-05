# ADR-015: Public address via a free DuckDNS name + Caddy HTTPS; demo email via Resend's sandbox sender
- **Status:** Accepted (amends ADR-014's Elastic IP plan and Q17/Q18 "subdomain of your own domain")
- **Date:** 2026-11-05

## Context
The demo needs a stable HTTPS address that I can share with prospects. Requirements: **$0**, and the server can be switched off between demos. I own a domain bought through Vercel, but I don't want to move its DNS or change it for this project.

Checked 2026-11-05:
- **Cloudflare Tunnel (named):** the free plan only works if Cloudflare runs DNS for the **whole** domain (nameserver switch). Subdomain-only (partial/CNAME) setup is Business/Enterprise. It's unconfirmed whether Vercel allows a nameserver switch on domains bought there.
- **Cloudflare Quick Tunnel (trycloudflare.com):** **no Server-Sent Events** (breaks our streaming chat), random hostname on every start, at most 200 in-flight requests, testing only.
- **Tailscale Funnel:** the free Personal plan is for non-commercial use (this demo sells my services), and bandwidth limits are unpublished.
- **Public IPv4 on EC2:** an EC2 instance without one has no outbound internet unless you add a NAT gateway (paid), so the server needs a public IP anyway. Free tier: 750 h/month of in-use public IPv4 on EC2. Anything else is paid from credits, not my card.
- **Resend without a verified domain:** the sandbox sender `onboarding@resend.dev` can only send to the Resend account's own email address.
- **DuckDNS + Caddy:** confirmed working with Let's Encrypt in 2026 reports. Plain Caddy uses the HTTP-01 challenge (port 80 open), so no DNS plugin is needed.

## Options
1. **DuckDNS free name** (e.g. `ragshow.duckdns.org`) → public IP → Caddy auto-HTTPS
2. Subdomain of my Vercel domain (one A record in Vercel DNS)
3. Move the Vercel domain's DNS to Cloudflare and use a named Tunnel
4. Cloudflare Quick Tunnel / Tailscale Funnel

## Decision
Option 1.
- A DuckDNS updater runs on boot (systemd/cron, token in `.env` on the server only), so the name follows the new public IP after every stop/start. **No Elastic IP**: an Elastic IP is billed while the instance is stopped, and the updater makes it unnecessary.
- Caddy gets and renews the Let's Encrypt certificate itself. Security group: 80/443 open on deploy day, 22 only from my IP.
- **Email for the demo:** escalation emails go through Resend's sandbox sender to my own inbox. For the demo, the "company" is me. The `Notifier` interface stays, so a client sets their own verified domain via config. The HMAC-signed webhook (Discord) is unaffected.

## Trade-offs and consequences
- **Looks hobby-ish** to clients. Upgrading to `demo.<my-domain>` later is one DNS record plus one Caddyfile line (roadmap).
- **Dependency on DuckDNS**, a free volunteer-run service with no SLA. If it's down, the demo is unreachable (F19). Fallback: an A record on my Vercel domain, ~10 minutes.
- **The IP changes on every start.** The updater must run before Caddy requests a certificate. Old DNS answers may linger for about a minute.
- **The demo can't email anyone but me.** That's fine for a demo; a real client deployment needs their verified domain.
- Rejected: option 2 needs the record updated by hand or with a Vercel API token on each start. Option 3 touches the whole domain. Option 4 breaks streaming or the licence terms.
- To verify on Day 7: that `duckdns.org` is on the Public Suffix List, so our Let's Encrypt rate limit isn't shared with other DuckDNS users.

## How I'd explain it to a client
"The demo uses a free dynamic-DNS name so it costs nothing and can sleep between demos. Your deployment would sit on your own domain with your own email sender. That's a config change, not a code change."
