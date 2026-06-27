import asyncpg
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

DEFAULT_CATEGORIES = [
    {"name": "Food", "emoji": "🍴"},
    {"name": "Groceries", "emoji": "🛒"},
    {"name": "Transport", "emoji": "🚗"},
    {"name": "Rent", "emoji": "🏠"},
    {"name": "Utilities", "emoji": "💡"},
    {"name": "Entertainment", "emoji": "🎬"},
    {"name": "Shopping", "emoji": "🛍️"},
    {"name": "Health", "emoji": "💊"},
    {"name": "Subscriptions", "emoji": "📱"},
    {"name": "Education", "emoji": "📚"},
    {"name": "Misc", "emoji": "📦"},
]

# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user(pool: asyncpg.Pool, telegram_id: int) -> Optional[dict]:
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1", telegram_id
    )
    return dict(row) if row else None


async def upsert_user(pool: asyncpg.Pool, telegram_id: int, name: str) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO users (telegram_id, name)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING *
        """,
        telegram_id,
        name,
    )
    return dict(row)


async def set_awaiting_balance(
    pool: asyncpg.Pool, user_id: str, value: bool
) -> None:
    await pool.execute(
        "UPDATE users SET awaiting_balance = $1 WHERE id = $2", value, user_id
    )


async def set_balance_prompt_sent(pool: asyncpg.Pool, user_id: str) -> None:
    await pool.execute(
        "UPDATE users SET balance_prompt_sent_at = now(), awaiting_balance = true WHERE id = $1",
        user_id,
    )


# ── Categories ────────────────────────────────────────────────────────────────

async def seed_categories(pool: asyncpg.Pool, user_id: str) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            for cat in DEFAULT_CATEGORIES:
                await conn.execute(
                    """
                    INSERT INTO categories (user_id, name, emoji)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, name) DO NOTHING
                    """,
                    user_id,
                    cat["name"],
                    cat["emoji"],
                )


async def list_categories(pool: asyncpg.Pool, user_id: str) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT * FROM categories
        WHERE user_id = $1 AND is_active = true
        ORDER BY name
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def get_category_by_name(
    pool: asyncpg.Pool, user_id: str, name: str
) -> Optional[dict]:
    row = await pool.fetchrow(
        """
        SELECT * FROM categories
        WHERE user_id = $1 AND name = $2 AND is_active = true
        """,
        user_id,
        name,
    )
    return dict(row) if row else None


async def update_category_budget(
    pool: asyncpg.Pool, category_id: str, monthly_budget: Optional[float]
) -> Optional[dict]:
    row = await pool.fetchrow(
        "UPDATE categories SET monthly_budget = $1 WHERE id = $2 RETURNING *",
        str(monthly_budget) if monthly_budget is not None else None,
        category_id,
    )
    return dict(row) if row else None


async def get_category_mtd_spend(
    pool: asyncpg.Pool, user_id: str, category_id: str
) -> Decimal:
    """Sum of confirmed expenses for a category in the current IST calendar month."""
    val = await pool.fetchval(
        """
        SELECT COALESCE(SUM(amount::numeric), 0)
        FROM expenses
        WHERE user_id = $1
          AND category_id = $2
          AND status = 'confirmed'
          AND date_trunc('month', spent_at AT TIME ZONE 'Asia/Kolkata')
              = date_trunc('month', now() AT TIME ZONE 'Asia/Kolkata')
        """,
        user_id,
        category_id,
    )
    return val or Decimal(0)


async def update_category_budget_alert(
    pool: asyncpg.Pool, category_id: str, level: int, month_str: str
) -> None:
    """level: 80 or 100"""
    col = "budget_80_sent_month" if level == 80 else "budget_100_sent_month"
    await pool.execute(
        f"UPDATE categories SET {col} = $1 WHERE id = $2",
        month_str,
        category_id,
    )


# ── Expenses ──────────────────────────────────────────────────────────────────

async def create_expense(pool: asyncpg.Pool, **data) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO expenses (
            user_id, amount, currency, category_id, merchant, note,
            raw_text, source, status, confidence, llm_provider, telegram_update_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
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
    )
    return dict(row)


async def confirm_expense(pool: asyncpg.Pool, expense_id: str) -> None:
    await pool.execute(
        "UPDATE expenses SET status = 'confirmed' WHERE id = $1", expense_id
    )


async def recategorize_expense(
    pool: asyncpg.Pool, expense_id: str, category_id: str
) -> None:
    await pool.execute(
        "UPDATE expenses SET category_id = $1, status = 'confirmed' WHERE id = $2",
        category_id,
        expense_id,
    )


async def delete_expense(pool: asyncpg.Pool, expense_id: str) -> None:
    await pool.execute("DELETE FROM expenses WHERE id = $1", expense_id)


async def list_recent_expenses(
    pool: asyncpg.Pool, user_id: str, limit: int = 10
) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT e.*, c.name AS category_name, c.emoji AS category_emoji
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = $1
        ORDER BY e.created_at DESC
        LIMIT $2
        """,
        user_id,
        limit,
    )
    return [dict(r) for r in rows]


async def get_last_expense(pool: asyncpg.Pool, user_id: str) -> Optional[dict]:
    row = await pool.fetchrow(
        """
        SELECT e.*, c.name AS category_name, c.emoji AS category_emoji
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = $1
        ORDER BY e.created_at DESC
        LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None


async def get_expense_by_update_id(
    pool: asyncpg.Pool, update_id: int
) -> Optional[dict]:
    row = await pool.fetchrow(
        "SELECT * FROM expenses WHERE telegram_update_id = $1", update_id
    )
    return dict(row) if row else None


async def get_expenses_sum_in_period(
    pool: asyncpg.Pool,
    user_id: str,
    period_start: datetime,
    period_end: datetime,
    source: Optional[str] = None,
) -> Decimal:
    """Sum of confirmed expenses in a time range, optionally filtered by source."""
    if source is not None:
        val = await pool.fetchval(
            """
            SELECT COALESCE(SUM(amount::numeric), 0)
            FROM expenses
            WHERE user_id = $1
              AND status = 'confirmed'
              AND spent_at >= $2 AND spent_at < $3
              AND source = $4
            """,
            user_id,
            period_start,
            period_end,
            source,
        )
    else:
        val = await pool.fetchval(
            """
            SELECT COALESCE(SUM(amount::numeric), 0)
            FROM expenses
            WHERE user_id = $1
              AND status = 'confirmed'
              AND spent_at >= $2 AND spent_at < $3
              AND source != 'recurring'
            """,
            user_id,
            period_start,
            period_end,
        )
    return val or Decimal(0)


# ── Balance snapshots ─────────────────────────────────────────────────────────

async def create_balance_snapshot(
    pool: asyncpg.Pool, user_id: str, balance: float, note: Optional[str] = None
) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO balance_snapshots (user_id, balance, note)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        user_id,
        str(balance),
        note,
    )
    return dict(row)


async def get_latest_snapshot(
    pool: asyncpg.Pool, user_id: str, before: Optional[datetime] = None
) -> Optional[dict]:
    if before:
        row = await pool.fetchrow(
            """
            SELECT * FROM balance_snapshots
            WHERE user_id = $1 AND recorded_at < $2
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            user_id,
            before,
        )
    else:
        row = await pool.fetchrow(
            """
            SELECT * FROM balance_snapshots
            WHERE user_id = $1
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            user_id,
        )
    return dict(row) if row else None


async def list_balance_snapshots(
    pool: asyncpg.Pool, user_id: str, limit: int = 20
) -> list[dict]:
    rows = await pool.fetch(
        "SELECT * FROM balance_snapshots WHERE user_id = $1 ORDER BY recorded_at DESC LIMIT $2",
        user_id,
        limit,
    )
    return [dict(r) for r in rows]


# ── Reconciliations ───────────────────────────────────────────────────────────

async def create_reconciliation(pool: asyncpg.Pool, **data) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO reconciliations (
            user_id, period_start, period_end,
            opening_balance, closing_balance,
            logged_total, recurring_total,
            expected_close, discrepancy
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """,
        data["user_id"],
        data["period_start"],
        data["period_end"],
        str(data["opening_balance"]),
        str(data["closing_balance"]),
        str(data["logged_total"]),
        str(data["recurring_total"]),
        str(data["expected_close"]),
        str(data["discrepancy"]),
    )
    return dict(row)


# ── Recurring items ───────────────────────────────────────────────────────────

async def list_recurring_items(
    pool: asyncpg.Pool, user_id: str, active_only: bool = True
) -> list[dict]:
    if active_only:
        rows = await pool.fetch(
            """
            SELECT ri.*, c.name AS category_name, c.emoji AS category_emoji
            FROM recurring_items ri
            JOIN categories c ON ri.category_id = c.id
            WHERE ri.user_id = $1 AND ri.is_active = true
            ORDER BY ri.day_of_month, ri.name
            """,
            user_id,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT ri.*, c.name AS category_name, c.emoji AS category_emoji
            FROM recurring_items ri
            JOIN categories c ON ri.category_id = c.id
            WHERE ri.user_id = $1
            ORDER BY ri.day_of_month, ri.name
            """,
            user_id,
        )
    return [dict(r) for r in rows]


async def get_recurring_item(
    pool: asyncpg.Pool, item_id: str
) -> Optional[dict]:
    row = await pool.fetchrow(
        """
        SELECT ri.*, c.name AS category_name, c.emoji AS category_emoji
        FROM recurring_items ri
        JOIN categories c ON ri.category_id = c.id
        WHERE ri.id = $1
        """,
        item_id,
    )
    return dict(row) if row else None


async def create_recurring_item(pool: asyncpg.Pool, **data) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO recurring_items (
            user_id, name, amount, category_id, direction,
            day_of_month, is_active, start_date, end_date
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """,
        data["user_id"],
        data["name"],
        str(data["amount"]),
        data["category_id"],
        data.get("direction", "debit"),
        data["day_of_month"],
        data.get("is_active", True),
        data.get("start_date", date.today()),
        data.get("end_date"),
    )
    return dict(row)


async def update_recurring_item(
    pool: asyncpg.Pool, item_id: str, **data
) -> Optional[dict]:
    fields = []
    values = []
    idx = 1
    for key in ("name", "amount", "category_id", "direction", "day_of_month", "is_active", "end_date"):
        if key in data:
            fields.append(f"{key} = ${idx}")
            values.append(str(data[key]) if key == "amount" else data[key])
            idx += 1
    if not fields:
        return await get_recurring_item(pool, item_id)
    values.append(item_id)
    row = await pool.fetchrow(
        f"UPDATE recurring_items SET {', '.join(fields)} WHERE id = ${idx} RETURNING *",
        *values,
    )
    return dict(row) if row else None


async def delete_recurring_item(pool: asyncpg.Pool, item_id: str) -> None:
    await pool.execute("DELETE FROM recurring_items WHERE id = $1", item_id)


async def get_recurring_items_due_today(
    pool: asyncpg.Pool, today: date
) -> list[dict]:
    """
    Returns active recurring items whose day_of_month matches today (IST)
    and have not yet been applied this month.
    """
    rows = await pool.fetch(
        """
        SELECT ri.*, c.name AS category_name, c.emoji AS category_emoji,
               u.telegram_id, u.id AS owner_user_id
        FROM recurring_items ri
        JOIN categories c ON ri.category_id = c.id
        JOIN users u ON ri.user_id = u.id
        WHERE ri.is_active = true
          AND ri.day_of_month = $1
          AND ri.start_date <= $2
          AND (ri.end_date IS NULL OR ri.end_date >= $2)
          AND (
              ri.last_applied_on IS NULL
              OR date_trunc('month', ri.last_applied_on::timestamptz)
                 != date_trunc('month', $2::timestamptz)
          )
        """,
        today.day,
        today,
    )
    return [dict(r) for r in rows]


async def mark_recurring_applied(
    pool: asyncpg.Pool, item_id: str, applied_date: date
) -> None:
    await pool.execute(
        "UPDATE recurring_items SET last_applied_on = $1 WHERE id = $2",
        applied_date,
        item_id,
    )
