import json

import pytest

from genui.stream import StreamError, ToolCallArgs, ToolCallEnd, ToolCallStart, ToolResult, to_agui, to_openai


def events(lines):
    return [json.loads(l[6:]) for l in lines if l.startswith("data: ") and not l.startswith("data: [DONE]")]


async def collect(agen):
    return [x async for x in agen]


async def test_agui_text_from_plain_strings():
    out = events(await collect(to_agui(["root = ", 'Text("hi")'], thread_id="t", run_id="r", message_id="m")))
    assert [e["type"] for e in out] == ["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT",
                                        "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED"]
    assert "".join(e["delta"] for e in out if e["type"] == "TEXT_MESSAGE_CONTENT") == 'root = Text("hi")'
    assert out[0] == {"type": "RUN_STARTED", "threadId": "t", "runId": "r"}


async def test_agui_tools_and_errors():
    async def agent():
        yield ToolCallStart("c1", "search")
        yield ToolCallArgs("c1", '{"q":"x"}')
        yield ToolCallEnd("c1")
        yield ToolResult("c1", "[]")
        yield "done"
        yield StreamError("boom")
    types = [e["type"] for e in events(await collect(to_agui(agent())))]
    assert types == ["RUN_STARTED", "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT",
                     "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "RUN_ERROR"]


async def test_agent_exception_becomes_run_error():
    async def agent():
        yield "a"
        raise RuntimeError("model down")
    out = events(await collect(to_agui(agent())))
    assert out[-1] == {"type": "RUN_ERROR", "message": "model down"}


async def test_openai_chunks_from_openai_and_anthropic_shapes():
    openai_chunks = [{"choices": [{"delta": {"content": "root = "}}]}, {"choices": [{"delta": {"content": "x"}}]}]
    anthropic = [{"type": "message_start"}, {"type": "content_block_delta", "index": 0,
                                             "delta": {"type": "text_delta", "text": "root = x"}}]
    for src in (openai_chunks, anthropic):
        lines = await collect(to_openai(src))
        assert lines[-1] == "data: [DONE]\n\n"
        text = "".join(c["choices"][0]["delta"].get("content", "") for c in events(lines))
        assert text == "root = x"
        assert events(lines)[-1]["choices"][0]["finish_reason"] == "stop"


async def test_unknown_item_type_reports_error():
    out = events(await collect(to_agui([object()])))
    assert out[-1]["type"] == "RUN_ERROR" and "can't stream" in out[-1]["message"]
