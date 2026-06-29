# Nudge API (Python backend)

FastAPI + python-telegram-bot + asyncpg backend for the Nudge personal finance
tracker. Handles the Telegram webhook, scheduled cron jobs, intelligence
features, and the dashboard API.

## Run locally

```bash
cd apps/api
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn main:app --reload --port 8000
```

After deploying, point Telegram at the webhook:

```bash
python scripts/register_webhook.py
```

## Layout

```
apps/api/
├── main.py              # FastAPI app: /webhook, /health, mounts routers
├── config.py            # env-var loading
├── ai/
│   ├── classify.py      # expense classification (Groq → OpenRouter fallback)
│   └── nl_query.py      # NL question → allowlisted {function, params}
├── bot/
│   ├── application.py    # PTB handler registration
│   ├── commands/        # /start /recent /undo /budget /ask /help
│   └── handlers/        # text router, expense, nl_query, suggestion callbacks
├── db/
│   ├── client.py        # asyncpg pool
│   └── queries.py       # all SQL
├── routers/
│   ├── auth.py          # Telegram Login Widget → signed session cookie
│   ├── cron.py          # /cron/* (Bearer CRON_SECRET)
│   └── dashboard.py     # /dashboard/* (session cookie or Bearer)
├── services/            # recurring, summary, detection, analytics
├── utils/               # pure logic: ranges, finance, detection, session, etc.
└── tests/               # pytest (pure-logic unit tests)
```

## HTTP API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/webhook` | Telegram secret header | Bot updates |
| GET | `/health` | public | Keep-warm + DB ping |
| GET | `/auth/telegram/callback` | widget signature | Login → set session cookie |
| POST | `/auth/logout` | — | Clear session |
| GET | `/auth/session` | session | Current session info |
| POST | `/cron/apply-recurring` | Bearer `CRON_SECRET` | Apply due recurring items |
| POST | `/cron/weekly-summary` | Bearer `CRON_SECRET` | Weekly digest |
| POST | `/cron/monthly-summary` | Bearer `CRON_SECRET` | Monthly digest + detection |
| GET | `/dashboard/analytics?from=&to=` | session | Charts data |
| GET | `/dashboard/expenses?page=&limit=&category=&from=&to=&q=` | session | Paginated list |
| PATCH | `/dashboard/expenses/{id}` | session | Edit an expense |
| GET/POST | `/dashboard/recurring` | session | List / create |
| PATCH/DELETE | `/dashboard/recurring/{id}` | session | Update / delete |
| GET | `/dashboard/categories` | session | Categories + budgets |
| PATCH | `/dashboard/categories/{id}` | session | Set monthly budget |

Dashboard routes accept either the session cookie (set after Telegram login) or
an `Authorization: Bearer <CRON_SECRET>` header (server-side / testing).

## Tests

```bash
cd apps/api && python -m pytest tests/ -q
```

## Security note

The backend connects to Postgres as the `postgres` role and enforces `user_id`
scoping in the API layer. RLS policies exist on every table as a backstop but
are currently permissive (`USING (true)`); the app does not use the Supabase
Data API. If you ever expose the Data API or distribute the anon key, tighten
these policies first.
