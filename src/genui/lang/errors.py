"""The error object (language.md, section 8.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Codes that wait for the end of the stream before they are reported.
PARSER_CODES = frozenset({
    "unknown-component", "missing-required", "null-required", "type-mismatch", "excess-args",
    "inline-reserved", "unknown-function", "no-root", "parse-failed", "parse-exception",
})


@dataclass
class OpenUIError:
    """An error, in the one shape that crosses the wire.

    ``source`` is ``parser``, ``runtime``, ``query``, or ``mutation``. ``message``
    and ``hint`` are text for the model.
    """

    source: str
    code: str
    message: str
    statement_id: str | None = None
    component: str | None = None
    path: str | None = None
    hint: str | None = None
    tool_name: str | None = None
    #: ``"warning"`` for an error the page renders through (the non-fatal ``no-root``).
    severity: str | None = None

    @property
    def fatal(self) -> bool:
        """True when nothing renders because of this error."""
        return self.code in ("no-root", "parse-failed", "parse-exception") and self.severity != "warning"

    def to_dict(self) -> dict[str, Any]:
        """The JSON shape of section 8.3 (camelCase keys, absent fields left out)."""
        out: dict[str, Any] = {"source": self.source, "code": self.code}
        if self.statement_id is not None:
            out["statementId"] = self.statement_id
        if self.component is not None:
            out["component"] = self.component
        if self.path:
            out["path"] = self.path
        out["message"] = self.message
        if self.hint is not None:
            out["hint"] = self.hint
        if self.tool_name is not None:
            out["toolName"] = self.tool_name
        if self.severity is not None:
            out["severity"] = self.severity
        return out
