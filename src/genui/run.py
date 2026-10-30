"""Read the request body OpenUI's React client POSTs (an AG-UI ``RunAgentInput``)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from .messages import to_model_messages


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


def parse_run_input(body: Mapping[str, Any]) -> RunInput:
    """Parse ``{threadId, runId, messages, tools, context, ...}`` from the frontend."""
    known = {"threadId", "runId", "messages", "tools", "context"}
    raw = list(body.get("messages") or [])
    return RunInput(
        thread_id=str(body.get("threadId") or uuid.uuid4()),
        run_id=str(body.get("runId") or uuid.uuid4()),
        messages=to_model_messages(raw),
        raw_messages=raw,
        tools=list(body.get("tools") or []),
        context=list(body.get("context") or []),
        extra={k: v for k, v in body.items() if k not in known},
    )
