# Phase 3 — Dashboard & Intelligence

**Goal:** Full Next.js dashboard with auth, charts, and recurring config; plus smart features — NL queries, auto summaries, recurring-expense detection, and net worth tracking. End of this phase: the project is feature-complete.

**Depends on:** Phase 1 and Phase 2 complete. All DB tables, cron jobs, and API stubs in place.

---

## Scope

- Next.js dashboard: Overview, Spending, Net Worth, Recurring, Transactions pages
- Telegram Login Widget authentication + session cookie
- All dashboard API routes (analytics aggregates, expense CRUD)
- Natural-language query handling in bot
- Weekly and monthly auto-summaries via cron
- Recurring-expense detection (suggestion engine)
- Savings rate and net worth calculations
- Recharts visualizations

---

## Milestones

### M3.1 — Dashboard authentication
- Telegram Login Widget integrated into the login page (`/dashboard/login`)
- Widget callback URL: `/api/auth/telegram/callback`
- Verify widget data signature with `HMAC-SHA256(BOT_TOKEN_SHA256, data_check_string)` — never trust without verifying
- On success: create signed session cookie (httpOnly, sameSite=strict, 24h TTL) using `SESSION_SECRET`
- Middleware in `apps/web/middleware.ts` redirects unauthenticated requests from `/dashboard/*` to `/dashboard/login`
- `/dashboard/login` shows the Telegram Login Widget button
- Log out: clear session cookie, redirect to login

**Done when:** Open `/dashboard` in a fresh browser → redirected to login → click widget → authenticated → session persists on page refresh → logout clears session.

### M3.2 — Dashboard layout & navigation
- Persistent sidebar: Overview, Spending, Net Worth, Recurring, Transactions
- Mobile-responsive (hamburger menu for small screens)
- Loading skeletons for all data-dependent sections
- Error boundary per section (one failing chart doesn't crash the page)

**Done when:** All nav links render the correct page; layout is usable on a 375px viewport.

### M3.3 — Analytics API routes
- `GET /api/dashboard/analytics?from=&to=` — returns:
  ```json
  {
    "totalSpend": 42500,
    "byCategory": [{"name": "Food", "amount": 12000, "budget": 15000}],
    "spendOverTime": [{"date": "2026-06-01", "amount": 1400}],
    "topMerchants": [{"merchant": "Swiggy", "amount": 4200, "count": 8}],
    "savingsRate": 0.32,
    "balanceTrend": [{"date": "2026-05-15", "balance": 85000}]
  }
  ```
- `GET /api/dashboard/expenses?page=&limit=&category=&from=&to=&q=` — paginated list with filters
- `PATCH /api/dashboard/expenses/:id` — edit amount, category, note, date
- All routes require session auth middleware; all DB queries scoped to `user_id` from session

**Done when:** All routes return correct data for a seeded test dataset; pagination works; unauthorized requests return 401.

### M3.4 — Overview page
- Cards: current balance (latest snapshot), this-month spend, savings rate, reconciliation status
- Reconciliation status banner: ✅ balanced / ⚠️ gap ₹X / 🔴 large gap
- Recent 5 transactions list with category emoji, amount, date
- "Last updated" timestamp on balance card

**Done when:** All cards show correct values; reconciliation banner reflects the latest `reconciliations` row.

### M3.5 — Spending page
- Pie chart: category breakdown for selected period (default: current month)
- Line chart: daily spend over time for selected period
- Budget bars: per-category MTD spend vs budget (only categories with a budget set)
- Period selector: this month / last month / last 3 months / custom range

**Done when:** Charts render with real data; period selector updates all charts simultaneously.

### M3.6 — Net Worth page
- Area chart: balance over time from `balance_snapshots`
- Period-over-period savings: `(prev_balance - curr_balance + income_in_period)` — or simpler: balance delta
- Savings rate card: `(income - expenses) / income` when income is tracked as a recurring credit; shows `N/A` if no income configured

**Done when:** Chart renders with all balance snapshots; savings rate is correct for a hand-calculated test scenario.

### M3.7 — Recurring page
- Table: all recurring items with name, amount, category, day, direction, active toggle
- Inline active toggle (PATCH on click, no page reload)
- Add/edit form: name, amount, category dropdown, day (1-28), direction (debit/credit), start date, end date (optional)
- Delete with confirmation dialog
- Uses `/api/dashboard/recurring` CRUD from Phase 2

**Done when:** Add a new recurring item, toggle it off, edit the amount, delete it — all reflected in DB without page reload.

### M3.8 — Transactions page
- Paginated list: 25 per page; columns: date, amount, category (with emoji), merchant, note, source badge
- Search by merchant or note (debounced, 300ms)
- Filter by category, date range
- Inline edit: click amount or category to edit in place; save on blur/enter
- Source badge: `recurring` items shown with a 🔄 indicator; non-editable amount

**Done when:** Search narrows results correctly; inline edit persists to DB; recurring items are visually distinct.

### M3.9 — Natural-language query handling
- `@nudge/ai` exports `mapNLQuery(text): Promise<{function: string, params: QueryParams}>`
- Supported functions: `sumByCategory`, `topMerchants`, `totalSpend`, `countExpenses` — each with `{range, category?, limit?}` params
- `apps/web` / `packages/bot` maps the function + params to a predefined DB query; LLM never sees query results or raw SQL
- Bot handler: detect query intent (message ends with `?` or starts with `/ask`); run the pipeline; reply with a formatted answer
- Unknown intent falls back to: *"I didn't understand that query. Try 'how much on food this month?' or '/ask top merchants last week'."*

**Done when:** 10 representative queries tested manually; no raw SQL ever generated by the LLM; unrecognized queries get the fallback reply.

### M3.10 — Auto summaries
- `POST /api/cron/weekly-summary` — generates weekly digest from templates (no LLM):
  - Total spend this week
  - Top 3 categories
  - Budget status (any over 80%)
  - Reconciliation status
  - Optionally: one LLM call for a one-line insight (optional, can disable via env var)
- `POST /api/cron/monthly-summary` — same structure for the full month + savings rate + YTD
- Both endpoints complete the GitHub Actions stubs from Phase 2

**Done when:** Manual dispatch of both endpoints sends correctly formatted Telegram messages with real data.

### M3.11 — Recurring-expense detection
- Part of `POST /api/cron/monthly-summary` (runs on 1st of month)
- Scan `expenses` for patterns: same merchant + similar amount (±10%), appearing in ≥2 of the last 3 months, not already in `recurring_items`
- For each match, bot sends: *"Looks like 'Netflix ₹649' recurs monthly — add as recurring? [Yes] [No]"*
- `[Yes]` → open dashboard link to add it; `[No]` → store suppression so it's not suggested again

**Done when:** Seed test expenses with a repeating pattern; detection fires and suggests correctly; `[No]` suppresses the suggestion in the next cycle.

---

## Testing Criteria

### Unit Tests (Vitest)

| Test | What it verifies |
|---|---|
| Telegram widget signature verification | Valid data passes; tampered data fails |
| `mapNLQuery("how much on food this month?")` | Returns `{function: "sumByCategory", params: {range: "month", category: "Food"}}` |
| `mapNLQuery("what did I spend most on last week?")` | Returns `{function: "topMerchants", params: {range: "week"}}` |
| Summary template generation | Correct totals and formatting for known inputs |
| Recurring detection algorithm | Identifies a 3-month repeating pattern; does not flag a one-off |
| Savings rate calculation | `(income - expenses) / income` — handles zero income gracefully (`N/A`) |
| Analytics aggregation | `byCategory` sums match sum of individual expenses in the same period |

### Integration Tests

| Test | What it verifies |
|---|---|
| `GET /api/dashboard/analytics` (authenticated) | Returns correct shape and values |
| `GET /api/dashboard/analytics` (unauthenticated) | Returns 401 |
| `PATCH /api/dashboard/expenses/:id` | Updates correct row; other rows unchanged |
| `PATCH /api/dashboard/expenses/:id` (wrong user_id) | Returns 403 |
| Widget callback with valid signature | Session cookie set; redirect to `/dashboard` |
| Widget callback with invalid signature | Returns 401; no cookie set |
| `POST /api/cron/weekly-summary` | Telegram message sent; returns 200 |

### Manual / E2E Checklist

- [ ] Log in via Telegram Login Widget → see dashboard
- [ ] Refresh page → still logged in (cookie persists)
- [ ] Log out → redirected to login; `/dashboard` redirects to login
- [ ] Overview page shows correct current balance and this-month spend
- [ ] Spending pie chart shows correct category breakdown for current month
- [ ] Change period to "last month" → charts update
- [ ] Add a recurring item → appears in table → toggle off → toggle on
- [ ] Search transactions by merchant → results filtered correctly
- [ ] Inline edit a transaction's category → saved without page reload
- [ ] Send "how much on food this month?" to bot → correct answer
- [ ] Send "what did I spend most on last week?" → correct answer
- [ ] Manual dispatch weekly-summary cron → Telegram message received
- [ ] Manual dispatch monthly-summary cron → Telegram message + recurring detection suggestions

---

## Definition of Done

- All unit and integration tests pass
- Manual E2E checklist complete
- All Recharts visualizations render correctly with real data and empty states
- NL query handling tested with 10+ representative questions
- Auto summaries verified with real monthly data
- Telegram Login Widget auth works in production (requires domain set via BotFather)
- No TypeScript errors across the monorepo (`pnpm build` clean)

---

## Concerns & Risks

1. **Telegram Login Widget domain requirement** — The widget only works if the bot's domain is set via `@BotFather → Bot Settings → Domain`. This must be set to the Render app's public URL before testing. There is no localhost workaround; use ngrok or similar for local dev of the auth flow.

2. **Session cookie on Render** — Render may run multiple instances on paid tiers, but on the free tier it's one instance. If you ever scale, the signed session cookie (stateless JWT-style) is portable — avoid server-side session storage. Use `jose` or `iron-session` for cookie signing.

3. **Recharts SSR** — Recharts requires a browser environment (uses `window`). Use Next.js `dynamic(() => import(...), { ssr: false })` for all chart components, or wrap them in a client component with `'use client'`. Missing this causes a hydration error on first render.

4. **NL query LLM hallucinations** — The LLM may return a function name that doesn't exist in your predefined set. Always validate the returned `function` against the allowlist before executing. Return the fallback message if validation fails.

5. **Recurring detection false positives** — The ±10% similarity threshold may flag variable-amount expenses (e.g., electricity bills) as recurring. Consider requiring exact amount match for the MVP, or adding a "fuzzy" flag to the suggestion so the user knows it's approximate.

6. **Inline edit UX on mobile** — Inline editing (click to edit) is less usable on touch screens. Consider a tap-to-open modal for mobile instead. Test on a real phone before marking M3.8 done.
