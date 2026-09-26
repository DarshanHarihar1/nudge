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

## Gmail setup (bank debit alerts)

Gmail pushes a notification to Cloud Pub/Sub the moment a bank alert lands;
Pub/Sub POSTs it to `/email/gmail-push`, which fetches the mail and logs the
expense (`services/gmail_sync.py`). One-time setup:

1. **Gmail filter.** In Gmail → Settings → Filters → Create filter:
   From `noreplyubi-txn@ubi.bank.in` → *Apply the label* → new label `nudge-bank`.
   (Also tick *Also apply filter to matching conversations*.)
2. **Google Cloud project.** At console.cloud.google.com create a project
   (e.g. `nudge-gmail`). Enable **Gmail API** and **Cloud Pub/Sub API**
   (APIs & Services → Library). Pub/Sub may ask you to attach a billing
   account — usage stays inside the free tier.
3. **OAuth consent screen.** Google Auth Platform → Branding: app name
   `nudge`, your email. Audience: *External*, add yourself as a test user,
   then click **Publish app** so it shows *In production*. Skip this and
   the refresh token dies after 7 days. You'll see an "unverified app"
   warning when signing in — that's expected for a personal app.
4. **OAuth client.** Google Auth Platform → Clients → Create client →
   type **Desktop app**. Put its ID and secret in `apps/api/.env` as
   `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET`.
5. **Refresh token + label ID.** `cd apps/api && .venv/bin/python scripts/gmail_auth.py`
   → sign in, allow read access → copy the printed `GMAIL_REFRESH_TOKEN`
   and `GMAIL_LABEL_ID` into `.env`.
6. **Pub/Sub topic.** Pub/Sub → Topics → Create topic `gmail-bank`
   (untick "Add a default subscription"). Topic → Permissions → Add principal
   `gmail-api-push@system.gserviceaccount.com` with role **Pub/Sub Publisher**
   (without this, the watch "succeeds" but nothing is ever delivered).
   `GMAIL_PUBSUB_TOPIC=projects/<project-id>/topics/gmail-bank`.
7. **Push subscription.** Pick a random `GMAIL_PUSH_TOKEN`
   (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`). On the
   topic → Create subscription: delivery type **Push**, endpoint
   `https://nudge-api-va33.onrender.com/email/gmail-push?token=<GMAIL_PUSH_TOKEN>`,
   acknowledgement deadline **60** seconds.
8. **Render.** Add all six `GMAIL_*` vars to the `nudge-api` service's
   environment, and deploy.
9. **Start the watch.** GitHub → Actions → *Renew Gmail Watch* → Run workflow.
   It runs daily after that (the watch expires after 7 days) and pings
   Telegram if renewal fails.

## Layout

```
apps/api/
├── main.py              # FastAPI app: /webhook, /health, mounts routers
├── config.py            # env-var loading
├── ai/
│   ├── llm.py           # Gemini API JSON calls (Gemma → Flash fallback)
│   ├── classify.py      # expense classification
│   └── nl_query.py      # NL question → allowlisted {function, params}
├── bot/
│   ├── application.py    # PTB handler registration
│   ├── commands/        # /start /recent /undo /clear /restore /budget /ask /help
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
| POST | `/email/gmail-push?token=` | `GMAIL_PUSH_TOKEN` | Cloud Pub/Sub push → bank debit-alert ingestion |
| GET | `/health` | public | Keep-warm + DB ping |
| GET | `/auth/telegram/callback` | widget signature | Login → set session cookie |
| POST | `/auth/logout` | — | Clear session |
| GET | `/auth/session` | session | Current session info |
| POST | `/cron/apply-recurring` | Bearer `CRON_SECRET` | Apply due recurring items |
| POST | `/cron/weekly-summary` | Bearer `CRON_SECRET` | Weekly digest |
| POST | `/cron/monthly-summary` | Bearer `CRON_SECRET` | Monthly digest + detection |
| POST | `/cron/gmail-watch` | Bearer `CRON_SECRET` | Renew Gmail watch + catch up |
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
