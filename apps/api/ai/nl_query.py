"""
Natural-language query → predefined parameterized query mapping.

The LLM only ever chooses a function name from a fixed allowlist and fills
typed params. It never sees query results and never generates SQL, so there
is no injection surface. The returned mapping is always re-validated against
the allowlist before execution.
"""
from __future__ import annotations

import json
import os
from typing import Optional

ALLOWED_FUNCTIONS = {"sumByCategory", "topMerchants", "totalSpend", "countExpenses"}

VALID_RANGES = {
    "today",
    "yesterday",
    "week",
    "last_week",
    "month",
    "last_month",
    "last_3_months",
    "year",
    "all",
}

CATEGORIES = [
    "Food", "Groceries", "Transport", "Rent", "Utilities", "Entertainment",
    "Shopping", "Health", "Subscriptions", "Education", "Misc",
]

SYSTEM_PROMPT = f"""You translate a user's personal-finance question into a structured query.

Choose exactly one function:
- totalSpend: total amount spent in a period
- countExpenses: number of expenses in a period
- sumByCategory: spending grouped by category, or for one category if specified
- topMerchants: highest-spend merchants in a period

Params:
- range (required): one of {sorted(VALID_RANGES)}
- category (optional, only for sumByCategory): one of {CATEGORIES}
- limit (optional, only for topMerchants): integer 1-20, default 5

Map relative time words: "this month"->month, "last week"->last_week, "today"->today,
"this year"->year, "all time"->all. If no period is mentioned, use "month".

Return JSON only: {{"function": "...", "params": {{...}}}}. No prose."""


def validate_mapping(raw: dict) -> Optional[dict]:
    """
    Validate and normalize an LLM mapping against the allowlist.
    Returns a clean {function, params} dict, or None if invalid.
    """
    if not isinstance(raw, dict):
        return None
    func = raw.get("function")
    if func not in ALLOWED_FUNCTIONS:
        return None

    params_in = raw.get("params") or {}
    if not isinstance(params_in, dict):
        return None

    rng = params_in.get("range", "month")
    if rng not in VALID_RANGES:
        rng = "month"
    params: dict = {"range": rng}

    if func == "sumByCategory":
        cat = params_in.get("category")
        if isinstance(cat, str) and cat in CATEGORIES:
            params["category"] = cat

    if func == "topMerchants":
        limit = params_in.get("limit", 5)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 5
        params["limit"] = max(1, min(20, limit))

    return {"function": func, "params": params}


async def map_nl_query(text: str) -> Optional[dict]:
    """
    Use Groq to map free text to a validated {function, params} mapping.
    Returns None when the query can't be mapped (caller sends a fallback).
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = json.loads(response.choices[0].message.content)
    except Exception:
        return None

    return validate_mapping(raw)
