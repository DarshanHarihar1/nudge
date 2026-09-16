# Email Expense Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the SMS-forwarding trigger with an email-based one — when Union Bank of India sends a `DEBIT TRANSACTION ALERT` email, automatically parse it, classify it, log it, and confirm it over Telegram, the same way the existing Telegram-text flow works today.

**Architecture:** A Composio Gmail poll-trigger (`GMAIL_NEW_GMAIL_MESSAGE`, filtered to `from:noreplyubi-txn@ubi.bank.in`) delivers new-message payloads to a new `POST /email/webhook` endpoint on the existing `nudge-api` FastAPI service (Render, already deployed). The endpoint hands off to a new service module that deterministically regex-parses the bank's fixed "Transaction Details" block (no LLM needed for extraction — the template is 100% consistent across live samples), reuses the existing `classify_expense()` LLM call purely for categorization, inserts into the existing `expenses` table with `source='email'`, and reuses the existing Telegram confirm/recategorize UI to notify the user. No new services, no new database, no second repo.

**Tech Stack:** Python/FastAPI (`apps/api`), asyncpg/Supabase Postgres, python-telegram-bot, Composio (Gmail trigger, already connected), Render (existing `nudge-api` service, srv-d90d715ckfvc73dcvs60).

**Spec:** This plan's spec is the architecture review conducted earlier in this conversation (no separate spec doc — the "Spec" context below inlines what was decided).

## Global Constraints

- Single user, low volume — do not add infrastructure (no GCP Pub/Sub, no new services, no message queue). Matches `design/spec.md`'s stated principle.
- LLM only where language is ambiguous — the bank email body is deterministically parseable, so only category classification (already existing `ai/classify.classify_expense()`) touches an LLM. Amount/merchant/status come from regex, not the LLM.
- One service, one repo — new code lives in `apps/api`, following existing `routers/` + `services/` + `db/queries.py` + `utils/` layout. No new packages, no monorepo split.
- Reuse existing patterns exactly: `utils/balance_parser.py` (deterministic regex parsing), `bot/handlers/expense.py`'s confirm/recategorize Telegram UI, `routers/shortcut.py` (sibling router style), `config.py`'s `_require()` pattern for secrets.
- `expenses.source` is free-text with no CHECK constraint (confirmed live on Supabase project `eujgadmyeqndbtvygumg`) — `'email'` is a safe value, no schema fight needed there.

---

### Task 1: Add an idempotency column for email transactions

**Why:** The existing `telegram_update_id` unique column stops Telegram webhook retries from double-inserting. The email path needs the same guarantee against Composio's poll-trigger redelivering the same message. The bank's own `Transaction ID/RRN` is a clean natural key for this.

**Files:**
- None (Supabase schema change via MCP, no local migration files exist in this repo — schema lives directly in Supabase)

**Interfaces:**
- Produces: `expenses.email_ref` — nullable `text`, `UNIQUE` (Postgres allows multiple `NULL`s under `UNIQUE`, so Telegram/shortcut rows are unaffected).

- [ ] **Step 1: Apply the column via Supabase MCP**

Run (via `mcp__plugin_supabase_supabase__apply_migration`, project_id `eujgadmyeqndbtvygumg`):

```sql
ALTER TABLE expenses ADD COLUMN email_ref text UNIQUE;
```

- [ ] **Step 2: Verify**

Run (via `mcp__plugin_supabase_supabase__execute_sql`, project_id `eujgadmyeqndbtvygumg`):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'expenses' AND column_name = 'email_ref';
```

Expected: one row, `data_type = 'text'`, `is_nullable = 'YES'`.

- [ ] **Step 3: Commit**

No local file changed — nothing to commit. Note the migration in the PR description for Task 3 (which is the first task that reads/writes this column from Python).

---

### Task 2: Deterministic UBI debit-email parser

**Files:**
- Create: `apps/api/utils/email_parser.py`
- Test: `apps/api/tests/test_email_parser.py`

**Interfaces:**
- Produces: `ParsedDebitEmail` dataclass (`payee: str`, `amount: float`, `currency: str`, `channel: str`, `rrn: str`, `status: str`, `occurred_at: str`) and `parse_ubi_debit_email(html_text: str) -> Optional[ParsedDebitEmail]`, consumed by Task 5's `services/email_ingest.py`.

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_email_parser.py
from utils.email_parser import parse_ubi_debit_email

SUCCESS_EMAIL = """
<div>
Dear <strong>DARSHAN HARIHAR</strong>,<br><br>
Your fund transfer request through <strong>UPI</strong> has been processed successfully.<br><br>
<div>
  <div>Transaction Details</div>
  1. Payee Name :   ZOMATO<br>
  2. Amount : Rs. 97.84<br>
  3. Channel : UPI<br>
  4. Transaction ID/RRN : 561297249109<br>
  5. Transaction Status : Success<br>
  6. Transaction Date and Time : 16-09-2026 22:11:19<br>
  7. Debit Account Number : *4200
</div>
<br>
<div>
  If you have not initiated this transaction, please report it immediately
</div>
</div>
"""

FAILED_EMAIL = SUCCESS_EMAIL.replace("Success", "Failed")

COMMA_AMOUNT_EMAIL = SUCCESS_EMAIL.replace("Rs. 97.84", "Rs. 1,234.50")

NON_TRANSACTION_EMAIL = """
<div>Your monthly e-statement is now available. Log in to download it.</div>
"""


def test_parses_success_email():
    result = parse_ubi_debit_email(SUCCESS_EMAIL)
    assert result is not None
    assert result.payee == "ZOMATO"
    assert result.amount == 97.84
    assert result.currency == "INR"
    assert result.channel == "UPI"
    assert result.rrn == "561297249109"
    assert result.status == "Success"
    assert result.occurred_at == "16-09-2026 22:11:19"


def test_parses_failed_status():
    result = parse_ubi_debit_email(FAILED_EMAIL)
    assert result is not None
    assert result.status == "Failed"


def test_parses_comma_separated_amount():
    result = parse_ubi_debit_email(COMMA_AMOUNT_EMAIL)
    assert result is not None
    assert result.amount == 1234.50


def test_returns_none_for_non_transaction_email():
    assert parse_ubi_debit_email(NON_TRANSACTION_EMAIL) is None


def test_returns_none_for_empty_string():
    assert parse_ubi_debit_email("") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_email_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'utils.email_parser'`

- [ ] **Step 3: Write the implementation**

```python
# apps/api/utils/email_parser.py
"""
Deterministic parser for Union Bank of India's "DEBIT TRANSACTION ALERT"
emails (sender: noreplyubi-txn@ubi.bank.in). The bank's template embeds a
fixed numbered "Transaction Details" block — confirmed identical across
live samples, so this is regex, not an LLM call.
"""
import re
from dataclasses import dataclass
from typing import Optional

_BLOCK_RE = re.compile(
    r"Transaction Details.*?(?=If you have not initiated|Alert Section|$)",
    re.S,
)
_FIELD_RE = re.compile(r"\d+\.\s*([^:<]+?)\s*:\s*([^<\n]+)")
_AMOUNT_RE = re.compile(r"([\d,]+\.?\d*)")


@dataclass
class ParsedDebitEmail:
    payee: str
    amount: float
    currency: str
    channel: str
    rrn: str
    status: str
    occurred_at: str


def parse_ubi_debit_email(html_text: str) -> Optional[ParsedDebitEmail]:
    """
    Extract payee/amount/status/etc. from the numbered "Transaction Details"
    block. Returns None if the block is missing or a required field is
    absent — e.g. a non-transactional email from the same sender
    (statement notice, promo) that doesn't match the debit-alert template.
    """
    block_match = _BLOCK_RE.search(html_text)
    if not block_match:
        return None

    fields = {
        key.strip().lower(): value.strip()
        for key, value in _FIELD_RE.findall(block_match.group(0))
    }

    payee = fields.get("payee name")
    amount_raw = fields.get("amount")
    rrn = fields.get("transaction id/rrn")
    status = fields.get("transaction status")

    if not all([payee, amount_raw, rrn, status]):
        return None

    amount_match = _AMOUNT_RE.search(amount_raw)
    if not amount_match:
        return None

    return ParsedDebitEmail(
        payee=payee,
        amount=float(amount_match.group(1).replace(",", "")),
        currency="INR",
        channel=fields.get("channel", ""),
        rrn=rrn,
        status=status,
        occurred_at=fields.get("transaction date and time", ""),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_email_parser.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/utils/email_parser.py apps/api/tests/test_email_parser.py
git commit -m "feat: add deterministic parser for UBI debit-alert emails"
```

---

### Task 3: DB support for the email idempotency key

**Files:**
- Modify: `apps/api/db/queries.py:147-171` (`create_expense`)
- Test: none (this file has no existing DB-touching unit tests — the repo's own convention, per its README, is "pure-logic unit tests" only; DB-touching functions are verified manually, same as every other function in this file)

**Interfaces:**
- Consumes: nothing new
- Produces: `create_expense(pool, ..., email_ref: str | None = None)` now accepts and persists `email_ref`; new `get_expense_by_email_ref(pool, email_ref: str) -> Optional[dict]`, consumed by Task 5.

- [ ] **Step 1: Extend `create_expense`**

In `apps/api/db/queries.py`, replace lines 147-171:

```python
async def create_expense(pool: asyncpg.Pool, **data) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO expenses (
            user_id, amount, currency, category_id, merchant, note,
            raw_text, source, status, confidence, llm_provider,
            telegram_update_id, email_ref
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING *
        """,
        data["user_id"],
        str(data["amount"]),
        data.get("currency", "INR"),
        data["category_id"],
        data.get("merchant"),
        data.get("note"),
        data["raw_text"],
        data.get("source", "telegram"),
        data.get("status", "pending"),
        str(data["confidence"]) if data.get("confidence") is not None else None,
        data.get("llm_provider"),
        data.get("telegram_update_id"),
        data.get("email_ref"),
    )
    return dict(row)


async def get_expense_by_email_ref(
    pool: asyncpg.Pool, email_ref: str
) -> Optional[dict]:
    row = await pool.fetchrow(
        "SELECT * FROM expenses WHERE email_ref = $1", email_ref
    )
    return dict(row) if row else None


async def confirm_expense(pool: asyncpg.Pool, expense_id: str) -> None:
    await pool.execute(
        "UPDATE expenses SET status = 'confirmed' WHERE id = $1", expense_id
    )
```

- [ ] **Step 2: Run the full pytest suite to confirm no regression**

Run: `cd apps/api && python -m pytest tests/ -v`
Expected: all previously-passing tests still pass (this change is additive — existing callers of `create_expense` don't pass `email_ref`, so `data.get("email_ref")` is `None` for them, same as before).

- [ ] **Step 3: Commit**

```bash
git add apps/api/db/queries.py
git commit -m "feat: add email_ref support to create_expense for email idempotency"
```

---

### Task 4: Extract reusable Telegram confirm/recategorize keyboards

**Why:** `bot/handlers/expense.py` already has the exact OK/Recategorize/Delete UI and category-picker keyboard the email flow needs. They're currently private (`_`-prefixed) and the recategorize keyboard is built inline inside `callback_handler`. Pull both into importable, non-underscored functions so Task 5's email service can call them without duplicating Telegram UI code.

**Files:**
- Modify: `apps/api/bot/handlers/expense.py`

**Interfaces:**
- Produces: `confirm_keyboard(expense_id: str) -> InlineKeyboardMarkup` (sync, renamed from `_confirm_keyboard`), `recategorize_keyboard(pool, user_id: str, expense_id: str) -> InlineKeyboardMarkup` (new async function, extracted from `callback_handler`'s `CB_RECAT` branch), `post_keyboard(expense_id: str) -> InlineKeyboardMarkup` (new sync function — Recategorize/Delete only, no OK, for expenses that are inserted already-confirmed). Consumed by Task 5.

- [ ] **Step 1: Rename `_confirm_keyboard` → `confirm_keyboard`**

In `apps/api/bot/handlers/expense.py`, replace:

```python
def _confirm_keyboard(expense_id: str) -> InlineKeyboardMarkup:
```

with:

```python
def confirm_keyboard(expense_id: str) -> InlineKeyboardMarkup:
```

Update its one call site inside `expense_handler`:

```python
        reply_markup=_confirm_keyboard(str(expense["id"])),
```

becomes:

```python
        reply_markup=confirm_keyboard(str(expense["id"])),
```

- [ ] **Step 2: Extract `recategorize_keyboard` from `callback_handler`**

Replace the `CB_RECAT` branch of `callback_handler`:

```python
    elif data.startswith(CB_RECAT):
        expense_id = data[len(CB_RECAT):]
        user = await get_user(pool, update.effective_user.id)
        if not user:
            return

        cats = await list_categories(pool, str(user["id"]))
        rows: list[list[InlineKeyboardButton]] = []
        current_row: list[InlineKeyboardButton] = []
        for i, c in enumerate(cats):
            current_row.append(
                InlineKeyboardButton(
                    f"{c['emoji']} {c['name']}",
                    callback_data=f"{CB_CAT}{expense_id}:{c['id']}",
                )
            )
            if len(current_row) == 3:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)

        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
```

with:

```python
    elif data.startswith(CB_RECAT):
        expense_id = data[len(CB_RECAT):]
        user = await get_user(pool, update.effective_user.id)
        if not user:
            return

        keyboard = await recategorize_keyboard(pool, str(user["id"]), expense_id)
        await query.edit_message_reply_markup(reply_markup=keyboard)
```

Add the new function above `expense_handler` (after `_confirm_keyboard`/`confirm_keyboard`):

```python
async def recategorize_keyboard(
    pool, user_id: str, expense_id: str
) -> InlineKeyboardMarkup:
    cats = await list_categories(pool, user_id)
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for c in cats:
        current_row.append(
            InlineKeyboardButton(
                f"{c['emoji']} {c['name']}",
                callback_data=f"{CB_CAT}{expense_id}:{c['id']}",
            )
        )
        if len(current_row) == 3:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(rows)
```

- [ ] **Step 3: Add `post_keyboard` — Recategorize/Delete only, no OK**

For an expense that's inserted *already confirmed* (Task 5's high-confidence email path), there's nothing for an "OK" tap to do — it's already counted. Add this next to `confirm_keyboard`:

```python
def post_keyboard(expense_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✏️ Recategorize", callback_data=f"{CB_RECAT}{expense_id}"
                ),
                InlineKeyboardButton("🗑 Delete", callback_data=f"{CB_DEL}{expense_id}"),
            ]
        ]
    )
```

- [ ] **Step 4: Verify no regression**

Run: `cd apps/api && python -m pytest tests/ -v` (expected: all pass — this module has no direct unit tests, so this only catches import errors)

Then manually smoke-test over Telegram: send yourself a plain-text expense message, confirm the "Logged X → Category" message with OK/Recategorize/Delete buttons still appears, and confirm tapping "Recategorize" still shows the category-picker grid.

- [ ] **Step 5: Commit**

```bash
git add apps/api/bot/handlers/expense.py
git commit -m "refactor: extract reusable confirm/recategorize keyboards"
```

---

### Task 5: Email ingestion service (parse → classify → store → notify)

**Files:**
- Create: `apps/api/services/email_ingest.py`
- Test: `apps/api/tests/test_email_ingest.py`

**Behavior:** A confident classification is inserted **already `confirmed`** (counts toward spending totals/budgets immediately, same as the existing Shortcuts quick-add path) and the Telegram message carries only Recategorize/Delete — no OK tap needed. A low-confidence classification stays `pending` and goes straight to the category picker; picking a category there already confirms it (existing `recategorize_expense` behavior, unchanged). This matters beyond UI: only `status = 'confirmed'` expenses are counted in `db/queries.py`'s spend/budget/summary queries (verified: `grep -n "status = 'confirmed'" db/queries.py` — used across `get_category_mtd_spend`, weekly/monthly summary totals, etc.), so skipping the confirm step without setting `status='confirmed'` up front would silently leave auto-logged expenses uncounted.

**Interfaces:**
- Consumes: `parse_ubi_debit_email` (Task 2), `create_expense`/`get_expense_by_email_ref`/`get_user`/`get_category_by_name` (Task 3 + existing `db/queries.py`), `recategorize_keyboard`/`post_keyboard` (Task 4), `classify_expense` (existing `ai/classify.py`), `format_amount` (existing `bot/utils/format.py`).
- Produces: `needs_recategorize(confidence: float) -> bool` and `async def process_debit_email(pool, bot, allowed_telegram_id: int, message_text: str, subject: str) -> dict`, consumed by Task 6's router.

- [ ] **Step 1: Write the failing test for the pure confidence-gate function**

```python
# apps/api/tests/test_email_ingest.py
import pytest

from services.email_ingest import needs_recategorize


@pytest.mark.parametrize("confidence,expected", [
    (0.0, True),
    (0.59, True),
    (0.6, False),
    (0.61, False),
    (1.0, False),
])
def test_needs_recategorize(confidence, expected):
    assert needs_recategorize(confidence) is expected
```

(This is the only piece of `email_ingest.py` that's pure logic testable without a live DB/Telegram bot — the rest is orchestration glue, same boundary the rest of this repo draws: `services/recurring.py`, `services/detection.py`, etc. have no direct unit tests either, only the pure `utils/` functions they call do.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && python -m pytest tests/test_email_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.email_ingest'`

- [ ] **Step 3: Write the implementation**

```python
# apps/api/services/email_ingest.py
"""
Orchestrates the email debit-alert flow: parse -> filter -> dedupe ->
classify -> store -> notify. Mirrors bot/handlers/expense.py's Telegram
text flow, reusing its classification call and confirm/recategorize UI.
"""
from telegram import Bot

from ai.classify import classify_expense
from bot.handlers.expense import post_keyboard, recategorize_keyboard
from bot.utils.format import format_amount
from db.queries import (
    create_expense,
    get_category_by_name,
    get_expense_by_email_ref,
    get_user,
)
from utils.email_parser import parse_ubi_debit_email

# Below this classification confidence, don't guess — ask via the
# recategorize picker immediately instead of showing OK/Recategorize/Delete.
LOW_CONFIDENCE_THRESHOLD = 0.6


def needs_recategorize(confidence: float) -> bool:
    return confidence < LOW_CONFIDENCE_THRESHOLD


async def process_debit_email(
    pool,
    bot: Bot,
    allowed_telegram_id: int,
    message_text: str,
    subject: str,
) -> dict:
    parsed = parse_ubi_debit_email(message_text)
    if not parsed:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f'📧 Got a mail from the bank I couldn\'t parse: "{subject}". Log it manually if it was a transaction.',
        )
        return {"ok": False, "reason": "unparseable"}

    if parsed.status.lower() != "success":
        return {"ok": False, "reason": f"status={parsed.status}"}

    if await get_expense_by_email_ref(pool, parsed.rrn):
        return {"ok": False, "reason": "duplicate"}

    user = await get_user(pool, allowed_telegram_id)
    if not user:
        return {"ok": False, "reason": "user_not_registered"}

    classified = await classify_expense(f"{parsed.amount} at {parsed.payee}")
    category = await get_category_by_name(pool, str(user["id"]), classified.category)
    if not category:
        return {"ok": False, "reason": "category_not_found"}

    low_confidence = needs_recategorize(classified.confidence)

    # Confident guesses are inserted already-confirmed (no tap required to
    # count toward totals/budgets); unsure ones stay pending until a
    # category is picked, same as recategorize_expense() already does.
    expense = await create_expense(
        pool,
        user_id=str(user["id"]),
        amount=parsed.amount,
        currency=parsed.currency,
        category_id=str(category["id"]),
        merchant=parsed.payee,
        raw_text=message_text,
        source="email",
        status="pending" if low_confidence else "confirmed",
        confidence=classified.confidence,
        llm_provider=classified.provider,
        email_ref=parsed.rrn,
    )

    label = (
        f"{format_amount(parsed.amount, parsed.currency)} → "
        f"{category['emoji']} {category['name']} ({parsed.payee})"
    )

    if low_confidence:
        keyboard = await recategorize_keyboard(pool, str(user["id"]), str(expense["id"]))
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 {label} — not sure about the category, pick one:",
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(
            chat_id=allowed_telegram_id,
            text=f"🏦 Logged {label}",
            reply_markup=post_keyboard(str(expense["id"])),
        )

    return {"ok": True, "id": str(expense["id"])}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && python -m pytest tests/test_email_ingest.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/services/email_ingest.py apps/api/tests/test_email_ingest.py
git commit -m "feat: add email debit-alert ingestion service"
```

---

### Task 6: Webhook endpoint + wiring + docs

**Files:**
- Create: `apps/api/routers/email.py`
- Modify: `apps/api/main.py`
- Modify: `apps/api/README.md`

**Interfaces:**
- Consumes: `process_debit_email` (Task 5), `EMAIL_WEBHOOK_SECRET`/`TELEGRAM_ALLOWED_ID` (Task 7's `config.py`).
- Produces: `POST /email/webhook` endpoint.

- [ ] **Step 1: Write the router**

```python
# apps/api/routers/email.py
"""
Webhook endpoint — Composio's Gmail poll-trigger (GMAIL_NEW_GMAIL_MESSAGE,
filtered to from:noreplyubi-txn@ubi.bank.in) POSTs new-message events here.

Auth: shared secret header (X-Webhook-Secret), same pattern as Telegram's
own webhook secret header in main.py.
"""
from fastapi import APIRouter, Header, HTTPException, Request

from config import EMAIL_WEBHOOK_SECRET, TELEGRAM_ALLOWED_ID
from services.email_ingest import process_debit_email

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/webhook")
async def email_webhook(
    request: Request,
    x_webhook_secret: str = Header(default=""),
):
    if not EMAIL_WEBHOOK_SECRET or x_webhook_secret != EMAIL_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    message_text = body.get("message_text", "")
    subject = body.get("subject", "")

    pool = request.app.state.pool
    bot = request.app.state.telegram_app.bot
    result = await process_debit_email(
        pool, bot, TELEGRAM_ALLOWED_ID, message_text, subject
    )
    return {"ok": True, **result}
```

`message_text`/`subject` field names match the `NewMessagePayload` schema Composio's `GMAIL_NEW_GMAIL_MESSAGE` trigger documents (`message_text`, `subject`, `sender`, `id`, `message_id`, `thread_id`, `to`, `label_ids`, `message_timestamp`, `payload`, `preview`, `attachment_list`). This is the trigger's own declared payload shape, not yet verified against a live delivery — Step 4 below confirms it.

- [ ] **Step 2: Wire into `main.py`**

In `apps/api/main.py`, add the import alongside the other routers:

```python
from routers.email import router as email_router
```

and the include alongside the others:

```python
app.include_router(email_router)
```

- [ ] **Step 3: Update the API docs table**

In `apps/api/README.md`, add a row to the HTTP API table (after the `/webhook` row):

```markdown
| POST | `/email/webhook` | `X-Webhook-Secret` header | Composio Gmail trigger → bank debit-alert ingestion |
```

- [ ] **Step 4: Verify against a live payload before relying on field names**

This step exists because Composio's actual webhook delivery envelope for this trigger hasn't been observed live in this environment yet (only its declared schema has). Before Task 9's end-to-end test:

1. Deploy this change.
2. Send `curl -X POST https://nudge-api-va33.onrender.com/email/webhook -H "X-Webhook-Secret: <value>" -d '{"message_text":"test","subject":"test"}'` and confirm a `403` becomes `{"ok": true, ...}` once the header matches — confirms auth wiring.
3. Once Task 8's real trigger is registered and a real bank email arrives, check the Render logs (`mcp__plugin_render_render__list_logs`, service `srv-d90d715ckfvc73dcvs60`) for the request body Composio actually sent. If `message_text`/`subject` aren't top-level fields (e.g. nested under `data` or `payload`), adjust the two `body.get(...)` lines in Step 1 accordingly — everything downstream (`process_debit_email`) is unaffected.

- [ ] **Step 5: Commit**

```bash
git add apps/api/routers/email.py apps/api/main.py apps/api/README.md
git commit -m "feat: add /email/webhook endpoint for bank debit-alert ingestion"
```

---

### Task 7: Secrets — `EMAIL_WEBHOOK_SECRET`

**Files:**
- Modify: `apps/api/config.py`
- Modify: `apps/api/.env.example`

**Interfaces:**
- Produces: `config.EMAIL_WEBHOOK_SECRET: str`, consumed by Task 6's router.

- [ ] **Step 1: Add the required env var to `config.py`**

In `apps/api/config.py`, add after the `CRON_SECRET` line:

```python
EMAIL_WEBHOOK_SECRET: str = _require("EMAIL_WEBHOOK_SECRET")
```

- [ ] **Step 2: Document it in `.env.example`**

In `apps/api/.env.example`, add after the `Cron` section:

```
# Email ingestion (Composio Gmail trigger webhook)
EMAIL_WEBHOOK_SECRET=
```

- [ ] **Step 3: Generate a secret value and set it on Render**

Generate one locally: `openssl rand -hex 32`

⚠️ **This changes production config on a live Render service — confirm with the user before applying.** Once confirmed, set it via:

`mcp__plugin_render_render__update_environment_variables` for service `srv-d90d715ckfvc73dcvs60`, adding `EMAIL_WEBHOOK_SECRET=<generated value>` (merge with existing vars — do not replace the full env var set).

Note: adding a `_require()`'d var means the API **will fail to boot** on the next deploy until this is set — sequence the Render env var update and the Task 6 deploy together, not the Task 6 deploy first.

- [ ] **Step 4: Commit**

```bash
git add apps/api/config.py apps/api/.env.example
git commit -m "feat: add EMAIL_WEBHOOK_SECRET config for email ingestion"
```

---

### Task 8: Register the Composio Gmail trigger

**Why:** This is external configuration, not code in this repo — it tells Composio to start polling Gmail and where to deliver matches.

**What to configure** (trigger `GMAIL_NEW_GMAIL_MESSAGE`, toolkit `gmail`, already-connected account):

```json
{
  "query": "from:noreplyubi-txn@ubi.bank.in",
  "labelIds": "INBOX",
  "interval": 60,
  "userId": "me"
}
```

(`interval` is minutes between polls — set to 60 per your preference. Composio's enforced floor for a Composio-managed connection is 15 minutes (since April 15, 2026 a lower value returns an API error outright — source: [Composio changelog](https://docs.composio.dev/reference/changelog)), so anything 15 or above is valid; 60 is comfortably above that floor, not up against it. Confident guesses don't need a tap anyway (Task 5's `post_keyboard` change), so an hourly check just means you'll see the Telegram log a bit later, with no functional downside — still far less overhead than the 3x/day cron alternative this plan rejected, and it's a config value on Composio's side, tunable later with no code change.)

- [ ] **Step 1: Confirm how this environment can subscribe a delivery target**

The `composio` CLI available in this environment only exposes `composio triggers list`/`info` (browsing trigger *types*) — not creating a trigger *instance* with a delivery target. That has to happen through either:
- **Composio's dashboard** (Triggers → create instance for `GMAIL_NEW_GMAIL_MESSAGE`, paste the config above, set the target webhook URL to `https://nudge-api-va33.onrender.com/email/webhook` with header `X-Webhook-Secret: <value from Task 7>`), or
- **Composio's Python/TS SDK**, if the dashboard doesn't expose a "webhook URL" field for this trigger type — in which case a small always-on `composio listen` forwarder would be needed instead, which reopens the "extra long-running process" question this plan deliberately avoided. Prefer the dashboard webhook-URL path if it exists.

Check which is available before proceeding — this determines whether Task 8 is a five-minute dashboard click-through or needs its own follow-up plan.

- [ ] **Step 2: Register the trigger**

Using whichever path Step 1 confirmed, create the trigger instance with the config above pointed at the Task 6 endpoint.

- [ ] **Step 3: Verify**

Send yourself (or wait for) a real UPI debit — Composio should poll it up within the configured interval and hit the webhook. Confirm via Render logs that a request landed at `/email/webhook`.

- [ ] **Step 4: Commit**

Nothing to commit (external config) — note the trigger instance ID/dashboard link somewhere you'll remember it, in case it needs to be disabled or re-pointed later.

---

### Task 9: End-to-end smoke test

**Files:** none — verification only.

- [ ] **Step 1: Trigger a real transaction**

Make a small real UPI payment (or wait for the next one) from the account UBI sends alerts for.

- [ ] **Step 2: Confirm the full pipeline**

Within the configured poll interval, confirm:
1. Render logs show a `POST /email/webhook` hit.
2. A new row appears in `expenses` with `source = 'email'`, correct `amount`/`merchant`/`email_ref` (via `mcp__plugin_supabase_supabase__execute_sql`: `SELECT * FROM expenses WHERE source = 'email' ORDER BY created_at DESC LIMIT 1;`).
3. A Telegram message arrives — either "Logged ₹X → Category (Payee)" with Recategorize/Delete only (already counted, no tap needed), or (if confidence was low) the direct category picker.
4. Tapping Recategorize/a category still behaves exactly like the Telegram-text flow.

- [ ] **Step 3: Confirm idempotency**

Manually re-POST the same webhook body (same `message_text`, same RRN) to `/email/webhook`. Expected: `{"ok": true, "ok": false, "reason": "duplicate"}` — no second row, no second Telegram message.

- [ ] **Step 4: Disable the old SMS-forwarding Shortcut**

This is a phone-side change, not code: open the Shortcuts app on the iPhone and turn off (or delete) the automation that listens for the bank's SMS and forwards it to Telegram — it's now redundant and would double-log if the bank ever sends both.

---

## Self-Review

**Spec coverage:**
- "Update it from email to mail... store the data" → Tasks 1-6 (parse, classify, store).
- "run the entire process for classification" → Task 5 reuses existing `classify_expense()` unchanged.
- "send a message on Telegram saying I've added this to this category" → Task 5's confident-guess branch (auto-confirmed, `post_keyboard`, no tap required).
- "if not able to classify, ask via options I can click" → Task 5's `needs_recategorize`/`recategorize_keyboard` branch (also covers genuinely unparseable emails via the fallback Telegram alert in `process_debit_email`).
- "minimize my effort — no OK, only act if wrong" → Task 4's `post_keyboard` (Recategorize/Delete only) + Task 5 inserting confident guesses as `status='confirmed'` directly, so no tap is needed for them to count.
- "check Supabase services are fine" → done live earlier in this conversation (project restored, `ACTIVE_HEALTHY`, schema confirmed) — not a plan task since it's already verified.
- "setting a watcher on Gmail... or cron thrice a day" → Composio poll-trigger chosen (Task 8) over GitHub Actions cron, per the earlier architecture discussion (lower latency, zero new infra, Gmail already connected).
- Same repo vs. new repo → same repo, reflected throughout (all new files under `apps/api/`).

**Placeholder scan:** none found — every step has runnable code or a concrete command.

**Type consistency:** `ParsedDebitEmail` (Task 2) fields match usage in `services/email_ingest.py` (Task 5) exactly (`payee`, `amount`, `currency`, `channel`, `rrn`, `status`, `occurred_at`). `post_keyboard`/`recategorize_keyboard` signatures (Task 4) match their call sites in Task 5. `create_expense`'s new `email_ref` kwarg (Task 3) matches Task 5's call. `confirm_keyboard` (Task 4) stays used by the existing Telegram-text flow in `bot/handlers/expense.py`, unchanged — the email flow uses `post_keyboard` instead since it never needs an OK tap.
