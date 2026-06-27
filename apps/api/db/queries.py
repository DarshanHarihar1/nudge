import asyncpg
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
        "UPDATE expenses SET status = 'confirmed' WHERE id = $1",
        expense_id,
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
