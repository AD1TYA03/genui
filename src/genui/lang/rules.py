"""Form field validation rules (language.md, section 5.4)."""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from ._js import is_number, number_to_string, to_string

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+\Z")
_PARSE_FLOAT_RE = re.compile(
    r"[\s ﻿]*[+-]?(?:Infinity|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)
_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*\Z")
_NUMERIC_RULES = {"min", "max", "minLength", "maxLength"}

Validator = Callable[[Any, Any], "str | None"]


def parse_float(s: str) -> float:
    """ECMAScript ``parseFloat``: the longest numeric prefix, or NaN."""
    m = _PARSE_FLOAT_RE.match(s)
    if not m:
        return math.nan
    text = m.group(0).strip()
    if text.lstrip("+-") == "Infinity":
        return -math.inf if text.startswith("-") else math.inf
    try:
        return float(text)
    except ValueError:
        return math.nan


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def is_empty(value: Any) -> bool:
    if value is None or (isinstance(value, str) and value == ""):
        return True
    if isinstance(value, list) and not value:
        return True
    if isinstance(value, dict):
        if "value" in value:
            return is_empty(value["value"])
        return not value
    return False


def _translate_pattern(pattern: str) -> str:
    """Make an ECMAScript pattern (no flags) behave the same under Python ``re``."""
    out: list[str] = []
    i = 0
    in_class = False
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\" and i + 1 < n:
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
            out.append(c)
        elif c == "[":
            in_class = True
            out.append(c)
        elif c == "$":
            out.append(r"\Z")  # end of input only (Python's $ also matches before a final \n)
        elif c == "(" and pattern.startswith("(?<", i) and not pattern.startswith(("(?<=", "(?<!"), i):
            out.append("(?P<")
            i += 3
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _required(value: Any, _arg: Any = None) -> str | None:
    if is_empty(value):
        return "This field is required"
    if isinstance(value, dict):
        vals = list(value.values())
        if vals and all(isinstance(v, bool) for v in vals) and not any(vals):
            return "At least one option is required"
    return None


def _email(value: Any, _arg: Any = None) -> str | None:
    if is_empty(value):
        return None
    if not isinstance(value, str) or not _EMAIL_RE.match(value):
        return "Please enter a valid email"
    return None


def _url(value: Any, _arg: Any = None) -> str | None:
    if is_empty(value):
        return None
    if not isinstance(value, str):
        return "Please enter a valid URL"
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return "Please enter a valid URL"
    if not parts.scheme or not _SCHEME_RE.match(parts.scheme) or not parts.netloc:
        return "Please enter a valid URL"
    return None


def _numeric(value: Any, _arg: Any = None) -> str | None:
    if is_empty(value):
        return None
    if is_number(value) and not (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str) and value.strip() != "" and not math.isnan(parse_float(value)):
        return None
    return "Must be a number"


def _as_number(value: Any) -> float:
    if is_number(value):
        return float(value)
    return parse_float(to_string(value))


def _min(value: Any, arg: Any) -> str | None:
    if is_empty(value):
        return None
    n = _as_number(value)
    if math.isnan(n):
        return None
    limit = _as_number(arg)
    return None if n >= limit else f"Must be at least {number_to_string(limit)}"


def _max(value: Any, arg: Any) -> str | None:
    if is_empty(value):
        return None
    n = _as_number(value)
    if math.isnan(n):
        return None
    limit = _as_number(arg)
    return None if n <= limit else f"Must be no more than {number_to_string(limit)}"


def _min_length(value: Any, arg: Any) -> str | None:
    if is_empty(value) or not isinstance(value, str):
        return None
    limit = _as_number(arg)
    return None if _utf16_len(value) >= limit else f"Must be at least {number_to_string(limit)} characters"


def _max_length(value: Any, arg: Any) -> str | None:
    if is_empty(value) or not isinstance(value, str):
        return None
    limit = _as_number(arg)
    return None if _utf16_len(value) <= limit else f"Must be no more than {number_to_string(limit)} characters"


def _pattern(value: Any, arg: Any) -> str | None:
    if is_empty(value) or not isinstance(value, str) or not isinstance(arg, str):
        return None
    try:
        rx = re.compile(_translate_pattern(arg), re.ASCII)
    except re.error:
        return None
    return None if rx.search(value) else "Invalid format"


VALIDATORS: dict[str, Validator] = {
    "required": _required,
    "email": _email,
    "url": _url,
    "numeric": _numeric,
    "min": _min,
    "max": _max,
    "minLength": _min_length,
    "maxLength": _max_length,
    "pattern": _pattern,
}


def parse_rules(rules: Any) -> list[tuple[str, Any]]:
    """Rules as ``(type, arg)`` pairs.

    Accepts the rules object ``{"required": true, "maxLength": 80}`` (``false``
    and ``null`` entries are skipped) or a list of strings like ``"min:8"``.
    """
    out: list[tuple[str, Any]] = []
    if isinstance(rules, Mapping):
        for key, val in rules.items():
            if val is False or val is None:
                continue
            out.append((key, None if val is True else val))
    elif isinstance(rules, list):
        for r in rules:
            if not isinstance(r, str):
                continue
            name, sep, raw = r.partition(":")
            if not sep:
                out.append((name, None))
                continue
            arg: Any = raw
            if name in _NUMERIC_RULES:
                try:
                    arg = float(raw)
                except ValueError:
                    pass
            out.append((name, arg))
    return out


def check_rules(
    value: Any,
    rules: Any,
    validators: Mapping[str, Validator] | None = None,
) -> str | None:
    """Check a field value against validation rules; the first failing rule's
    message, or None when the value passes. Unknown rules are ignored."""
    for name, arg in parse_rules(rules):
        fn = (validators or {}).get(name) or VALIDATORS.get(name)
        if fn is None:
            continue
        err = fn(value, arg)
        if err:
            return err
    return None
