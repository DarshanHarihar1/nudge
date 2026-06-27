# Phase 2 — Discipline Engine

**Goal:** Add the features that enforce financial discipline: balance check & reconciliation, recurring deductions (SIP, rent, maid), and per-category budgets with alerts. End of this phase: the bot actively holds you accountable.

**Depends on:** Phase 1 complete. `users`, `categories`, `expenses` tables and bot infrastructure in place.

---

## Scope

- DB tables: `balance_snapshots`, `recurring_items`, `reconciliations`
- Balance prompt cron + balance capture (no LLM)
- Reconciliation math + bot report
- Recurring items: daily `apply-recurring` cron + bot notifications
- Per-category budgets: alert on 80% and 100% of monthly budget
- Bot commands: `/balance`, `/budget`
- GitHub Actions workflows for all cron jobs (including keep-warm)
- Dashboard API stubs for recurring and categories (CRUD — UI comes in Phase 3)

---

## Milestones

### M2.1 — Extend schema
- Add `balance_snapshots`, `recurring_items`, `reconciliations` tables to `packages/db`
- Add `monthly_budget` column to `categories` (nullable)
- Add migration; run against Supabase
- Add typed helpers: `createBalanceSnapshot()`, `getLatestSnapshot()`, `createReconciliation()`, `listRecurringItems()`, `applyRecurringItem()`

**Done when:** Migration runs cleanly; all helpers have TypeScript types and compile.

### M2.2 — Balance capture
- Parse numeric balance from text with regex (no LLM): handles `48200`, `48,200`, `₹48200`, `48k`
- `/balance <amount>` command writes to `balance_snapshots`
- Bot enters "awaiting balance" state (grammY session or in-memory map) after the cron prompt; the next numeric message is captured as a balance reply even without the command

**Done when:** Unit tests cover all regex cases; `/balance 48200` and `₹48,200` both write the correct numeric value.

### M2.3 — Balance prompt cron
- `POST /api/cron/balance-prompt` — validates `CRON_SECRET`, sends *"💰 Balance check — reply with your current bank balance."* to the whitelisted user
- GitHub Actions workflow: runs every 14 days
- The endpoint is idempotent — calling it twice in one day sends at most one prompt (track last-sent date in a simple KV or the users table)

**Done when:** Manual trigger of the endpoint sends the Telegram message; second call within 24h is a no-op.

### M2.4 — Reconciliation
- On balance capture, if a previous `balance_snapshots` row exists:
  - Compute `period_start` (prev snapshot `recorded_at`), `period_end` (now)
  - Sum `expenses` in period (excluding recurring that will be counted separately)
  - Sum `recurring_items` applied in period from `expenses` where `source='recurring'`
  - `expected_close = opening - logged_total - recurring_total + recurring_credits`
  - `discrepancy = expected_close - closing_balance`
  - Write `reconciliations` row
  - Bot reports: *"📊 Reconciliation: Expected ₹46,800 · Actual ₹44,500 · Gap ₹2,300 unaccounted."*
  - If `|discrepancy| < 100` (configurable): *"✅ Accounts balance within ₹100."*

**Done when:** Unit tests for reconciliation math pass across 5+ scenarios (credits, debits, zero gap, large gap); integration test writes correct row.

### M2.5 — Recurring items backend
- `packages/bot` CRUD helpers used by the API routes
- `POST /api/cron/apply-recurring` — validates secret, finds items where `day_of_month == today(IST)` and `last_applied_on` is not this month's first-of-month; creates `expenses` rows; updates `last_applied_on`
- Bot sends confirmation per applied item: *"🏠 Rent ₹15,000 applied."*
- Idempotent: running twice in one day applies each item at most once

**Done when:** Running the endpoint on the 1st of the month applies all day-1 items exactly once; a second run applies nothing.

### M2.6 — Per-category budget alerts
- On every new expense (confirmed), compute month-to-date sum for its category
- If sum / `monthly_budget` ≥ 0.80 and < 1.0: bot warns ⚠️ at 80%
- If sum / `monthly_budget` ≥ 1.0: bot warns 🚨 at 100%
- Send at most one 80% alert and one 100% alert per category per month (deduplicate via a simple check against the last alert sent, or a flag in categories)
- Categories without a budget set: no alert

**Done when:** Manual test: set Food budget ₹1,000; log ₹850 food expense; confirm 80% alert fires. Log another ₹200; confirm 100% alert fires. Log again; confirm no duplicate 100% alert.

### M2.7 — Bot commands
- `/balance <amount>` — records balance, triggers reconciliation if a previous snapshot exists
- `/budget` — lists all categories with budgets: shows MTD spend / budget / percentage bar

**Done when:** Both commands return correctly formatted messages in manual testing.

### M2.8 — GitHub Actions workflows
- `.github/workflows/cron-apply-recurring.yml` — daily 00:05 IST (`30 18 * * *` UTC)
- `.github/workflows/cron-balance-prompt.yml` — every 14 days
- `.github/workflows/cron-weekly-summary.yml` — Sun 19:00 IST (`30 13 * * 0` UTC) *(stub; full implementation Phase 3)*
- `.github/workflows/cron-monthly-summary.yml` — 1st 09:00 IST (`30 3 1 * *` UTC) *(stub)*
- `.github/workflows/keep-warm.yml` — every 10 min GET `/api/health` (prevents Render cold start and Supabase inactivity pause)
- All workflows use GitHub Actions secrets for `CRON_SECRET` and `APP_URL`

**Done when:** All workflows are committed; `apply-recurring` fires correctly in a manual dispatch test.

### M2.9 — Dashboard API stubs for Phase 3 readiness
- `GET /api/dashboard/analytics` — returns empty `{}` with 200 (placeholder)
- `CRUD /api/dashboard/recurring` — full CRUD backed by `recurring_items` table (used by Phase 3 UI)
- `CRUD /api/dashboard/categories` — GET and PATCH `monthly_budget` (used by Phase 3 UI)

**Done when:** Postman/curl tests against all endpoints return expected shapes.

---

## Testing Criteria

### Unit Tests (Vitest)

| Test | What it verifies |
|---|---|
| Balance regex parser | `"48,200"`, `"₹48200"`, `"48k"`, `"48.5k"` all parse correctly |
| Balance regex parser | `"hello"`, `""`, `"abc123"` return `null` |
| Reconciliation math | `expected_close` computed correctly with debits, credits, recurring |
| Reconciliation math | Zero discrepancy when numbers balance exactly |
| Reconciliation math | Negative discrepancy (overspend) reported correctly |
| `apply-recurring` idempotency | Same item not applied twice in one month |
| `apply-recurring` day matching | Item with `day_of_month=5` applied on the 5th, not on the 4th or 6th |
| Budget alert threshold | 80% alert fires at exactly 80%; no alert at 79% |
| Budget alert deduplication | Second expense crossing 80% in same month does not re-send alert |

### Integration Tests

| Test | What it verifies |
|---|---|
| POST `/api/cron/apply-recurring` with valid secret | Creates `expenses` rows with `source='recurring'`; updates `last_applied_on` |
| POST `/api/cron/apply-recurring` called twice same day | Second call creates no new rows |
| POST `/api/cron/balance-prompt` | Telegram message sent to whitelisted user |
| `/balance 48200` via bot | `balance_snapshots` row created; reconciliation computed if prior snapshot exists |
| CRUD `/api/dashboard/recurring` | Create, read, update, delete recurring item |

### Manual / E2E Checklist

- [ ] Run `apply-recurring` cron manually on day matching a configured item → expense appears in `/recent`
- [ ] Set category budget, log expenses → 80% alert fires at correct threshold
- [ ] Log another expense → 100% alert fires, no duplicate alert on further spend
- [ ] Send numeric reply after balance prompt → reconciliation report sent
- [ ] `/budget` shows correct MTD spend and percentage for each category
- [ ] Reconciliation math: manually verify expected vs actual with known numbers

---

## Definition of Done

- All unit and integration tests pass
- Manual E2E checklist complete
- GitHub Actions workflows committed and manually dispatched successfully
- Reconciliation math verified against a hand-calculated test case
- API stubs in place for Phase 3

---

## Concerns & Risks

1. **IST timezone handling** — `day_of_month` for `apply-recurring` must use IST (UTC+5:30), not UTC. A cron running at `00:05 IST` is `18:35 UTC` the previous day. Use `Intl.DateTimeFormat` with `Asia/Kolkata` or a library like `date-fns-tz` for all date comparisons. This is the most likely source of subtle bugs.

2. **Supabase free tier inactivity pause** — After 7 days of no activity, free Supabase projects pause and require a manual resume. The keep-warm workflow must hit an actual DB query (e.g., `SELECT 1`), not just the health endpoint, to count as activity. Add a `/api/health/db` endpoint that does a lightweight query.

3. **Reconciliation double-counting** — Recurring items are logged as `expenses` rows (`source='recurring'`). The reconciliation query must correctly separate manually logged expenses from recurring ones to avoid double-counting. The `source` column is the discriminator — make this explicit in the query.

4. **Balance prompt state management** — grammY's conversation/session for "awaiting balance reply" needs a persistence layer (not in-memory) on Render, since the service may restart between the prompt being sent and the user replying. Use `packages/db` to store a `awaiting_balance: bool` flag on the `users` table, or a lightweight KV in Supabase.

5. **Budget alert spam** — If the user logs many expenses rapidly, the 80%/100% alerts could fire multiple times. The deduplication logic (send at most one 80% and one 100% per category per calendar month) must be reliable. Store the last alert timestamps in a new column on `categories` or a separate `budget_alerts` table.
