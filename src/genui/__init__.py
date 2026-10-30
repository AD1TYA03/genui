"""genui: generative UI for Python agents.

Stream OpenUI Lang from any Python agent to a React frontend using OpenUI's open-source renderer.
Free, self-hosted, zero telemetry.
"""

from .library import Library, LibraryError
from .messages import build_message, parse_message, strip_markers, to_model_messages
from .prompt import system_prompt
from .run import RunInput, parse_run_input
from .stream import encode, normalize

__version__ = "0.1.0.dev0"

__all__ = [
    "Library", "LibraryError", "RunInput", "build_message", "encode", "normalize", "parse_message",
    "parse_run_input", "strip_markers", "system_prompt", "to_model_messages",
]
