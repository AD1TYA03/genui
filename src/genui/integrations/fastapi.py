"""FastAPI / Starlette helpers. Requires ``pip install "genui-py[fastapi]"``."""

from __future__ import annotations

import json
from typing import Any

try:
    from starlette.exceptions import HTTPException
    from starlette.responses import StreamingResponse
except ImportError as e:  # pragma: no cover
    raise ImportError("genui.integrations.fastapi needs Starlette: pip install 'genui-py[fastapi]'") from e

from ..run import RunInput, RunInputError, parse_run_input
from ..stream import SSE_HEADERS, Format, encode
from ..stream.events import Source


def stream_response(source: Source, *, format: Format = "ag-ui", run: RunInput | None = None, **kw: Any) -> StreamingResponse:
    """Return any agent/LLM stream as an SSE response OpenUI's React client can render.

    ``source`` may yield str, genui events, OpenAI/Anthropic stream items or LangChain chunks.
    Pass ``run`` (from :func:`parse_run_input`) so AG-UI events reuse the client's thread/run ids.
    """
    if format == "ag-ui" and run is not None:
        kw.setdefault("thread_id", run.thread_id)
        kw.setdefault("run_id", run.run_id)
    return StreamingResponse(encode(source, format, **kw), media_type="text/event-stream", headers=SSE_HEADERS)


#: Largest request body :func:`read_run` accepts by default (bytes).
MAX_BODY_BYTES = 2_000_000


async def read_run(request: Any, *, max_bytes: int = MAX_BODY_BYTES, **options: Any) -> RunInput:
    """Parse the JSON body of a Starlette/FastAPI request into a :class:`RunInput`.

    Rejects bodies over ``max_bytes`` with HTTP 413 and malformed ones with HTTP 400.
    ``options`` go to :func:`parse_run_input` (``roles``, ``max_messages``, ``max_chars`` ...).
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > max_bytes:
        raise HTTPException(413, "request body too large")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(413, "request body too large")
        chunks.append(chunk)
    try:
        body = json.loads(b"".join(chunks) or b"{}")
    except ValueError:
        raise HTTPException(400, "request body is not valid JSON") from None
    try:
        return parse_run_input(body, **options)
    except RunInputError as e:
        raise HTTPException(413 if "longer than" in str(e) else 400, str(e)) from None


__all__ = ["MAX_BODY_BYTES", "RunInput", "RunInputError", "SSE_HEADERS", "parse_run_input", "read_run", "stream_response"]
