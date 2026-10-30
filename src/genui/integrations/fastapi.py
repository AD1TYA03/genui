"""FastAPI / Starlette helpers. Requires ``pip install genui[fastapi]``."""

from __future__ import annotations

from typing import Any

try:
    from starlette.responses import StreamingResponse
except ImportError as e:  # pragma: no cover
    raise ImportError("genui.integrations.fastapi needs Starlette: pip install 'genui[fastapi]'") from e

from ..run import RunInput, parse_run_input
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


async def read_run(request: Any) -> RunInput:
    """Parse the JSON body of a Starlette/FastAPI request into a :class:`RunInput`."""
    return parse_run_input(await request.json())


__all__ = ["stream_response", "read_run", "parse_run_input", "RunInput", "SSE_HEADERS"]
