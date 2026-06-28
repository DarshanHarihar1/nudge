"""
Dashboard API — consumed by the Phase 3 web UI.
All routes require a valid session (Telegram-login cookie) or Bearer <CRON_SECRET>.
Every query is scoped to the authenticated user.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from db.queries import (
    create_recurring_item,
    delete_recurring_item,
    get_expense,
    get_recurring_item,
    get_user,
    list_categories,
    list_expenses_filtered,
    list_recurring_items,
    update_category_budget,
    update_expense,
    update_recurring_item,
)
from routers.auth import require_session
from services.analytics import build_analytics
from utils.ranges import parse_custom_range

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _user(request: Request, telegram_id: int) -> dict:
    user = await get_user(request.app.state.pool, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")
    return user


def _serialize(obj: dict) -> dict:
    """Convert UUID/Decimal/date/datetime to JSON-friendly types."""
    import uuid
    from decimal import Decimal

    out = {}
    for k, v in obj.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _serialize_expense(e: dict) -> dict:
    return {
        "id": str(e["id"]),
        "amount": float(e["amount"]),
        "currency": e["currency"],
        "category_id": str(e["category_id"]) if e.get("category_id") else None,
        "category_name": e.get("category_name"),
        "category_emoji": e.get("category_emoji"),
        "merchant": e.get("merchant"),
        "note": e.get("note"),
        "source": e["source"],
        "status": e["status"],
        "spent_at": e["spent_at"].isoformat() if e.get("spent_at") else None,
    }


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    request: Request,
    telegram_id: int = Depends(require_session),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    user = await _user(request, telegram_id)
    start, end = parse_custom_range(from_, to)
    return await build_analytics(request.app.state.pool, str(user["id"]), start, end)


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category_id: Optional[str] = None
    note: Optional[str] = None
    merchant: Optional[str] = None
    spent_at: Optional[datetime] = None


@router.get("/expenses")
async def get_expenses(
    request: Request,
    telegram_id: int = Depends(require_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    q: Optional[str] = None,
):
    user = await _user(request, telegram_id)
    start = end = None
    if from_ or to:
        start, end = parse_custom_range(from_, to)

    rows, total = await list_expenses_filtered(
        request.app.state.pool,
        str(user["id"]),
        page=page,
        limit=limit,
        category=category,
        start=start,
        end=end,
        q=q,
    )
    return {
        "expenses": [_serialize_expense(r) for r in rows],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.patch("/expenses/{expense_id}")
async def patch_expense(
    request: Request,
    expense_id: str,
    body: ExpenseUpdate,
    telegram_id: int = Depends(require_session),
):
    user = await _user(request, telegram_id)
    pool = request.app.state.pool

    existing = await get_expense(pool, expense_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Expense not found")
    if str(existing["user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    if existing["source"] in ("recurring_debit", "recurring_credit"):
        raise HTTPException(status_code=409, detail="Recurring expenses are read-only")

    updates = body.model_dump(exclude_none=True)
    updated = await update_expense(pool, expense_id, **updates)
    return _serialize_expense(updated)


# ── Recurring items ───────────────────────────────────────────────────────────

class RecurringCreate(BaseModel):
    name: str
    amount: float
    category_id: str
    direction: str = "debit"
    day_of_month: int
    is_active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RecurringUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[str] = None
    direction: Optional[str] = None
    day_of_month: Optional[int] = None
    is_active: Optional[bool] = None
    end_date: Optional[date] = None


@router.get("/recurring")
async def list_recurring(request: Request, telegram_id: int = Depends(require_session)):
    user = await _user(request, telegram_id)
    items = await list_recurring_items(request.app.state.pool, str(user["id"]))
    return {"items": [_serialize(i) for i in items]}


@router.post("/recurring", status_code=201)
async def create_recurring(
    request: Request, body: RecurringCreate, telegram_id: int = Depends(require_session)
):
    user = await _user(request, telegram_id)
    if not 1 <= body.day_of_month <= 28:
        raise HTTPException(status_code=422, detail="day_of_month must be 1–28")
    item = await create_recurring_item(
        request.app.state.pool,
        user_id=str(user["id"]),
        name=body.name,
        amount=body.amount,
        category_id=body.category_id,
        direction=body.direction,
        day_of_month=body.day_of_month,
        is_active=body.is_active,
        start_date=body.start_date or date.today(),
        end_date=body.end_date,
    )
    return _serialize(item)


@router.patch("/recurring/{item_id}")
async def patch_recurring(
    request: Request,
    item_id: str,
    body: RecurringUpdate,
    telegram_id: int = Depends(require_session),
):
    user = await _user(request, telegram_id)
    pool = request.app.state.pool
    existing = await get_recurring_item(pool, item_id)
    if not existing or str(existing["user_id"]) != str(user["id"]):
        raise HTTPException(status_code=404, detail="Recurring item not found")
    item = await update_recurring_item(pool, item_id, **body.model_dump(exclude_none=True))
    return _serialize(item)


@router.delete("/recurring/{item_id}", status_code=204)
async def remove_recurring(
    request: Request, item_id: str, telegram_id: int = Depends(require_session)
):
    user = await _user(request, telegram_id)
    pool = request.app.state.pool
    existing = await get_recurring_item(pool, item_id)
    if not existing or str(existing["user_id"]) != str(user["id"]):
        raise HTTPException(status_code=404, detail="Recurring item not found")
    await delete_recurring_item(pool, item_id)


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryBudgetUpdate(BaseModel):
    monthly_budget: Optional[float]  # null clears the budget


@router.get("/categories")
async def get_categories(request: Request, telegram_id: int = Depends(require_session)):
    user = await _user(request, telegram_id)
    cats = await list_categories(request.app.state.pool, str(user["id"]))
    return {"categories": [_serialize(c) for c in cats]}


@router.patch("/categories/{category_id}")
async def patch_category(
    request: Request,
    category_id: str,
    body: CategoryBudgetUpdate,
    telegram_id: int = Depends(require_session),
):
    await _user(request, telegram_id)
    cat = await update_category_budget(request.app.state.pool, category_id, body.monthly_budget)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return _serialize(cat)
