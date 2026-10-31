"""Server-side chat history: the model sees what your server stored, not what the browser sends.

By default each request carries the whole conversation from the browser, so a user can edit
earlier turns ("the assistant agreed to a 90% discount"). For agents that take actions, keep
history on the server: take only the **new** user turn from the request, load the rest from a
:class:`ThreadStore`, and record the reply when the stream finishes.

    from genui.threads import MemoryThreadStore, history, record

    store = MemoryThreadStore()

    @app.post("/api/chat")
    async def chat(request: Request, user=Depends(current_user)):
        run = await read_run(request)
        key = f"{user.id}:{run.thread_id}"           # scope threads to the signed-in user
        messages = await history(store, key, run)   # stored turns + this turn's user message
        stream = await client.chat.completions.create(
            model=MODEL, messages=[{"role": "system", "content": PROMPT}, *messages], stream=True)
        return stream_response(record(store, key, run, stream), run=run)

Stores for Redis and Postgres are in ``examples/threads``. Any object with the three async
methods of :class:`ThreadStore` works.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from .messages import strip_markers
from .run import RunInput
from .stream.events import (
    Event,
    Source,
    StreamError,
    TextDelta,
    ToolCallArgs,
    ToolCallStart,
    ToolResult,
    normalize,
)

__all__ = ["MemoryThreadStore", "ThreadStore", "history", "new_turn", "record"]


@runtime_checkable
class ThreadStore(Protocol):
    """Where conversations live. ``key`` identifies one thread of one user."""

    async def load(self, key: str) -> list[dict[str, Any]]:
        """All stored messages of the thread, oldest first ([] for a new thread)."""
        ...

    async def append(self, key: str, messages: list[dict[str, Any]]) -> None:
        """Add messages to the end of the thread, atomically."""
        ...

    async def delete(self, key: str) -> None:
        """Forget the thread."""
        ...


class MemoryThreadStore:
    """A :class:`ThreadStore` in process memory: for development, tests and single-process apps.

    Keeps the ``max_threads`` most recently used threads (default 10,000) and at most
    ``max_messages`` per thread (default 500, oldest dropped). Lost on restart.
    """

    def __init__(self, *, max_threads: int = 10_000, max_messages: int = 500) -> None:
        self._threads: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.max_threads = max_threads
        self.max_messages = max_messages

    async def load(self, key: str) -> list[dict[str, Any]]:
        async with self._lock:
            msgs = self._threads.get(key)
            if msgs is None:
                return []
            self._threads.move_to_end(key)
            return [dict(m) for m in msgs]

    async def append(self, key: str, messages: list[dict[str, Any]]) -> None:
        async with self._lock:
            msgs = self._threads.setdefault(key, [])
            msgs.extend(dict(m) for m in messages)
            del msgs[: max(0, len(msgs) - self.max_messages)]
            self._threads.move_to_end(key)
            while len(self._threads) > self.max_threads:
                self._threads.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._threads.pop(key, None)


def new_turn(run: RunInput) -> dict[str, Any] | None:
    """This request's new user message: the last message, when it is the user's.

    Clicks (``@ToAssistant``) are user turns too, already formatted for the model.
    Returns ``None`` when the request ends with anything else (e.g. a regenerate).
    """
    if run.messages and run.messages[-1].get("role") == "user":
        return {"role": "user", "content": run.messages[-1].get("content") or ""}
    return None


async def history(store: ThreadStore, key: str, run: RunInput) -> list[dict[str, Any]]:
    """The messages for your model: the stored thread plus this request's new user turn.

    Everything else the browser sent is ignored. Nothing is written yet: :func:`record`
    stores the user turn together with the reply, so a failed run leaves no half turn.
    """
    stored = await store.load(key)
    turn = new_turn(run)
    return [*stored, turn] if turn else stored


async def record(
    store: ThreadStore,
    key: str,
    run: RunInput,
    source: Source,
    *,
    include_tools: bool = False,
) -> AsyncIterator[Event]:
    """Stream ``source`` unchanged, then store this turn: the user message and the reply.

    The reply stored is what the UI renders: the text after the last tool event, with
    markers stripped (so an :func:`~genui.autofix` correction stores only the fixed program).
    ``include_tools=True`` also stores the tool calls and results the server ran, as
    OpenAI-style ``assistant``/``tool`` messages, so later turns can see what was done.
    Nothing is stored if the stream fails or the client disconnects before it ends.
    """
    turn = new_turn(run)
    text: list[str] = []
    preamble: list[str] = []
    calls: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    tool_messages: list[dict[str, Any]] = []

    def flush_tools() -> None:
        # Only calls the server answered: a call without its result is rejected by model APIs.
        answered = {r["tool_call_id"] for r in results}
        done = [c for c in calls.values() if c["id"] in answered]
        if done:
            tool_messages.append({"role": "assistant", "content": "".join(preamble), "tool_calls": done})
            tool_messages.extend(r for r in results if r["tool_call_id"] in {c["id"] for c in done})
        calls.clear()
        results.clear()
        preamble.clear()

    async for ev in normalize(source):
        if isinstance(ev, StreamError):
            yield ev
            return
        if isinstance(ev, TextDelta):
            if results:  # text after tool results: that tool round is over
                flush_tools()
            text.append(ev.text)
        elif isinstance(ev, ToolCallStart):
            if results:
                flush_tools()
            if not calls:
                preamble[:] = text
            text.clear()
            calls[ev.id] = {"id": ev.id, "type": "function", "function": {"name": ev.name, "arguments": ""}}
        elif isinstance(ev, ToolCallArgs) and ev.id in calls:
            calls[ev.id]["function"]["arguments"] += ev.delta
        elif isinstance(ev, ToolResult):
            text.clear()
            results.append({"role": "tool", "tool_call_id": ev.id, "content": ev.content})
        yield ev

    flush_tools()
    reply = strip_markers("".join(text))
    turn_messages = [turn] if turn else []
    if include_tools:
        turn_messages.extend(tool_messages)
    if reply.strip():
        turn_messages.append({"role": "assistant", "content": reply})
    if turn_messages:
        await store.append(key, turn_messages)
