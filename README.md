# Nudge

A personal finance tracker built around a Telegram bot. Log expenses in plain
English ("250 lunch with team"), let an LLM classify them, and review
everything in a Next.js dashboard — spending breakdown, trends, recurring
bills, and activity history.

## How it works

- **Log expenses via Telegram** — type any free-text message and Nudge
  extracts the amount, category, and merchant automatically.
- **Ask questions** — end a message with `?` (or use `/ask`) to query your
  spending in natural language ("how much on food this month?").
- **Recurring bills** — configure rent, subscriptions, SIPs, etc. from the
  dashboard; a daily cron logs them automatically on the right day of the
  month.
- **Daily nudges** — three reminders a day to log expenses, plus a 9pm daily
  spend summary, and weekly/monthly digests.
- **iPhone Shortcut support** — log expenses straight from a bank SMS
  notification without opening Telegram (`GET /shortcut/expense`).
- **Dashboard** — Telegram Login Widget-gated web UI with spending
  breakdown, category budgets, recurring items, and transaction history.

## Architecture

```
Telegram ──▶ apps/api (FastAPI, Render)  ──▶ Groq / OpenRouter (expense classification)
                    │
                    ▼
          Supabase Postgres (asyncpg)
                    ▲
                    │
apps/web (Next.js, Vercel) ──▶ dashboard, reads/writes via apps/api

GitHub Actions (cron) ──▶ hits /cron/* endpoints on schedule
```

- **`apps/api`** — Python/FastAPI backend. Owns the Telegram webhook, all
  business logic, and the dashboard API. See [`apps/api/README.md`](apps/api/README.md)
  for the full HTTP surface and local dev instructions.
- **`apps/web`** — Next.js (App Router) dashboard. Talks to `apps/api` over
  HTTP using a signed session cookie set by Telegram Login.
- **`.github/workflows`** — scheduled jobs (recurring items, reminders,
  daily/weekly/monthly summaries, keep-warm ping) that call `apps/api`'s
  `/cron/*` endpoints with a shared bearer secret.
- **`packages/`** — shared TS config for the web app (`@nudge/config`).
  Legacy `db`/`bot`/`ai` TS packages are unused; the backend now lives
  entirely in `apps/api`.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + python-telegram-bot + asyncpg |
| Frontend | Next.js 16 (App Router, TypeScript) |
| Database | Supabase Postgres |
| LLM | Groq (primary), OpenRouter (fallback) |
| Backend hosting | Render |
| Frontend hosting | Vercel |
| Scheduling | GitHub Actions cron |

## Getting started

### Backend (`apps/api`)

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env   # fill in values — see below
uvicorn main:app --reload --port 8000
```

### Frontend (`apps/web`)

```bash
pnpm install
pnpm --filter @nudge/web dev
```

### Environment variables

Copy `.env.example` at the repo root for the full list (Telegram bot token,
Supabase connection string, Groq/OpenRouter keys, cron secret, session
secret, app URLs). Required by `apps/api`; `apps/web` only needs the API's
public URL.

## Monorepo commands

Run from the repo root (pnpm + Turborepo):

```bash
pnpm dev          # run all TS workspaces in dev mode
pnpm build        # build all TS workspaces
pnpm lint         # lint all TS workspaces
pnpm typecheck    # typecheck all TS workspaces
```

The Python backend isn't part of the Turborepo pipeline — run it directly
from `apps/api` as shown above. Backend tests: `cd apps/api && python -m pytest tests/ -q`.

## Design docs

The `design/` directory has the original phased design spec. It predates the
move from a Next.js/Drizzle backend to the current Python/FastAPI backend, so
treat it as historical context for the product's intent rather than an
accurate description of the current implementation — `apps/api/README.md` is
the source of truth for the live API.
