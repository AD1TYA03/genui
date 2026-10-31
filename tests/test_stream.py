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
    assert out[-1] == {"type": "RUN_ERROR", "message": "The agent failed. Please try again."}
    out = events(await collect(to_agui(agent(), expose_errors=True)))
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
    out = events(await collect(to_agui([object()], expose_errors=True)))
    assert out[-1]["type"] == "RUN_ERROR" and "can't stream" in out[-1]["message"]


async def test_langgraph_tuples_toolmessages_and_split_messages():
    class AIMessageChunk:
        def __init__(self, content="", tool_call_chunks=None):
            self.content, self.tool_call_chunks, self.type = content, tool_call_chunks or [], "AIMessageChunk"

    class ToolMessage:
        type = "tool"
        def __init__(self, content, tool_call_id):
            self.content, self.tool_call_id = content, tool_call_id

    src = [
        (AIMessageChunk("Let me check. "), {}),
        (AIMessageChunk(tool_call_chunks=[{"index": 0, "id": "c1", "name": "weather", "args": '{"q":"Paris"}'}]), {}),
        (ToolMessage("Sunny in Paris", "c1"), {}),
        (AIMessageChunk('root = Text("sunny")'), {}),
    ]
    out = events(await collect(to_agui(src)))
    types = [e["type"] for e in out]
    assert "TOOL_CALL_START" in types and "TOOL_CALL_RESULT" in types
    texts = [e for e in out if e["type"] == "TEXT_MESSAGE_CONTENT"]
    assert texts[-1]["delta"] == 'root = Text("sunny")'
    assert texts[0]["messageId"] != texts[-1]["messageId"]  # new section after the tool
    assert all("Sunny in Paris" not in e.get("delta", "") for e in texts)


async def test_agents_sdk_and_responses_tool_calls():
    class Ev:
        def __init__(self, **kw): self.__dict__.update(kw)
    src = [
        Ev(type="raw_response_event", data={"type": "response.output_item.added",
                                             "item": {"type": "function_call", "id": "fc1", "call_id": "call_1", "name": "search"}}),
        Ev(type="raw_response_event", data={"type": "response.function_call_arguments.delta", "item_id": "fc1", "delta": "{}"}),
        Ev(type="raw_response_event", data={"type": "response.output_item.done", "item": {"id": "fc1"}}),
        Ev(type="run_item_stream_event", name="tool_output", item=Ev(raw_item={"call_id": "call_1"}, output="[]")),
        Ev(type="agent_updated_stream_event"),
        Ev(type="raw_response_event", data={"type": "response.output_text.delta", "delta": "root = x"}),
    ]
    types = [e["type"] for e in events(await collect(to_agui(src)))]
    assert types[1:5] == ["TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT"]
    assert "TEXT_MESSAGE_CONTENT" in types and types[-1] == "RUN_FINISHED"


def test_encode_sync_and_text_messages():
    from genui.run import parse_run_input
    from genui.stream import encode_sync
    lines = list(encode_sync(["root = ", "x"]))
    assert lines[0].startswith("data: ") and "RUN_FINISHED" in lines[-1]
    run = parse_run_input({"messages": [{"role": "system", "content": "s"}, {"role": "assistant", "content": "hi"},
                                        {"role": "user", "content": "a"}, {"role": "user", "content": "b"},
                                        {"role": "tool", "content": "t", "toolCallId": "1"}]})
    assert run.text_messages() == [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "a\n\nb"}]
    assert run.anthropic("SYS") == {"system": "SYS", "messages": [{"role": "user", "content": "a\n\nb"}]}
