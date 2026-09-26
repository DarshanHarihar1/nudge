from typing import Optional

from pydantic import BaseModel

from ai.llm import generate_json

CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Rent",
    "Entertainment",
    "Shopping",
    "Health",
    "Subscriptions",
    "Investment",
    "Credit Card",
    "Family",
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


async def classify_expense(text: str) -> ClassifiedExpense:
    data, model = await generate_json(SYSTEM_PROMPT, text)
    data["provider"] = model
    return ClassifiedExpense(**data)
