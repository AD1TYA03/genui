"""Streaming: adapt any agent/LLM stream and encode it for OpenUI's React client."""

from .encoders import Format, encode, sse, to_agui, to_openai
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
    "Event", "Format", "StreamError", "TextDelta", "ToolCallArgs", "ToolCallEnd", "ToolCallStart",
    "ToolResult", "encode", "normalize", "sse", "to_agui", "to_openai",
]
