"""
Dashboard API — used by the Phase 3 web UI.
Auth: Bearer <CRON_SECRET> as a placeholder until Telegram Login Widget is wired up in Phase 3.
"""
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import CRON_SECRET, TELEGRAM_ALLOWED_ID
from db.queries import (
    create_recurring_item,
    delete_recurring_item,
    get_recurring_item,
    get_user,
    list_categories,
    list_recurring_items,
    update_category_budget,
    update_recurring_item,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
_bearer = HTTPBearer()


def _verify(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if creds.credentials != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _get_user_or_404(pool, telegram_id: int) -> dict:
    user = await get_user(pool, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")
    return user


# ── Analytics (stub) ──────────────────────────────────────────────────────────

@router.get("/analytics", dependencies=[Depends(_verify)])
async def get_analytics():
    """Aggregated chart data — full implementation in Phase 3."""
    return {}


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


@router.get("/recurring", dependencies=[Depends(_verify)])
async def list_recurring(request: Request):
    pool = request.app.state.pool
    user = await _get_user_or_404(pool, TELEGRAM_ALLOWED_ID)
    items = await list_recurring_items(pool, str(user["id"]))
    return {"items": [_serialize(i) for i in items]}


@router.post("/recurring", dependencies=[Depends(_verify)], status_code=201)
async def create_recurring(request: Request, body: RecurringCreate):
    pool = request.app.state.pool
    user = await _get_user_or_404(pool, TELEGRAM_ALLOWED_ID)

    if not 1 <= body.day_of_month <= 28:
        raise HTTPException(status_code=422, detail="day_of_month must be 1–28")

    item = await create_recurring_item(
        pool,
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


@router.patch("/recurring/{item_id}", dependencies=[Depends(_verify)])
async def patch_recurring(request: Request, item_id: str, body: RecurringUpdate):
    pool = request.app.state.pool
    updates = body.model_dump(exclude_none=True)
    item = await update_recurring_item(pool, item_id, **updates)
    if not item:
        raise HTTPException(status_code=404, detail="Recurring item not found")
    return _serialize(item)


@router.delete("/recurring/{item_id}", dependencies=[Depends(_verify)], status_code=204)
async def remove_recurring(request: Request, item_id: str):
    pool = request.app.state.pool
    existing = await get_recurring_item(pool, item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recurring item not found")
    await delete_recurring_item(pool, item_id)


# ── Categories ────────────────────────────────────────────────────────────────

class CategoryBudgetUpdate(BaseModel):
    monthly_budget: Optional[float]  # null to remove budget


@router.get("/categories", dependencies=[Depends(_verify)])
async def get_categories(request: Request):
    pool = request.app.state.pool
    user = await _get_user_or_404(pool, TELEGRAM_ALLOWED_ID)
    cats = await list_categories(pool, str(user["id"]))
    return {"categories": [_serialize(c) for c in cats]}


@router.patch("/categories/{category_id}", dependencies=[Depends(_verify)])
async def patch_category(request: Request, category_id: str, body: CategoryBudgetUpdate):
    pool = request.app.state.pool
    cat = await update_category_budget(pool, category_id, body.monthly_budget)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return _serialize(cat)


# ── helpers ───────────────────────────────────────────────────────────────────

def _serialize(obj: dict) -> dict:
    """Convert non-JSON-serialisable types (UUID, Decimal, date, datetime)."""
    import uuid
    from decimal import Decimal
    from datetime import date, datetime

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
