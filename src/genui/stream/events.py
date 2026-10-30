"""Provider-neutral stream events, and adapters from common LLM / agent streams.

Everything genui streams goes through these few events. Adapters turn whatever your agent yields
(plain strings, OpenAI chunks, Anthropic events, or these events) into them, so the encoders in
:mod:`genui.stream.agui` and :mod:`genui.stream.openai` never care where text came from.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, AsyncIterable, AsyncIterator, Iterable, Union


@dataclass(frozen=True)
class TextDelta:
    """A piece of assistant text (OpenUI Lang, or prose in inline mode)."""

    text: str


@dataclass(frozen=True)
class ToolCallStart:
    id: str
    name: str


@dataclass(frozen=True)
class ToolCallArgs:
    id: str
    delta: str


@dataclass(frozen=True)
class ToolCallEnd:
    id: str


@dataclass(frozen=True)
class ToolResult:
    id: str
    content: str


@dataclass(frozen=True)
class StreamError:
    message: str
    code: str | None = None


Event = Union[TextDelta, ToolCallStart, ToolCallArgs, ToolCallEnd, ToolResult, StreamError]
EVENT_TYPES = (TextDelta, ToolCallStart, ToolCallArgs, ToolCallEnd, ToolResult, StreamError)

Source = Union[AsyncIterable[Any], Iterable[Any]]


async def aiter_any(source: Source) -> AsyncIterator[Any]:
    """Iterate a sync or async iterable (or an awaitable returning one) asynchronously."""
    if inspect.isawaitable(source):
        source = await source  # type: ignore[assignment]
    if hasattr(source, "__aiter__"):
        async for item in source:  # type: ignore[union-attr]
            yield item
    else:
        for item in source:  # type: ignore[union-attr]
            yield item


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class _Normalizer:
    """Stateful conversion of one provider item into genui events."""

    def __init__(self) -> None:
        self.tool_ids: dict[int, str] = {}  # OpenAI tool-call index -> id
        self.block_tools: dict[int, str] = {}  # Anthropic content-block index -> tool id
        self.resp_items: dict[str, str] = {}  # Responses API output item id -> call id
        self.lc_started: set[str] = set()  # LangChain tool calls already started

    def convert(self, item: Any) -> list[Event]:
        if isinstance(item, EVENT_TYPES):
            return [item]
        if isinstance(item, str):
            return [TextDelta(item)] if item else []
        if item is None:
            return []

        # LangGraph stream_mode="messages" yields (message_chunk, metadata) tuples
        if isinstance(item, tuple) and item:
            return self.convert(item[0])

        # OpenAI Chat Completions chunk
        choices = _get(item, "choices")
        if choices is not None:
            return self._openai(choices)

        etype = _get(item, "type")

        # OpenAI Agents SDK stream events
        if etype == "raw_response_event":
            return self.convert(_get(item, "data"))
        if etype == "run_item_stream_event":
            return self._agents_item(item)
        if etype == "agent_updated_stream_event":
            return []

        # Anthropic Messages stream event
        if isinstance(etype, str) and etype.startswith(("content_block_", "message_", "ping", "error")):
            return self._anthropic(item, etype)

        # OpenAI Responses API stream event
        if isinstance(etype, str) and etype.startswith("response."):
            return self._responses(item, etype)

        # LangChain tool result message: a tool result, never UI text
        if etype == "tool" or type(item).__name__ in ("ToolMessage", "ToolMessageChunk"):
            tid = _get(item, "tool_call_id")
            content = _get(item, "content")
            return [ToolResult(tid, content if isinstance(content, str) else str(content))] if tid else []

        # LangChain / LangGraph message chunk (AIMessageChunk), or anything with .content
        out: list[Event] = []
        content = _get(item, "content")
        if isinstance(content, str):
            if content:
                out.append(TextDelta(content))
        elif isinstance(content, list):
            text = "".join(_get(p, "text", "") for p in content if _get(p, "type") in ("text", None))
            if text:
                out.append(TextDelta(text))
        elif content is None and _get(item, "tool_call_chunks") is None:
            raise TypeError(
                f"genui can't stream items of type {type(item).__name__}. Yield str, a genui event, "
                "an OpenAI/Anthropic stream item, an OpenAI Agents SDK event, or a LangChain message chunk."
            )
        for tc in _get(item, "tool_call_chunks") or []:
            idx = _get(tc, "index", 0) or 0
            tid, name, args = _get(tc, "id"), _get(tc, "name"), _get(tc, "args")
            if tid and tid not in self.lc_started:
                self.lc_started.add(tid)
                self.tool_ids[idx] = tid
                out.append(ToolCallStart(tid, name or ""))
            if args and idx in self.tool_ids:
                out.append(ToolCallArgs(self.tool_ids[idx], args))
        return out

    def _responses(self, item: Any, etype: str) -> list[Event]:
        if etype == "response.output_text.delta":
            return [TextDelta(_get(item, "delta", ""))]
        if etype == "response.output_item.added":
            it = _get(item, "item")
            if _get(it, "type") == "function_call":
                tid = _get(it, "call_id") or _get(it, "id")
                self.resp_items[_get(it, "id")] = tid
                return [ToolCallStart(tid, _get(it, "name", ""))]
            return []
        if etype == "response.function_call_arguments.delta":
            tid = self.resp_items.get(_get(item, "item_id"))
            return [ToolCallArgs(tid, _get(item, "delta", ""))] if tid else []
        if etype == "response.output_item.done":
            it = _get(item, "item")
            tid = self.resp_items.pop(_get(it, "id"), None)
            return [ToolCallEnd(tid)] if tid else []
        if etype in ("response.error", "response.failed", "error"):
            err = _get(item, "error")
            msg = _get(err, "message") if err is not None else _get(item, "message")
            return [StreamError(str(msg or "LLM error"))]
        return []

    def _agents_item(self, item: Any) -> list[Event]:
        name, run_item = _get(item, "name"), _get(item, "item")
        raw = _get(run_item, "raw_item")
        if name == "tool_output":
            tid = _get(raw, "call_id") or _get(raw, "tool_call_id")
            out = _get(run_item, "output")
            return [ToolResult(tid, out if isinstance(out, str) else str(out))] if tid else []
        # tool_called / message_output_created repeat what raw events already streamed
        return []

    def _openai(self, choices: Any) -> list[Event]:
        if not choices:
            return []
        delta = _get(choices[0], "delta")
        out: list[Event] = []
        if delta is not None:
            text = _get(delta, "content")
            if text:
                out.append(TextDelta(text))
            for tc in _get(delta, "tool_calls") or []:
                idx = _get(tc, "index", 0)
                tid = _get(tc, "id")
                fn = _get(tc, "function")
                if tid:
                    self.tool_ids[idx] = tid
                    out.append(ToolCallStart(tid, _get(fn, "name", "") or ""))
                args = _get(fn, "arguments") if fn is not None else None
                if args and idx in self.tool_ids:
                    out.append(ToolCallArgs(self.tool_ids[idx], args))
        if _get(choices[0], "finish_reason") == "tool_calls":
            out.extend(ToolCallEnd(t) for t in self.tool_ids.values())
            self.tool_ids.clear()
        return out

    def _anthropic(self, item: Any, etype: str) -> list[Event]:
        if etype == "content_block_start":
            block = _get(item, "content_block")
            if _get(block, "type") in ("tool_use", "server_tool_use"):
                tid = _get(block, "id")
                self.block_tools[_get(item, "index", 0)] = tid
                return [ToolCallStart(tid, _get(block, "name", ""))]
            text = _get(block, "text")
            return [TextDelta(text)] if text else []
        if etype == "content_block_delta":
            delta = _get(item, "delta")
            dtype = _get(delta, "type")
            if dtype == "text_delta":
                return [TextDelta(_get(delta, "text", ""))]
            if dtype == "input_json_delta":
                tid = self.block_tools.get(_get(item, "index", 0))
                return [ToolCallArgs(tid, _get(delta, "partial_json", ""))] if tid else []
            return []
        if etype == "content_block_stop":
            tid = self.block_tools.pop(_get(item, "index", 0), None)
            return [ToolCallEnd(tid)] if tid else []
        if etype == "error":
            err = _get(item, "error")
            return [StreamError(str(_get(err, "message", "") or "LLM error"), _get(err, "type"))]
        return []


async def normalize(source: Source) -> AsyncIterator[Event]:
    """Turn any supported agent/LLM stream into genui events.

    Supported items: ``str`` text deltas, genui events, OpenAI Chat Completions chunks, OpenAI
    Responses events, Anthropic Messages stream events, LangChain message chunks. Sync or async.
    """
    n = _Normalizer()
    async for item in aiter_any(source):
        for ev in n.convert(item):
            yield ev
