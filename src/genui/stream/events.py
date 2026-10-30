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

    def convert(self, item: Any) -> list[Event]:
        if isinstance(item, EVENT_TYPES):
            return [item]
        if isinstance(item, str):
            return [TextDelta(item)] if item else []
        if item is None:
            return []

        # OpenAI Chat Completions chunk
        choices = _get(item, "choices")
        if choices is not None:
            return self._openai(choices)

        # Anthropic Messages stream event
        etype = _get(item, "type")
        if isinstance(etype, str) and etype.startswith(("content_block_", "message_", "ping", "error")):
            return self._anthropic(item, etype)

        # OpenAI Responses API stream event
        if isinstance(etype, str) and etype.startswith("response."):
            if etype == "response.output_text.delta":
                return [TextDelta(_get(item, "delta", ""))]
            if etype == "response.error" or etype == "response.failed":
                return [StreamError(str(_get(item, "message", "") or "LLM error"))]
            return []

        # LangChain / LangGraph message chunk (AIMessageChunk), or anything with .content
        content = _get(item, "content")
        if isinstance(content, str):
            return [TextDelta(content)] if content else []
        if isinstance(content, list):
            text = "".join(_get(p, "text", "") for p in content if _get(p, "type") in ("text", None))
            return [TextDelta(text)] if text else []

        raise TypeError(
            f"genui can't stream items of type {type(item).__name__}. Yield str, a genui event, "
            "an OpenAI/Anthropic stream item, or a LangChain message chunk."
        )

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
            if _get(block, "type") == "tool_use":
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
