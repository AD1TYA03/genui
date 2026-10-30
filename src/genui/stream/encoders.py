"""Server-Sent Events in the two formats OpenUI's React client reads.

- ``"ag-ui"``  → AG-UI events, for ``agUIAdapter()`` (recommended; carries tool calls and errors)
- ``"openai"`` → OpenAI Chat Completions chunks, for ``openAIAdapter()``

Both yield ready-to-send SSE strings (``"data: {...}\\n\\n"``).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, Iterator, Literal

from .events import (
    Source,
    StreamError,
    TextDelta,
    ToolCallArgs,
    ToolCallEnd,
    ToolCallStart,
    ToolResult,
    normalize,
)

Format = Literal["ag-ui", "openai"]


def sse(data: Any) -> str:
    return f"data: {data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _id() -> str:
    return str(uuid.uuid4())


async def to_agui(
    source: Source,
    *,
    thread_id: str | None = None,
    run_id: str | None = None,
    message_id: str | None = None,
) -> AsyncIterator[str]:
    """Encode a stream as AG-UI SSE: RUN_STARTED … TEXT_MESSAGE_* / TOOL_CALL_* … RUN_FINISHED."""
    thread_id, run_id = thread_id or _id(), run_id or _id()
    message_id = message_id or _id()
    yield sse({"type": "RUN_STARTED", "threadId": thread_id, "runId": run_id})
    text_open = False
    after_tool = False
    open_tools: set[str] = set()

    def close_text() -> str | None:
        nonlocal text_open
        if not text_open:
            return None
        text_open = False
        return sse({"type": "TEXT_MESSAGE_END", "messageId": message_id})
    try:
        async for ev in normalize(source):
            if isinstance(ev, TextDelta):
                if not ev.text:
                    continue
                if not text_open:
                    if after_tool:  # text after a tool call is a new section of the reply
                        message_id, after_tool = _id(), False
                    yield sse({"type": "TEXT_MESSAGE_START", "messageId": message_id, "role": "assistant"})
                    text_open = True
                yield sse({"type": "TEXT_MESSAGE_CONTENT", "messageId": message_id, "delta": ev.text})
            elif isinstance(ev, ToolCallStart):
                end = close_text()
                if end:
                    yield end
                after_tool = True
                open_tools.add(ev.id)
                yield sse({"type": "TOOL_CALL_START", "toolCallId": ev.id, "toolCallName": ev.name,
                           "parentMessageId": message_id})
            elif isinstance(ev, ToolCallArgs):
                yield sse({"type": "TOOL_CALL_ARGS", "toolCallId": ev.id, "delta": ev.delta})
            elif isinstance(ev, ToolCallEnd):
                open_tools.discard(ev.id)
                yield sse({"type": "TOOL_CALL_END", "toolCallId": ev.id})
            elif isinstance(ev, ToolResult):
                after_tool = True
                yield sse({"type": "TOOL_CALL_RESULT", "messageId": _id(), "toolCallId": ev.id,
                           "content": ev.content, "role": "tool"})
            elif isinstance(ev, StreamError):
                yield sse({"type": "RUN_ERROR", "message": ev.message, **({"code": ev.code} if ev.code else {})})
                return
    except Exception as e:  # surface agent failures to the UI instead of a dead stream
        yield sse({"type": "RUN_ERROR", "message": str(e) or type(e).__name__})
        return
    for tid in open_tools:
        yield sse({"type": "TOOL_CALL_END", "toolCallId": tid})
    if text_open:
        yield sse({"type": "TEXT_MESSAGE_END", "messageId": message_id})
    yield sse({"type": "RUN_FINISHED", "threadId": thread_id, "runId": run_id})


async def to_openai(source: Source, *, model: str = "genui") -> AsyncIterator[str]:
    """Encode a stream as OpenAI Chat Completions SSE chunks, ending with ``[DONE]``."""
    cid, created = f"chatcmpl-{uuid.uuid4().hex[:24]}", int(time.time())
    tool_index: dict[str, int] = {}

    def chunk(delta: dict[str, Any], finish: str | None = None) -> str:
        return sse({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})

    yield chunk({"role": "assistant", "content": ""})
    finish = "stop"
    try:
        async for ev in normalize(source):
            if isinstance(ev, TextDelta) and ev.text:
                yield chunk({"content": ev.text})
            elif isinstance(ev, ToolCallStart):
                tool_index[ev.id] = len(tool_index)
                yield chunk({"tool_calls": [{"index": tool_index[ev.id], "id": ev.id, "type": "function",
                                             "function": {"name": ev.name, "arguments": ""}}]})
            elif isinstance(ev, ToolCallArgs) and ev.id in tool_index:
                yield chunk({"tool_calls": [{"index": tool_index[ev.id], "function": {"arguments": ev.delta}}]})
                finish = "tool_calls"
            elif isinstance(ev, StreamError):
                yield sse({"error": {"message": ev.message, "type": ev.code or "server_error"}})
                yield sse("[DONE]")
                return
    except Exception as e:
        yield sse({"error": {"message": str(e) or type(e).__name__, "type": "server_error"}})
        yield sse("[DONE]")
        return
    yield chunk({}, finish)
    yield sse("[DONE]")


SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
"""Headers to send with an SSE response (any framework)."""


def encode_sync(source: Source, format: Format = "ag-ui", **kw: Any) -> Iterator[str]:
    """Like :func:`encode`, but a plain generator for WSGI frameworks (Flask, sync Django).

    Runs the async encoder on a private event loop, one chunk at a time.
    """
    import asyncio

    agen = encode(source, format, **kw)
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                yield loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.run_until_complete(agen.aclose())
        loop.close()


def encode(source: Source, format: Format = "ag-ui", **kw: Any) -> AsyncIterator[str]:
    """Encode any supported stream as SSE in the given format."""
    if format == "ag-ui":
        return to_agui(source, **kw)
    if format == "openai":
        return to_openai(source, **kw)
    raise ValueError(f"unknown format {format!r}; use 'ag-ui' or 'openai'")
