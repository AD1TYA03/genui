"""Read the request body OpenUI's React client POSTs (an AG-UI ``RunAgentInput``)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .messages import CLIENT_ROLES, to_model_messages

#: Defaults for :func:`parse_run_input`. The body comes from the browser, and everything in
#: ``messages`` is sent to your LLM, so unbounded history is a cost and abuse problem.
MAX_MESSAGES = 200
MAX_CHARS = 500_000


class RunInputError(ValueError):
    """The request body is malformed or over the limits."""


@dataclass
class RunInput:
    thread_id: str
    run_id: str
    messages: list[dict[str, Any]]
    """History as plain chat messages, ready for your LLM (markers stripped, clicks formatted)."""
    raw_messages: list[dict[str, Any]] = field(default_factory=list)
    tools: list[Any] = field(default_factory=list)
    context: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    """Any other fields the frontend sent (e.g. ``body: { model }`` in ``fetchLLM``)."""

    def text_messages(self) -> list[dict[str, str]]:
        """User and assistant turns with text only, merged so roles alternate.

        For APIs that reject OpenAI-only shapes (``system``/``tool`` roles, ``tool_calls``),
        such as Anthropic Messages or the OpenAI Agents SDK input.
        """
        out: list[dict[str, str]] = []
        for m in self.messages:
            role, text = m.get("role"), m.get("content") or ""
            if role not in ("user", "assistant") or not text:
                continue
            if out and out[-1]["role"] == role:
                out[-1]["content"] += "\n\n" + text
            else:
                out.append({"role": role, "content": text})
        return out

    def anthropic(self, system: str) -> dict[str, Any]:
        """Keyword arguments for ``client.messages.create(**run.anthropic(system_prompt), ...)``."""
        msgs = self.text_messages()
        while msgs and msgs[0]["role"] != "user":  # Anthropic requires the first turn to be the user's
            msgs.pop(0)
        return {"system": system, "messages": msgs}

    @property
    def last_user_message(self) -> str:
        for m in reversed(self.messages):
            if m.get("role") == "user":
                return m.get("content") or ""
        return ""


def _trim(messages: list[dict[str, Any]], max_messages: int, max_chars: int) -> list[dict[str, Any]]:
    """Keep the newest messages within both limits."""
    kept: list[dict[str, Any]] = []
    total = 0
    for m in reversed(messages):
        size = len(m.get("content") or "")
        if len(kept) >= max_messages or total + size > max_chars:
            break
        kept.append(m)
        total += size
    if messages and not kept:
        raise RunInputError(f"the latest message is longer than {max_chars:,} characters")
    kept.reverse()
    return kept


def parse_run_input(
    body: Mapping[str, Any],
    *,
    roles: Iterable[str] = CLIENT_ROLES,
    tool_calls: bool = False,
    max_messages: int = MAX_MESSAGES,
    max_chars: int = MAX_CHARS,
) -> RunInput:
    """Parse ``{threadId, runId, messages, tools, context, ...}`` from the frontend.

    The body is untrusted. ``messages`` keeps only ``roles`` (default user and assistant; see
    :func:`~genui.messages.to_model_messages`) and the newest turns within ``max_messages``
    and ``max_chars``. Raises :class:`RunInputError` for a malformed body or a single message
    over ``max_chars``. ``raw_messages``, ``tools``, ``context`` and ``extra`` are passed
    through unchecked: never hand client-sent ``tools`` to your model, and validate any
    ``extra`` field (such as a model name) against an allowlist.
    """
    if not isinstance(body, Mapping):
        raise RunInputError("request body must be a JSON object")
    raw = body.get("messages") or []
    if not isinstance(raw, list):
        raise RunInputError("messages must be a list")
    known = {"threadId", "runId", "messages", "tools", "context"}
    messages = to_model_messages(raw, roles=roles, tool_calls=tool_calls)
    return RunInput(
        thread_id=str(body.get("threadId") or uuid.uuid4()),
        run_id=str(body.get("runId") or uuid.uuid4()),
        messages=_trim(messages, max_messages, max_chars),
        raw_messages=raw,
        tools=list(body.get("tools") or []),
        context=list(body.get("context") or []),
        extra={k: v for k, v in body.items() if k not in known},
    )
