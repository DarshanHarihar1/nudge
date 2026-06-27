# Phase 1 — Core Loop (MVP)

**Goal:** A working Telegram bot that logs expenses, classifies them with an LLM, stores them in Postgres, and lets you review and undo. End of this phase: you can replace your current expense tracking habit with this bot.

**Dependencies:** None. This is the foundation everything else builds on.

---

## Scope

- Monorepo scaffold (pnpm workspaces, Turborepo, shared configs)
- `packages/db` — Drizzle schema for `users`, `categories`, `expenses`; typed client; migrations
- `packages/ai` — Vercel AI SDK wrapper with Groq primary + OpenRouter fallback; Zod-validated output
- `packages/bot` — grammY handlers, middleware, command routing
- `apps/web` — Next.js route for `/api/telegram/webhook` and `/api/health`
- Seed 11 default categories on first `/start`
- Commands: `/start`, `/recent`, `/undo`, `/help`
- Free-text expense logging → classify → confirm with inline keyboard
- Inline keyboard: ✅ OK, ✏️ Recategorize (opens category list), 🗑 Delete
- Deploy to Render; register webhook

---

## Milestones

### M1.1 — Monorepo scaffold
- Init pnpm workspace with `apps/web`, `packages/db`, `packages/ai`, `packages/bot`, `packages/config`
- Root `turbo.json` with `build`, `dev`, `lint` pipelines
- Shared `tsconfig/base.json` and `eslint/base.js` in `packages/config`
- `pnpm dev` starts `apps/web` in watch mode

**Done when:** `pnpm build` from root completes without errors across all packages.

### M1.2 — Database schema & migrations
- Define Drizzle schema: `users`, `categories`, `expenses` (Phase 1 tables only)
- Migration scripts via `drizzle-kit`
- Typed query helpers: `getUser()`, `createExpense()`, `listRecentExpenses()`, `deleteExpense()`
- `packages/db` exports `db`, `schema`, `migrate`

**Done when:** `migrate()` runs against a local Supabase instance and all three tables exist with correct columns and constraints.

### M1.3 — LLM classification
- `packages/ai` implements `classifyExpense(text: string): Promise<ClassifiedExpense>`
- Zod schema for output: `{amount, currency, category, merchant, note, confidence}`
- Groq primary (`llama-3.1-8b-instant`), OpenRouter fallback — try/catch chain
- System prompt with category taxonomy and strict JSON schema
- Store which provider was used in `llm_provider` column

**Done when:** `classifyExpense("250 lunch with team")` returns a valid Zod-parsed object from Groq; force a 429 mock and confirm OpenRouter fallback is called.

### M1.4 — Telegram webhook integration
- `apps/web/app/api/telegram/webhook/route.ts` — POST handler
- Validate `X-Telegram-Bot-Api-Secret-Token` header; return 403 on mismatch
- Parse body with grammY's `webhookCallback` adapter for Next.js App Router
- Middleware: whitelist check — if `telegram_id` is not in `users`, ignore silently (except `/start`)

**Done when:** A message sent to the bot appears in server logs and the webhook returns 200 within 5 seconds (Telegram's timeout).

### M1.5 — Expense logging flow
- Free-text handler: call `classifyExpense()`, write to `expenses` (status `'pending'`), reply with confirmation message and inline keyboard
- `✅ OK` — set status `'confirmed'`, update message to `Logged ₹250 → Food 🍴`
- `✏️ Recategorize` — send inline category list; on tap, update `category_id`, set `'confirmed'`
- `🗑 Delete` — delete the row, edit message to `Deleted.`
- Fallback: if LLM fails all providers, reply `Sorry, couldn't classify that. Try /manual or check again.` and do NOT write to DB

**Done when:** Manual end-to-end test: send "250 lunch", bot confirms, tap Recategorize → select Transport → row updated correctly.

### M1.6 — Bot commands
- `/start` — upsert `users` row, seed 11 default categories, reply with welcome message
- `/recent` — list last 10 `expenses` with amount, category, date; formatted as readable text
- `/undo` — delete the most recently created expense (user-owned); confirm with expense details
- `/help` — list all commands with brief descriptions

**Done when:** All four commands work correctly in manual testing.

### M1.7 — Health endpoint & deployment
- `GET /api/health` — returns `{status: "ok", ts: <iso>}`, no auth required
- Render deployment config: root dir `apps/web`, build/start commands
- Webhook registration: `setWebhook` script in `packages/bot/scripts/register-webhook.ts`
- Environment variables documented in `.env.example` at repo root

**Done when:** Bot is live on Render, webhook is registered, sending a message from Telegram logs the expense correctly in production Supabase.

---

## Testing Criteria

### Unit Tests (Vitest)

| Test | What it verifies |
|---|---|
| `classifyExpense("250 lunch")` | Returns `{amount: 250, category: "Food", confidence > 0.7}` |
| `classifyExpense("cab 480")` | Returns `{amount: 480, category: "Transport"}` |
| Zod schema validation | Malformed LLM JSON throws `ZodError`, not a silent failure |
| Provider fallback | Mocked 429 from Groq → OpenRouter is called |
| All providers exhausted | Throws `Error('All LLM providers exhausted')` |
| Webhook secret validation | Wrong token → handler returns early without processing |
| Whitelist middleware | Unknown `telegram_id` → handler returns early |
| `createExpense()` | Writes correct row; `raw_text` matches input |
| `deleteExpense()` | Row is removed; re-calling is a no-op (not an error) |

### Integration Tests

| Test | What it verifies |
|---|---|
| POST `/api/telegram/webhook` with valid secret | Returns 200, creates expense row in test DB |
| POST `/api/telegram/webhook` with wrong secret | Returns 403 |
| `/start` command | Creates `users` row + 11 `categories` rows |
| Full classify → confirm flow | `expenses.status` changes from `pending` to `confirmed` on OK tap |
| Recategorize flow | `expenses.category_id` updated correctly |
| Delete flow | Row absent after delete |

### Manual / E2E Checklist

- [ ] Send "800 groceries from dmart" → bot logs ₹800 → Groceries
- [ ] Tap Recategorize → select Shopping → category updated
- [ ] Send "paid 1200 electricity" → bot logs ₹1200 → Utilities
- [ ] `/recent` shows both entries in correct order
- [ ] `/undo` deletes the most recent; `/recent` no longer shows it
- [ ] Send a message from a non-whitelisted account → no response

---

## Definition of Done

- All unit and integration tests pass
- Manual E2E checklist complete
- Deployed to Render, live webhook responding
- `.env.example` documents every required variable
- `pnpm build` passes from root with zero TypeScript errors

---

## Concerns & Risks

1. **grammY + App Router body parsing** — Next.js App Router may buffer/transform the request body before grammY can read it. Test early with a raw `req.text()` read before passing to `webhookCallback`. If this breaks, the workaround is `export const dynamic = 'force-dynamic'` and using the `web` adapter.

2. **Telegram 5-second webhook timeout** — If Groq takes >5s (rare but possible), Telegram re-sends the update. Make the handler idempotent on `update_id` to avoid duplicate expenses. Add an `update_id` unique index or cache recent IDs in memory.

3. **Category seeding on `/start`** — If the user runs `/start` twice, you'll get duplicate categories. Use `ON CONFLICT DO NOTHING` in the insert, keyed on `(user_id, name)`.

4. **LLM currency extraction** — The spec assumes INR, but amounts like "800 USD shoes" should be handled. The `currency` field exists in the schema — make sure the LLM prompt explicitly asks for it and defaults to `INR` when not specified.
