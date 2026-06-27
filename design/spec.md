# Personal Finance Tracker Bot — Design & Tech Spec

**Version:** 1.1 (moved to `design/` and updated for monorepo)
**Goal:** Build discipline around personal finances by logging every expense via a Telegram chat, auto-classifying it, periodically reconciling against actual bank balance, and visualizing everything in a dashboard.

---

## 1. Overview & Principles

You message the bot in plain language whenever you spend ("250 lunch with team"). It extracts the amount, classifies the category, stores it, and confirms. Every ~2 weeks the bot asks for your bank balance, then **reconciles** logged spend against the real balance drop to catch anything you forgot to log. A Next.js dashboard shows trends, budgets, net worth, and lets you configure recurring deductions (SIP, rent, maid, etc.).

**Design principles**
- **Single user, low volume.** Optimize for simplicity and free tiers, not scale.
- **LLM only where language is ambiguous.** Parsing free-text expenses needs an LLM; parsing a balance number does not. Keep deterministic things deterministic — cheaper, faster, and sensitive numbers never leave your stack.
- **Monorepo, one language.** pnpm workspaces + Turborepo. Shared `packages/` for DB, bot logic, and AI wrappers; one `apps/web` Next.js app for dashboard + API + webhook. One deploy.
- **Groq-first LLM.** Groq is the sole LLM provider; OpenRouter is a last-resort fallback when the daily quota is hit. All LLM calls go through `@nudge/ai` so swapping providers never touches business logic.

---

## 2. Monorepo Structure

```
nudge/
├── apps/
│   └── web/                  # Next.js (App Router, TS) — dashboard + API routes + webhook
├── packages/
│   ├── db/                   # Drizzle schema, migrations, typed db client
│   ├── bot/                  # grammY handlers, command definitions, middleware
│   ├── ai/                   # Vercel AI SDK wrappers, provider fallback chain
│   └── config/               # Shared tsconfig, eslint, prettier configs
├── .github/
│   └── workflows/            # Cron jobs (apply-recurring, balance-prompt, summaries)
├── package.json              # Root — workspaces: ["apps/*","packages/*"]
├── pnpm-workspace.yaml
├── turbo.json
└── design/                   # This directory
```

**Package responsibilities:**
| Package | Exports |
|---|---|
| `@nudge/db` | `db` client, `schema`, `migrate()`, typed query helpers |
| `@nudge/bot` | `createBot(db, ai)`, all handler functions, middleware |
| `@nudge/ai` | `classifyExpense()`, `mapNLQuery()`, `generateSummaryInsight()` |
| `@nudge/config` | `tsconfig/base.json`, `eslint/base.js` |
| `apps/web` | Next.js routes, React pages, cron endpoints |

---

## 3. Architecture

```
                ┌─────────────────────────────────────────────┐
   Telegram ───▶│  apps/web (Render Web Service)               │
   (you)        │                                              │
                │  /api/telegram/webhook   ← bot messages      │
                │  /api/cron/*             ← scheduled jobs    │──▶ Groq (llama-3.1-8b-instant)
                │  /api/dashboard/*        ← data for UI       │    OpenRouter fallback
                │  /dashboard (React UI)                       │    on daily quota
                │                                              │
                └───────────────┬──────────────────────────────┘
                                │
                                ▼
                     Supabase Postgres (free)
                                ▲
                                │
   External cron (GitHub Actions) ── hits /api/cron/* on schedule
```

- **Inbound from Telegram:** webhook (not long-polling) — Render provides a public HTTPS URL.
- **Scheduling:** GitHub Actions scheduled workflows POST to secured `/api/cron/*` endpoints. Also acts as a keep-warm ping to prevent Render cold starts.
- **Dashboard auth:** Telegram Login Widget — same Telegram account that owns the bot.

---

## 4. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| App framework | **Next.js 14 (App Router, TypeScript)** | One app for UI + API + webhook |
| Monorepo tooling | **pnpm workspaces + Turborepo** | Fast builds, shared packages, one lock file |
| Telegram lib | **grammY** | Modern, TS-first, first-class webhook support |
| Database | **Supabase Postgres** (free) | Managed, persistent, already in your toolset |
| ORM | **Drizzle ORM** | Lightweight, typed SQL, easy migrations |
| Input validation | **Zod** | Validate LLM JSON output; shared across packages |
| LLM access | **Vercel AI SDK** | Thin abstraction; swap providers without touching business logic |
| LLM (primary) | **Groq** — `llama-3.1-8b-instant` | 14,400 RPD · 500K TPD · 30 RPM · sub-200ms · no training data use |
| LLM (fallback) | **OpenRouter** (`:free` model) | Last resort when Groq daily quota is exhausted |
| Charts | **Recharts** | Simple, good-looking React charts |
| Hosting (app) | **Render** Web Service | Public URL for webhook |
| Scheduler | **GitHub Actions cron** | Free, reliable, keeps service warm |

---

## 5. Data Model (Postgres)

```sql
users
  id              uuid pk
  telegram_id     bigint unique      -- whitelist: only you can use the bot
  name            text
  base_currency   text default 'INR'
  created_at      timestamptz

categories
  id              uuid pk
  user_id         uuid fk → users.id
  name            text               -- Food, Transport, Rent...
  emoji           text
  monthly_budget  numeric null       -- null = no budget set
  is_active       bool default true

expenses
  id              uuid pk
  user_id         uuid fk → users.id
  amount          numeric
  currency        text default 'INR'
  category_id     uuid fk → categories.id
  merchant        text null
  note            text null
  raw_text        text               -- original message, always kept for re-classification
  source          text               -- 'telegram' | 'manual' | 'recurring'
  status          text default 'confirmed' -- 'confirmed' | 'pending'
  confidence      numeric null       -- LLM classifier confidence (0-1)
  llm_provider    text null          -- 'groq' | 'openrouter' (debug/analytics)
  spent_at        timestamptz
  created_at      timestamptz

balance_snapshots
  id              uuid pk
  user_id         uuid fk → users.id
  balance         numeric
  currency        text default 'INR'
  recorded_at     timestamptz
  note            text null

recurring_items                       -- SIP, rent, maid, subscriptions
  id              uuid pk
  user_id         uuid fk → users.id
  name            text
  amount          numeric
  category_id     uuid fk → categories.id
  direction       text default 'debit' -- 'debit' | 'credit' (e.g. salary)
  day_of_month    int                -- 1..28 (clamp to month end)
  is_active       bool default true
  start_date      date
  end_date        date null
  last_applied_on date null          -- idempotency guard

reconciliations
  id              uuid pk
  user_id         uuid fk → users.id
  period_start    timestamptz
  period_end      timestamptz
  opening_balance numeric
  closing_balance numeric
  logged_total    numeric            -- expenses logged in period
  recurring_total numeric            -- recurring items applied in period
  expected_close  numeric
  discrepancy     numeric            -- expected_close − closing_balance
  created_at      timestamptz
```

**Supabase RLS policies to add for every table:**
```sql
-- Example for expenses:
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_owns_expenses" ON expenses
  USING (user_id = auth.uid());
```
Apply equivalent policies to all tables. The API layer enforces `user_id` on every query; RLS is a belt-and-suspenders backstop.

---

## 6. Feature Specifications

### 6.1 Expense logging & classification
- **Trigger:** any free-text message that isn't a command or a query.
- **Pipeline:** message → `@nudge/ai`.`classifyExpense()` → Zod-validated `{amount, currency, category, merchant, note, confidence}`.
- **Taxonomy (seed):** Food, Groceries, Transport, Rent, Utilities, Entertainment, Shopping, Health, Subscriptions, Education, Misc. Stored in `categories` — add/edit later.
- **Always store `raw_text`** so you can re-run classification if you refine the taxonomy.
- Use structured-output / JSON mode so the LLM never returns unstructured prose.

### 6.2 Confirmation & quick edit
- After logging, bot replies: `Logged ₹250 → Food 🍴` with inline keyboard:
  `[✅ OK] [✏️ Recategorize] [🗑 Delete]`.
- Recategorize opens an inline list of categories; tapping one updates the row.
- Corrections stored — over time use as few-shot examples in the prompt.

### 6.3 Balance check & reconciliation *(the discipline engine)*
- **Schedule:** cron every 14 days: *"💰 Balance check — reply with your current bank balance."*
- **Capture:** next numeric reply (or `/balance 48200`) parsed **without the LLM** (regex) and stored in `balance_snapshots`. Sensitive number never leaves your stack.
- **Reconcile:**
  ```
  expected_close = opening_balance
                 − Σ(logged expenses in period)
                 − Σ(recurring debits applied in period)
                 + Σ(recurring credits, e.g. salary)
  discrepancy    = expected_close − actual_close
  ```
- Bot reports: *"Expected ₹46,800, actual ₹44,500 → ₹2,300 unaccounted. Anything you forgot to log?"*

### 6.4 Per-category budgets & alerts
- `categories.monthly_budget` sets a cap.
- On every new expense, compute month-to-date total; if it crosses **80%** or **100%**, bot warns: *"⚠️ Food: ₹4,100 / ₹5,000 this month (82%)."*

### 6.5 Recurring deductions
- **Configured in dashboard:** name, amount, category, day of month, direction, active toggle, optional end date. Examples: SIP ₹10,000 on 5th, Rent ₹15,000 on 1st.
- **Daily cron `apply-recurring`:** finds items where `day_of_month == today` and `last_applied_on != this month`, creates `expenses` row with `source='recurring'`, sets `last_applied_on`. Idempotent.
- Bot confirms: *"🏠 Applied recurring: Rent ₹15,000."*
- Flows into budgets and reconciliation automatically.

### 6.6 Recurring-expense detection *(suggestion engine)*
- Weekly job scans for repeated similar expenses (same/similar merchant + amount, ~monthly cadence) not already in `recurring_items`.
- Suggests: *"Looks like 'Netflix ₹649' recurs monthly — add it as a recurring item? [Yes] [No]"*

### 6.7 Natural-language queries
- Detect intent: messages ending with `?` or starting with `/ask`.
- **Safe pattern:** LLM maps your question to one of a few **predefined parameterized query functions** (`sumByCategory(range)`, `topMerchants(range)`, `totalSpend(range)`). Your code runs the actual query — no LLM-generated SQL, no injection risk.
- Examples: *"how much on food this month?"*, *"what did I spend most on last week?"*

### 6.8 Automatic summaries
- **Weekly** (Sun evening) and **monthly** (1st) cron posts a digest: total spend, top 3 categories, budget status, savings rate, reconciliation status.
- Generated from **templates** (no LLM needed) to conserve rate limits; optionally one LLM call for a one-line insight.

### 6.9 Savings rate & net worth
- Derived from `balance_snapshots` over time + recurring credits (income).
- Dashboard shows: balance trend line, period-over-period savings, savings rate = `(income − expenses) / income`.

---

## 7. LLM Usage & Rate-Limit Strategy

**Where the LLM is used:** expense classification, NL-query intent mapping, optional summary flavor.
**Where it is NOT used:** balance parsing, recurring application, budget math, reconciliation, summaries. Deterministic = cheaper, faster, private.

**Provider strategy (via Vercel AI SDK — manual fallback chain):**
```ts
// packages/ai/src/classify.ts
async function classifyExpense(text: string) {
  for (const provider of [groq, openrouter]) {
    try {
      return await provider.classify(text);
    } catch (err) {
      if (!isRateLimitError(err)) throw err;
      // continue to next provider
    }
  }
  throw new Error('All LLM providers exhausted');
}
```
- Primary: **Groq** (`llama-3.1-8b-instant`) — 14,400 RPD · 500K TPD · 30 RPM · no training data use.
- Fallback: **OpenRouter** (`:free` model) — last resort when Groq daily quota is hit.

**Rate limit headroom:** Each classification call ≈ 300–400 tokens (8b model with a concise prompt). Even 100 calls/day ≈ 35K tokens — well under the 500K TPD cap. The binding constraint at human-paced logging is RPM (30/min), which is never a concern in normal use.

---

## 8. Telegram Bot UX

**Free text**
- Expense: `250 lunch`, `cab to airport 480`, `bought shoes 2999`
- Query: `how much on food this month?`

**Commands**
- `/start` — register (whitelists your `telegram_id`)
- `/balance <amount>` — record balance
- `/recent` — last 10 expenses
- `/summary` — on-demand digest
- `/budget` — current budgets vs spend
- `/undo` — delete the last expense
- `/help`

**Security:** only the whitelisted `telegram_id` is served; all others are silently ignored. The webhook validates Telegram's `X-Telegram-Bot-Api-Secret-Token` header on every request.

---

## 9. API Surface (Next.js route handlers in `apps/web`)

```
POST /api/telegram/webhook        -- bot updates (secret-token protected)
GET  /api/health                  -- keep-warm ping (public)
POST /api/cron/balance-prompt     -- ask for balance (every 14 days)
POST /api/cron/apply-recurring    -- apply due recurring items (daily 00:05)
POST /api/cron/weekly-summary     -- weekly digest (Sun 19:00)
POST /api/cron/monthly-summary    -- monthly digest + detection scan (1st 09:00)
GET  /api/dashboard/expenses      -- list/filter (auth required)
GET  /api/dashboard/analytics     -- aggregates for charts (auth required)
CRUD /api/dashboard/recurring     -- manage recurring items (auth required)
CRUD /api/dashboard/categories    -- manage categories/budgets (auth required)
```
All `/api/cron/*` endpoints require `Authorization: Bearer <CRON_SECRET>` header.

---

## 10. Dashboard (`apps/web`)

- **Overview:** current balance, this-month spend, savings rate, reconciliation status banner.
- **Spending:** category breakdown (pie), spend-over-time (line), budget bars.
- **Net worth:** balance trend from snapshots.
- **Recurring:** table + form to add/edit SIP/rent/maid/subscriptions.
- **Transactions:** searchable, filterable, editable expense list.
- **Auth:** Telegram Login Widget → signed session cookie (24h); gate all `/dashboard/*` routes.

---

## 11. Deployment

**Render Web Service** (`apps/web`)
- Root dir: `apps/web`; build command: `pnpm --filter @nudge/web build`; start: `pnpm --filter @nudge/web start`
- Env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `DATABASE_URL`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CRON_SECRET`, `SESSION_SECRET`.
- On first deploy, run: `curl -X POST https://<app>.onrender.com/api/telegram/setWebhook`

**Database:** Supabase Postgres. Migrations run as part of the deploy build step (`drizzle-kit push` or `migrate()`).

**Scheduling (GitHub Actions):**
- `apply-recurring` — daily 00:05 IST
- `balance-prompt` — every 14 days
- `weekly-summary` — Sun 19:00 IST
- `monthly-summary` — 1st 09:00 IST
- `keep-warm` — every 10 min GET `/api/health` (prevents Render cold starts)

---

## 12. Security & Privacy Checklist

- [ ] Bot whitelists your `telegram_id`; silently ignores all others.
- [ ] Telegram webhook validates `X-Telegram-Bot-Api-Secret-Token` header.
- [ ] `/api/cron/*` requires `Authorization: Bearer <CRON_SECRET>`.
- [ ] Dashboard behind Telegram Login Widget session (cookie, 24h TTL).
- [ ] Balances and reconciliation numbers **never sent to any LLM**.
- [ ] All secrets in Render env vars and GitHub Actions secrets — never in the repo.
- [ ] Supabase RLS on every table, keyed on `user_id`.
- [ ] LLM JSON output validated with Zod before persisting.
- [ ] `raw_text` stored but never logged to any external system.

---

## 13. Known Concerns & Open Questions

See phase docs for per-phase concerns. Cross-cutting issues:

1. **grammY + Next.js App Router body parsing** — The webhook needs the raw body for secret-token header validation. Next.js App Router may buffer the body; test this explicitly in Phase 1 with a dedicated integration test.
2. **Render free tier cold starts** — The keep-warm GitHub Actions workflow (GET `/api/health` every 10 min) mitigates this, but verify Render's current free-tier sleep threshold before launch (it has changed before).
3. **Telegram Login Widget session** — Widget tokens expire after 24h. Implement a refresh or re-login redirect. Also requires your bot's domain to be set via `@BotFather` → `setDomain`.
4. **LLM fallback is manual, not automatic** — Vercel AI SDK does not auto-retry across providers on 429. The two-step fallback chain (Groq → OpenRouter) in `@nudge/ai` must be explicitly implemented and tested.
5. **Supabase free tier has inactivity pause** — After 7 days of no API calls, the free Supabase project pauses. The keep-warm ping should also query the DB to prevent this, or upgrade to a paid tier.

---

## 14. Cost Summary

| Item | Cost |
|---|---|
| Telegram Bot API | Free |
| Groq `llama-3.1-8b-instant` | Free tier (14,400 RPD · 500K TPD) |
| OpenRouter fallback | Free tier |
| Supabase Postgres | Free tier |
| GitHub Actions | Free (2,000 min/mo on free plan) |
| Render Web Service | Free (sleeps) or ~$7/mo always-on |

**Effectively $0** to run; optional ~$7/mo to remove cold starts.
