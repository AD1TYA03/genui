"""Auto-fix: validate the model's OpenUI Lang and let it correct its own mistakes.

Wrap the call to your model; genui streams the reply, parses it when it ends, and if the
program has errors asks the model again with the structured error list (spec/prompt.md,
section 6.2). The corrected program replaces the broken one in the same message, using the
protocol's regenerated-response rule: a new ``content`` marker, and the last content wins
(section 7.1). The model itself never sees a marker.

    from genui import autofix

    async def call_model(fix):  # `fix` is [] first, then the correction turns
        return await client.chat.completions.create(
            model=MODEL, messages=[system, *run.messages, *fix], stream=True)

    return stream_response(autofix(call_model, library), run=run)
"""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Any

from .lang import OpenUIError, parse
from .messages import PREFIX
from .stream.events import (
    Event,
    Source,
    StreamError,
    TextDelta,
    ToolCallStart,
    ToolResult,
    normalize,
)

__all__ = ["DEFAULT_FEEDBACK", "autofix", "errors_to_fix"]

log = logging.getLogger("genui")

#: The correction turn sent to the model; ``{errors}`` becomes the JSON error list.
DEFAULT_FEEDBACK = (
    "Your previous OpenUI Lang response had errors and did not render correctly:\n{errors}\n"
    "Reply again with the complete corrected program only. Follow each error's hint."
)

Generate = Callable[[list[dict[str, Any]]], Source | Awaitable[Source]]


def errors_to_fix(text: str, library: Any) -> list[OpenUIError]:
    """The errors in a finished program that are worth a correction round.

    Parser errors (unknown components, missing or mistyped props, no root ...), excluding
    warnings the page renders through. An empty or prose-only reply is not "fixed".
    """
    spec = library.to_spec() if hasattr(library, "to_spec") else library
    if not text.strip():
        return []
    result = parse(text, spec)
    errors = [e for e in result.errors if e.source == "parser" and e.severity != "warning"]
    if result.root is None and result.root_expression is None and not errors:
        errors.append(OpenUIError(source="parser", code="no-root", message="nothing renders",
                                  hint="Write a statement `root = ...` that calls a component"))
    return errors


async def _open(generate: Generate, fix: list[dict[str, Any]]) -> Source:
    source = generate(fix)
    if inspect.isawaitable(source):
        source = await source
    return source  # type: ignore[return-value]


async def autofix(
    generate: Generate,
    library: Any,
    *,
    max_retries: int = 1,
    buffer: bool = False,
    feedback: str = DEFAULT_FEEDBACK,
    check: Callable[[str], list[OpenUIError]] | None = None,
) -> AsyncIterator[Event]:
    """Run ``generate`` and re-run it with error feedback while the program has errors.

    ``generate(fix)`` returns any stream genui accepts (or an awaitable of one). ``fix`` is
    ``[]`` on the first attempt, then ``[{"role": "assistant", "content": <broken program>},
    {"role": "user", "content": <errors>}]``: append it to your messages.

    - ``max_retries``: correction rounds after the first attempt (default 1).
    - ``buffer=False`` (default) streams every attempt; a correction replaces the broken UI
      in place. ``buffer=True`` holds the program text back until it validates (or retries
      run out), so users never see a broken UI, at the cost of seeing nothing until then.
      Tool events always stream live.
    - ``check(text)`` replaces :func:`errors_to_fix` (return ``[]`` to accept).

    The program checked is the text after the last tool event, as the UI renders it.
    A :class:`StreamError` or exception ends the run without a retry.
    """
    if isinstance(library, Mapping) or hasattr(library, "to_spec"):
        spec = library
    else:
        raise TypeError("library must be a genui Library or a LibrarySpec dict")
    validate = check or (lambda text: errors_to_fix(text, spec))
    fix: list[dict[str, Any]] = []
    for attempt in range(max_retries + 1):
        final = attempt == max_retries
        program: list[str] = []
        held: list[TextDelta] = []
        marker_due = attempt > 0 and not buffer
        failed = False
        async for ev in normalize(await _open(generate, fix)):
            if isinstance(ev, TextDelta):
                program.append(ev.text)
                if buffer:
                    held.append(ev)
                    continue
                if marker_due and ev.text:
                    marker_due = False
                    # Mid-line is fine: a content marker starts its own line (section 7.1).
                    yield TextDelta(f"\n{PREFIX}content\n")
                yield ev
                continue
            if isinstance(ev, (ToolCallStart, ToolResult)):
                program.clear()  # the UI program is the text after the last tool event
                if buffer:
                    held.clear()  # preamble before a tool call is not the answer
            if isinstance(ev, StreamError):
                failed = True
            yield ev
        text = "".join(program)
        errors = [] if failed else validate(text)
        if not errors or final or failed:
            if errors:
                log.info("genui autofix: %d error(s) left after %d attempt(s)", len(errors), attempt + 1)
            for ev in held:
                yield ev
            return
        log.info("genui autofix: attempt %d had %d error(s); asking for a fix", attempt + 1, len(errors))
        fix = [
            {"role": "assistant", "content": text},
            {"role": "user", "content": feedback.format(
                errors=json.dumps([e.to_dict() for e in errors], ensure_ascii=False, indent=1))},
        ]
