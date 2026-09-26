"""
JSON-mode LLM calls via the Gemini API: free Gemma first, Flash as fallback.

Falls back on ANY primary failure, not just rate limits — a retired model
(how Groq's llama-3.1-8b-instant broke classification) must not take the
feature down with it.
"""
import json
import os

import httpx

# ponytail: model IDs hardcoded — if Google retires one, the other still
# answers; gemini-flash-latest is an alias that tracks the current Flash.
# Thinking level is per model: Gemma accepts "minimal" (~9s -> ~2.5s), Flash
# rejects it with a 400 and wants "low".
PRIMARY_MODEL = "gemma-4-26b-a4b-it"
FALLBACK_MODEL = "gemini-flash-latest"
THINKING_LEVEL = {PRIMARY_MODEL: "minimal", FALLBACK_MODEL: "low"}

API = "https://generativelanguage.googleapis.com/v1beta/models"


def parse_json_reply(text: str) -> dict:
    """Gemma sometimes wraps its object in ```json fences or a one-item list."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(text)
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    return data


async def _generate(client: httpx.AsyncClient, model: str, system: str, text: str, temperature: float) -> dict:
    r = await client.post(
        f"{API}/{model}:generateContent",
        # Header, not ?key= — a query param would leak into error messages.
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingLevel": THINKING_LEVEL.get(model, "low")},
            },
        },
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return parse_json_reply("".join(p.get("text", "") for p in parts if not p.get("thought")))


async def generate_json(system: str, text: str, temperature: float = 0.1) -> tuple[dict, str]:
    """Returns (parsed JSON object, model that answered)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            return await _generate(client, PRIMARY_MODEL, system, text, temperature), PRIMARY_MODEL
        except Exception:
            try:
                return await _generate(client, FALLBACK_MODEL, system, text, temperature), FALLBACK_MODEL
            except Exception as e:
                raise RuntimeError(f"All LLM providers exhausted. Last error: {e}") from e
