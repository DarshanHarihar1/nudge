import json
import os
from typing import Optional

import httpx
from pydantic import BaseModel

CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Rent",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Health",
    "Subscriptions",
    "Education",
    "Misc",
]

SYSTEM_PROMPT = (
    "You are an expense classifier for a personal finance tracker.\n"
    "Extract structured data from a user's expense message.\n\n"
    f"Categories (pick exactly one): {', '.join(CATEGORIES)}\n\n"
    "Rules:\n"
    "- amount: the numeric amount spent (required)\n"
    "- currency: 3-letter currency code, default \"INR\" if not mentioned\n"
    "- category: best matching category from the list\n"
    "- merchant: the shop/service name if mentioned, otherwise null\n"
    "- note: any extra context (e.g. \"team lunch\"), otherwise null\n"
    "- confidence: your confidence score 0.0–1.0\n\n"
    "Return JSON only. No prose."
)


class ClassifiedExpense(BaseModel):
    amount: float
    currency: str = "INR"
    category: str
    merchant: Optional[str] = None
    note: Optional[str] = None
    confidence: float
    provider: str


def _is_rate_limit_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(x in msg for x in ["429", "rate limit", "quota", "too many requests"])


async def _classify_with_groq(text: str) -> ClassifiedExpense:
    from groq import AsyncGroq

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    client = AsyncGroq(api_key=api_key)
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    data = json.loads(response.choices[0].message.content)
    data["provider"] = "groq"
    return ClassifiedExpense(**data)


async def _classify_with_openrouter(text: str) -> ClassifiedExpense:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed["provider"] = "openrouter"
        return ClassifiedExpense(**parsed)


async def classify_expense(text: str) -> ClassifiedExpense:
    try:
        return await _classify_with_groq(text)
    except Exception as e:
        if not _is_rate_limit_error(e):
            raise

    try:
        return await _classify_with_openrouter(text)
    except Exception as e:
        raise RuntimeError(f"All LLM providers exhausted. Last error: {e}") from e
