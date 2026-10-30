"""The OpenUI message protocol (spec/prompt.md, section 7) and model-history helpers.

A stored response wraps its program in marker lines::

    ]]>openui:content?library=support%401.2.0
    root = Card([title])
    ]]>openui:context
    {"formState": {...}}
    ]]>openui:end

The model never sees these lines. Use :func:`to_model_messages` to turn the chat history the
frontend sends into plain messages for your LLM.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
from urllib.parse import quote, unquote_plus

PREFIX = "]]>openui:"
_MARKER = re.compile(r"^\]\]>openui:([a-z]+)(?:\?(.*))?$")
# A regenerated response writes its content line right after the cut-off text. Start it on its own line.
_RETRY = re.compile(r"([^\n])(?=\]\]>openui:content(?:\?|\r?\n|$))")
# While streaming, hold back a mid-line `]]>openui:con` that may become a content line.
_RETRY_CUT = re.compile(r"[^\n](\]\]>[a-z:]*)$")

__all__ = [
    "ParsedMessage",
    "parse_message",
    "build_message",
    "strip_markers",
    "action_user_message",
    "to_model_messages",
]


@dataclass
class ParsedMessage:
    content: str
    """Body of the last `content` section, or the whole text when there is none."""
    context: Any = None
    """Body of the `context` section: parsed JSON, else raw text. None when absent."""
    attributes: dict[str, str] = field(default_factory=dict)
    """Attributes of the winning `content` marker, e.g. ``{"library": "support@1.2.0"}``."""
    end: bool = False
    """An `end` line follows the winning content (the stream finished)."""


def _encode(s: str) -> str:
    # Same bytes as URLSearchParams.
    return quote(s, safe="-_.*").replace("~", "%7E").replace("%20", "+")


def _read_attributes(query: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in (query or "").split("&"):
        key, eq, value = pair.partition("=")
        key = unquote_plus(key)
        if key:
            out[key] = unquote_plus(value) if eq else ""
    return out


def parse_message(raw: str, *, streaming: bool = False) -> ParsedMessage:
    """Split a stored message into content, context, attributes and the end flag (section 7.3)."""
    text = _RETRY.sub(r"\1\n", raw)
    if streaming:
        cut = _RETRY_CUT.search(text)
        if cut and f"{PREFIX}content".startswith(cut.group(1)):
            text = text[: cut.start() + 1]
    lines = text.split("\n")
    last = lines[-1]
    held = streaming and last != "" and (last.startswith(PREFIX) or PREFIX.startswith(last))
    if held:
        lines.pop()

    sections: list[dict[str, Any]] = [{"kind": None, "attributes": {}, "lines": []}]

    def close() -> None:
        body = sections[-1]["lines"]
        if body:
            body[-1] = body[-1].removesuffix("\r")

    end_at = -1
    for i, line in enumerate(lines):
        m = _MARKER.match(line.removesuffix("\r"))
        if not m:
            sections[-1]["lines"].append(line)
            continue
        close()
        if m.group(1) == "end":
            end_at = len(sections) - 1
            if i == len(lines) - 2 and lines[i + 1] == "":
                break
            continue
        sections.append({"kind": m.group(1), "attributes": _read_attributes(m.group(2)), "lines": []})
    if held:
        close()

    kinds = [s["kind"] for s in sections]
    win = max(0, _last_index(kinds, "content"))
    ctx = _last_index(kinds, "context")
    context: Any = "\n".join(sections[ctx]["lines"]) if ctx > win else None
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except ValueError:
            pass
    winner = sections[win]
    return ParsedMessage("\n".join(winner["lines"]), context, winner["attributes"], end_at >= win)


def _last_index(items: list[Any], value: Any) -> int:
    for i in range(len(items) - 1, -1, -1):
        if items[i] == value:
            return i
    return -1


def _js_json(value: Any) -> str:
    """JSON the way JavaScript's JSON.stringify writes it."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def build_message(
    content: str,
    *,
    context: Any = None,
    attributes: Mapping[str, str] | None = None,
    end: bool = False,
) -> str:
    """Write a stored message with its marker lines (section 7.4)."""
    query = "&".join(f"{_encode(k)}={_encode(v)}" for k, v in (attributes or {}).items())
    out = f"{PREFIX}content{'?' + query if query else ''}\n{content}"
    if context is not None:
        out += f"\n{PREFIX}context\n{context if isinstance(context, str) else _js_json(context)}"
    return f"{out}\n{PREFIX}end" if end else out


def strip_markers(raw: str) -> str:
    """The text a model or a person should see: the winning content, no marker lines."""
    return parse_message(raw).content


def action_user_message(message: str, form_state: Any = None, context: Any = None) -> str:
    """The stored user turn for a button click (`@ToAssistant`), as the reference chat client writes it."""
    ctx: list[Any] = [f"User clicked: {message}"]
    if form_state is not None or context is not None:
        ctx.append(form_state if form_state is not None else {})
    if context is not None:
        ctx.append(context)
    built = build_message(message, context=ctx)
    return built if message else built[built.index("\n") + 1 :]


def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # AG-UI / OpenAI content parts
        return "".join(p.get("text", "") for p in content if isinstance(p, Mapping) and p.get("type") == "text")
    return "" if content is None else str(content)


def to_model_messages(messages: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Turn the history the frontend sends into plain chat messages for an LLM (section 6.3, 7.5).

    - assistant turns become their program text, markers and stored form state removed
    - a click turn becomes ``<message>\\ncontext and form values = <json>``
    - everything else passes through with markers stripped

    Accepts AG-UI messages (``{"role", "content", "toolCalls"?, ...}``) or OpenAI-style dicts.
    Returns ``[{"role": ..., "content": str}, ...]``; tool messages keep ``tool_call_id``.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        text = _text_of(m.get("content"))
        if role in ("assistant", "user", "system", "developer") and PREFIX in text:
            parsed = parse_message(text)
            text = parsed.content
            if role == "user" and parsed.context is not None:
                text = f"{text}\ncontext and form values = {_js_json(parsed.context)}"
        msg: dict[str, Any] = {"role": role, "content": text}
        if role == "tool":
            tid = m.get("toolCallId") or m.get("tool_call_id")
            if tid:
                msg["tool_call_id"] = tid
        if role == "assistant" and (m.get("toolCalls") or m.get("tool_calls")):
            msg["tool_calls"] = m.get("toolCalls") or m.get("tool_calls")
        out.append(msg)
    return out
