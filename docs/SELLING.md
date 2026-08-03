# Selling & Multi-Client Deployment Guide

One codebase, many clients. Each client gets an isolated deployment configured
entirely through `.env` — no code changes per client.

## Why per-client instances (not one shared server)

- Complete data isolation: client A's tickets/conversations/documents can
  never leak to client B. This is a selling point for the client.
- Independent branding, credentials, integrations, and API quotas.
- One misbehaving client can't slow the others.
- You can upgrade clients one at a time.

## Per-client configuration checklist (`.env`)

| Variable | Set per client |
|---|---|
| `COMPANY_NAME` | Their company name (chat header, widget) |
| `BRAND_COLOR` | Their brand hex color |
| `CHAT_GREETING` | Their welcome message |
| `SECRET_KEY` | Fresh random value per client (JWT signing) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Their dashboard login |
| `GOOGLE_API_KEY` (or provider of choice) | Their key, or yours with billing tracked |
| `SLACK_WEBHOOK_URL`, `SLACK_SIGNING_SECRET` | Their Slack workspace |
| `TWILIO_*` | Their WhatsApp number |
| `SMTP_*`, `EMAIL_FROM` | Their email domain |
| `DATABASE_URL` | Per-instance DB (SQLite fine to start; Postgres at scale) |

## Onboarding workflow (~1–2 hours per client)

1. **Collect content**: FAQs, policies, product manuals, help articles,
   historical support tickets. Convert to the ingest JSON format
   (see `data/sample_docs.json`).
2. **Deploy an instance**:
   ```bash
   git clone <your-repo> client-name && cd client-name
   cp .env.example .env    # fill in the checklist above
   docker compose up -d --build
   ```
3. **Seed their knowledge base**:
   ```bash
   python scripts/seed_kb.py --base-url https://support.client.com \
       --email their-admin@client.com --password <their-password> \
       --file their_docs.json
   ```
4. **DNS + HTTPS**: point `support.client.com` at the instance behind a
   reverse proxy (Caddy or nginx + Let's Encrypt).
5. **Install the widget** on their site:
   ```html
   <script src="https://support.client.com/widget.js"></script>
   ```
6. **Handover**: give them the `/admin` dashboard login. The deflection rate
   and CSAT numbers on that dashboard justify the monthly invoice.

## Pricing models

- **Setup + retainer**: $1,000–3,000 setup (content ingestion, branding,
  channel hookup) + $200–500/month (hosting, monitoring, KB updates).
- **Per-resolution**: charge per AI-resolved conversation (the dashboard's
  deflection metrics give you the billing number).
- **Volume tiers**: price by conversations/month.

## Cost structure (your side)

- One $20–40/month VPS runs 5–10 client instances via Docker.
- Gemini paid tier: fractions of a cent per answer; ~1,000 conversations/month
  ≈ a few dollars per client. Free tier is fine for demos but suffers
  503 congestion — never demo or run production on it.

## Demo strategy that closes deals

1. Scrape/copy the prospect's public FAQ and help pages into the ingest JSON.
2. Stand up a demo instance with THEIR branding (10 minutes of work).
3. In the meeting, let them ask it their own customers' real questions,
   and show the escalation flow and dashboard live.
4. Leave the demo URL with them for a week.

## Before charging money — hardening checklist

- [ ] `ENVIRONMENT=production`, strong `SECRET_KEY`, non-default admin password
- [ ] HTTPS via reverse proxy; only ports 80/443 exposed
- [ ] Gemini paid tier (no 503s, no daily quota)
- [ ] Postgres + backups for clients with real volume
- [ ] Monitoring: `/health` checked by an uptime service
- [ ] A privacy note for their site (chats are processed by an AI provider)
