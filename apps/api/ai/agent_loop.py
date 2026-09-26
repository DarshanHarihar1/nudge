"""
Minimal agent loop: the model picks tools, we run them and feed results back,
until it answers with JSON. Tools are read-only; the caller decides what to
do with the answer.
"""
from typing import Awaitable, Callable

from ai.llm import FALLBACK_MODEL, generate_content, parse_json_reply

Tool = tuple[dict, Callable[[dict], Awaitable[dict]]]


class AgentGaveUp(Exception):
    pass


async def _default_model(system: str, contents: list[dict], declarations: list[dict]) -> dict:
    # Flash, not Gemma: multi-step tool use needs the stronger model.
    return await generate_content(FALLBACK_MODEL, system, contents, declarations)


async def run_tool_loop(
    system: str, prompt: str, tools: dict[str, Tool], call_model=None, max_turns: int = 6
) -> dict:
    call_model = call_model or _default_model
    declarations = [decl for decl, _ in tools.values()]
    contents: list[dict] = [{"role": "user", "parts": [{"text": prompt}]}]
    for _ in range(max_turns):
        content = await call_model(system, contents, declarations)
        contents.append(content)
        calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
        if not calls:
            text = "".join(p.get("text", "") for p in content.get("parts", []) if not p.get("thought"))
            return parse_json_reply(text)
        results = []
        for call in calls:
            handler = tools.get(call["name"], (None, None))[1]
            try:
                result = await handler(call.get("args") or {}) if handler else {"error": f"unknown tool {call['name']}"}
            except Exception as e:
                result = {"error": f"{type(e).__name__}: {e}"}
            results.append({"functionResponse": {"name": call["name"], "response": result}})
        contents.append({"role": "user", "parts": results})
    raise AgentGaveUp(f"no answer after {max_turns} turns")
