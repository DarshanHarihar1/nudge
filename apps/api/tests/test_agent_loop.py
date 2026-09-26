import asyncio

import pytest

from ai.agent_loop import AgentGaveUp, run_tool_loop


def fake_model(script):
    """Returns scripted model contents in order; records what it was sent."""
    seen = []

    async def call(system, contents, declarations):
        seen.append([dict(c) for c in contents])
        return script[len(seen) - 1]
    call.seen = seen
    return call


def call_part(name, args=None):
    return {"role": "model", "parts": [{"functionCall": {"name": name, "args": args or {}}, "thoughtSignature": "sig"}]}


def answer(text):
    return {"role": "model", "parts": [{"text": text}]}


async def echo(args):
    return {"echo": args}


TOOLS = {"echo": ({"name": "echo", "description": "d", "parameters": {"type": "object", "properties": {}}}, echo)}


def test_calls_tool_then_returns_final_json():
    model = fake_model([call_part("echo", {"x": 1}), answer('{"category": "Food"}')])
    assert asyncio.run(run_tool_loop("sys", "go", TOOLS, call_model=model)) == {"category": "Food"}
    second_turn = model.seen[1]
    assert second_turn[1]["parts"][0]["thoughtSignature"] == "sig"  # model turn passed back verbatim
    assert second_turn[2]["parts"][0]["functionResponse"] == {"name": "echo", "response": {"echo": {"x": 1}}}


def test_unknown_tool_and_crashing_tool_become_error_results():
    async def boom(args):
        raise RuntimeError("gmail down")
    tools = {**TOOLS, "boom": (TOOLS["echo"][0], boom)}
    model = fake_model([call_part("nope"), call_part("boom"), answer('{"ok": 1}')])
    assert asyncio.run(run_tool_loop("sys", "go", tools, call_model=model)) == {"ok": 1}
    assert "unknown tool" in model.seen[1][2]["parts"][0]["functionResponse"]["response"]["error"]
    assert "gmail down" in model.seen[2][4]["parts"][0]["functionResponse"]["response"]["error"]


def test_gives_up_after_max_turns():
    model = fake_model([call_part("echo")] * 3)
    with pytest.raises(AgentGaveUp):
        asyncio.run(run_tool_loop("sys", "go", TOOLS, call_model=model, max_turns=3))
