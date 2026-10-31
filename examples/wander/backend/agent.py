"""The Wander concierge: a tool-calling loop over Gemini (OpenAI-compatible API) whose final
answer is OpenUI Lang, streamed through genui.

    run_agent(history) -> async iterator of str (OpenUI Lang deltas) and genui tool events

Each round calls the model with streaming on and the Wander tools attached:
- tool calls are executed locally and surfaced to the UI as ToolCallStart / ToolCallArgs /
  ToolCallEnd / ToolResult (AG-UI TOOL_CALL_* events), so the frontend can show
  "searching stays..." while the model works;
- text is streamed straight through, after a short hold-back (until its first newline) so the
  odd sentence a model writes before deciding to call a tool never reaches the UI.

Validation / repair choice: the final program is parsed with ``genui.lang.parse``. Errors are
logged and, instead of an in-turn repair round (which would mean buffering the whole answer and
losing the live-streaming UI, or streaming a second program on top of the first), they are fed
back to the model on the NEXT request (spec/prompt.md section 6.2): the previous assistant
program is re-parsed from the history and its structured errors are appended as a system note.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from datetime import date
from pathlib import Path
from typing import Any, AsyncIterator, Union

from genui import Library
from genui.lang import parse
from genui.stream.events import StreamError, ToolCallArgs, ToolCallEnd, ToolCallStart, ToolResult

from tools import TOOL_SCHEMAS, run_tool

log = logging.getLogger("wander.agent")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
#: Gemini's OpenAI-compatible endpoint takes bare model ids (no "models/" prefix).
#: gemini-3.8-flash is the current Flash model in Google's model list and OpenAI-compat docs.
#: Faster/cheaper alternative: "gemini-3.5-flash-lite". Override with the MODEL env var.
DEFAULT_MODEL = "gemini-3-flash-preview"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
KEYCHAIN_SERVICE = "gemini-api-key"
MAX_ROUNDS = 6

HERE = Path(__file__).resolve().parent


# ─── Library and system prompt ───────────────────────────────────────────────

def spec_path() -> Path:
    """spec.json (written by the frontend's `npm run generate`) wins over the dev stand-in."""
    real = HERE / "spec.json"
    return real if real.exists() else HERE / "spec.dev.json"


library = Library.from_spec(spec_path())
SPEC = library.to_spec()

PREAMBLE = (
    "You are Wander, a warm, well-travelled concierge who helps people find and book "
    "extraordinary stays across India: Himalayan treehouses, desert domes, Kerala and Kashmir "
    "houseboats, Ladakh glamping, coffee-estate cottages, Spiti mud homes. You build the user "
    "interface yourself, in OpenUI Lang, from the components below."
)


def additional_rules(today: date) -> list[str]:
    return [
        f"Today is {today:%A, %d %B %Y} ({today.isoformat()}). Dates are ISO YYYY-MM-DD and must be after today.",
        "Always answer with an OpenUI Lang program whose root is a Stack. Never answer in plain prose or markdown; put prose in Text components.",
        "Use the tools for every fact about stays, availability, prices and bookings. Never invent stays, ids, prices or availability.",
        "Image URLs (StayCard.image, StayDetail.images, BookingTicket.image) must be copied exactly from tool results. Never write any other URL.",
        "All prices are in Indian rupees (INR); pass numbers, not formatted strings.",
        'Flow: greet with a Heading, a short Text and Suggestions. When the user asks for stays, call search_stays and show a StayGrid of StayCards; each StayCard action is @ToAssistant("Show <name>", {"stayId": "<id>"}).',
        'When the user picks a stay, call get_stay and show a StayDetail plus a Form containing a DateRangePicker (blocked = the stay\'s blocked dates, minNights 1), a GuestPicker (max = maxGuests) and a Button "Check availability" with action @ToAssistant("Check availability", {"stayId": "<id>"}). Bind the pickers to $checkIn, $checkOut, $adults, $children with sensible defaults ($adults = 2, $children = 0).',
        'When the user asks to check dates (form values arrive with the message), call check_availability. If available, show a PriceSummary built from price_lines and total plus a Button "Confirm booking" with @ToAssistant("Confirm booking", {"stayId": "<id>", "checkIn": "...", "checkOut": "...", "adults": n, "children": n}). If not, show a Callout (tone "warning") naming the clashing dates and the Form again.',
        "Only call create_booking after the user confirms. Then show a BookingTicket with the returned code and fields, a Callout (tone \"success\") and Suggestions for what to do next.",
        "End most answers with Suggestions offering 2-4 short, specific next steps.",
    ]


def build_system_prompt(today: date | None = None) -> str:
    today = today or date.today()
    return library.system_prompt(
        bindings=True,  # DateRangePicker / GuestPicker take $binding<...> props
        preamble=PREAMBLE,
        additional_rules=additional_rules(today),
    )


# ─── Model client ────────────────────────────────────────────────────────────

def gemini_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


_client: Any = None


def get_client() -> Any:
    """The AsyncOpenAI client for Gemini, created on first use (tests replace it)."""
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        key = gemini_api_key()
        if not key:
            raise RuntimeError(
                "No Gemini API key. Set GEMINI_API_KEY or run: "
                f"security add-generic-password -U -a genui -s {KEYCHAIN_SERVICE} -w"
            )
        _client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=key)
    return _client


def set_client(client: Any) -> None:
    global _client
    _client = client


# ─── History ─────────────────────────────────────────────────────────────────

def validation_errors(program: str) -> list[dict[str, Any]]:
    """Structured errors (spec language.md 8.3 shape) for a complete program, warnings excluded."""
    result = parse(program, SPEC)
    return [e.to_dict() for e in result.errors if e.severity != "warning"]


def prepare_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Plain user/assistant text turns for the model.

    Tool calls and tool results of earlier turns are dropped: the UI may or may not send them
    back, and Gemini rejects replayed tool calls that lost their thought signatures. Each turn's
    UI program is enough context. If the last assistant program had errors, they are appended
    as a system note so the model fixes them this turn (spec/prompt.md 6.2).
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""
        if role not in ("user", "assistant") or not content.strip():
            continue
        out.append({"role": role, "content": content})
    last_assistant = next((m for m in reversed(out) if m["role"] == "assistant"), None)
    if last_assistant is not None:
        errors = validation_errors(last_assistant["content"])
        if errors:
            out.append({
                "role": "system",
                "content": "Your previous OpenUI Lang response had these errors; avoid them in this response: "
                + json.dumps(errors, ensure_ascii=False),
            })
    return out


# ─── Agent loop ──────────────────────────────────────────────────────────────

Item = Union[str, ToolCallStart, ToolCallArgs, ToolCallEnd, ToolResult, StreamError]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    val = getattr(obj, key, None)
    if val is None:  # pydantic models keep unknown fields (e.g. Gemini's extra_content) here
        extra = getattr(obj, "model_extra", None) or {}
        val = extra.get(key, default)
    return default if val is None else val


class _ToolCallAcc:
    def __init__(self) -> None:
        self.id = ""
        self.name = ""
        self.arguments = ""
        self.extra_content: Any = None

    def add(self, tc: Any) -> None:
        self.id = self.id or _get(tc, "id", "")
        fn = _get(tc, "function")
        if fn is not None:
            self.name = self.name or _get(fn, "name", "")
            self.arguments += _get(fn, "arguments", "") or ""
        extra = _get(tc, "extra_content")
        if extra:  # Gemini 3 thought signature; must be sent back with the call
            self.extra_content = extra

    def message(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"id": self.id, "type": "function",
                               "function": {"name": self.name, "arguments": self.arguments or "{}"}}
        if self.extra_content:
            msg["extra_content"] = self.extra_content
        return msg


async def run_agent(
    history: list[dict[str, Any]],
    *,
    client: Any = None,
    model: str | None = None,
    today: date | None = None,
) -> AsyncIterator[Item]:
    """Run the concierge on the chat history; yield OpenUI Lang text and tool events."""
    today = today or date.today()
    if client is None:
        try:
            client = get_client()
        except RuntimeError:
            # A deliberate, safe message: genui hides raw exception text from the browser.
            yield StreamError("The server has no Gemini API key. Set GEMINI_API_KEY and restart it.")
            return
    model = model or MODEL
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt(today)},
        *prepare_history(history),
    ]

    for round_no in range(MAX_ROUNDS):
        last_round = round_no == MAX_ROUNDS - 1
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            tools=TOOL_SCHEMAS,
            tool_choice="none" if last_round else "auto",
        )
        calls: dict[int, _ToolCallAcc] = {}
        text = ""          # everything the model wrote this round
        pending = ""       # held back until we know this is the answer, not a pre-tool remark
        live = False
        async for chunk in stream:
            choices = _get(chunk, "choices") or []
            if not choices:
                continue
            delta = _get(choices[0], "delta")
            if delta is None:
                continue
            for tc in _get(delta, "tool_calls") or []:
                calls.setdefault(_get(tc, "index", len(calls)), _ToolCallAcc()).add(tc)
            piece = _get(delta, "content") or ""
            if not piece:
                continue
            text += piece
            if live:
                yield piece
            elif not calls:
                pending += piece
                if "\n" in pending.lstrip():
                    live = True
                    yield pending
                    pending = ""

        if not calls:
            if pending:
                yield pending
            errors = validation_errors(text)
            if errors:
                log.warning("program has %d error(s): %s", len(errors), errors)
            return

        # A tool round: surface the calls, run them, feed the results back.
        tool_calls = []
        for acc in calls.values():
            acc.id = acc.id or f"call_{uuid.uuid4().hex[:12]}"
            tool_calls.append(acc.message())
        messages.append({"role": "assistant", "content": text or None, "tool_calls": tool_calls})
        for acc in calls.values():
            yield ToolCallStart(acc.id, acc.name)
            yield ToolCallArgs(acc.id, acc.arguments or "{}")
            yield ToolCallEnd(acc.id)
            result = run_tool(acc.name, acc.arguments, today=today)
            yield ToolResult(acc.id, result)
            messages.append({"role": "tool", "tool_call_id": acc.id, "content": result})

    # Only reached if the model ignored tool_choice="none" on the last round.
    yield 'root = Stack([Callout("Sorry", "I got lost planning that. Please try again.", "warning")])'
