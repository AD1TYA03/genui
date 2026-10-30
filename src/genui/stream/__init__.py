"""Streaming: adapt any agent/LLM stream and encode it for OpenUI's React client."""

from .encoders import SSE_HEADERS, Format, encode, encode_sync, sse, to_agui, to_openai
from .events import (
    Event,
    StreamError,
    TextDelta,
    ToolCallArgs,
    ToolCallEnd,
    ToolCallStart,
    ToolResult,
    normalize,
)

__all__ = [
    "SSE_HEADERS", "Event", "Format", "encode_sync", "StreamError", "TextDelta", "ToolCallArgs", "ToolCallEnd", "ToolCallStart",
    "ToolResult", "encode", "normalize", "sse", "to_agui", "to_openai",
]
