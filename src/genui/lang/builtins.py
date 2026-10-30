"""Built-in functions and actions (language.md, sections 3.4, 3.5, 6.3)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cmp_to_key
from typing import Any, Callable

from ._js import (
    is_number,
    js_round,
    locale_compare,
    loose_equal,
    norm_num,
    string_to_number,
    to_number,
    to_string,
)


@dataclass
class ParamDef:
    name: str
    required: bool = False
    #: the schema ``default``; ``NO_DEFAULT`` when absent
    default: Any = None
    has_default: bool = False
    schema: Any = None


@dataclass
class CallDef:
    kind: str  # "function" | "action"
    params: list[ParamDef] = field(default_factory=list)
    builtin: bool = False
    lazy: bool = False


def _resolve_field(obj: Any, path: str) -> Any:
    if not path or obj is None:
        return None
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        cur = _get(cur, part)
    return cur


def _get(obj: Any, key: str) -> Any:
    from ._js import get_property

    return get_property(obj, key)


def _sum(arr: list) -> float | int:
    total: float = 0
    for v in arr:
        total = total + float(to_number(v))
    return norm_num(total)


def _count(array: Any = None, **_: Any) -> Any:
    return len(array) if isinstance(array, list) else 0


def _first(array: Any = None, **_: Any) -> Any:
    return array[0] if isinstance(array, list) and array else None


def _last(array: Any = None, **_: Any) -> Any:
    return array[-1] if isinstance(array, list) and array else None


def _sum_fn(numbers: Any = None, **_: Any) -> Any:
    return _sum(numbers) if isinstance(numbers, list) else 0


def _avg(numbers: Any = None, **_: Any) -> Any:
    if isinstance(numbers, list) and numbers:
        return norm_num(float(_sum(numbers)) / len(numbers))
    return 0


def _min(numbers: Any = None, **_: Any) -> Any:
    if isinstance(numbers, list) and numbers:
        return norm_num(min(float(to_number(v)) for v in numbers))
    return 0


def _max(numbers: Any = None, **_: Any) -> Any:
    if isinstance(numbers, list) and numbers:
        return norm_num(max(float(to_number(v)) for v in numbers))
    return 0


def _is_numeric(v: Any) -> bool:
    if is_number(v):
        return True
    if isinstance(v, str) and v != "":
        n = string_to_number(v)
        return not (isinstance(n, float) and math.isnan(n))
    return False


def _sort(array: Any = None, field: Any = None, direction: Any = None, **_: Any) -> Any:
    if not isinstance(array, list):
        return array
    f = to_string("" if field is None else field)
    desc = to_string("asc" if direction is None else direction) == "desc"

    def cmp(a: Any, b: Any) -> int:
        av = _resolve_field(a, f) if f else a
        bv = _resolve_field(b, f) if f else b
        if _is_numeric(av) and _is_numeric(bv):
            diff = float(to_number(av)) - float(to_number(bv))
            r = 0 if diff == 0 or diff != diff else (1 if diff > 0 else -1)
        else:
            r = locale_compare(
                to_string("" if av is None else av), to_string("" if bv is None else bv)
            )
        return -r if desc else r

    return sorted(array, key=cmp_to_key(cmp))


def _filter(array: Any = None, field: Any = None, operator: Any = None, value: Any = None, **_: Any) -> Any:
    if not isinstance(array, list):
        return []
    f = to_string("" if field is None else field)
    op = to_string("==" if operator is None else operator)

    def keep(item: Any) -> bool:
        v = _resolve_field(item, f) if f else item
        if op == "==":
            return loose_equal(v, value)
        if op == "!=":
            return not loose_equal(v, value)
        if op == ">":
            return to_number(v) > to_number(value)
        if op == "<":
            return to_number(v) < to_number(value)
        if op == ">=":
            return to_number(v) >= to_number(value)
        if op == "<=":
            return to_number(v) <= to_number(value)
        if op == "contains":
            return to_string("" if value is None else value) in to_string("" if v is None else v)
        return False

    return [item for item in array if keep(item)]


def _round(number: Any = None, decimals: Any = None, **_: Any) -> Any:
    num = float(to_number(number))
    d = float(to_number(decimals)) if decimals is not None else 0.0
    try:
        factor = math.pow(10, d)
    except OverflowError:
        return norm_num(num)
    if factor == 0 or not math.isfinite(factor):
        return norm_num(num)
    return norm_num(float(js_round(num * factor)) / factor)


def _abs(number: Any = None, **_: Any) -> Any:
    return norm_num(abs(float(to_number(number))))


def _floor(number: Any = None, **_: Any) -> Any:
    x = float(to_number(number))
    return norm_num(float(math.floor(x))) if math.isfinite(x) else x


def _ceil(number: Any = None, **_: Any) -> Any:
    x = float(to_number(number))
    return norm_num(float(math.ceil(x))) if math.isfinite(x) else x


#: name -> (param names, implementation); ``None`` implementation means lazy.
BUILTIN_FUNCTIONS: dict[str, tuple[tuple[str, ...], Callable[..., Any] | None]] = {
    "Count": (("array",), _count),
    "First": (("array",), _first),
    "Last": (("array",), _last),
    "Sum": (("numbers",), _sum_fn),
    "Avg": (("numbers",), _avg),
    "Min": (("numbers",), _min),
    "Max": (("numbers",), _max),
    "Sort": (("array", "field", "direction"), _sort),
    "Filter": (("array", "field", "operator", "value"), _filter),
    "Round": (("number", "decimals"), _round),
    "Abs": (("number",), _abs),
    "Floor": (("number",), _floor),
    "Ceil": (("number",), _ceil),
    "Each": (("array", "varName", "template"), None),
}

#: Built-in action steps: name -> (param names, lazy)
BUILTIN_STEPS: dict[str, tuple[tuple[str, ...], bool]] = {
    "Run": (("ref",), True),
    "ToAssistant": (("message", "context"), False),
    "OpenUrl": (("url",), False),
    "Set": (("variable", "value"), True),
    "Reset": (("variable",), True),
}

#: Step type values carried by evaluated action steps.
ACTION_STEP_TYPES = {
    "Run": "run",
    "ToAssistant": "continue_conversation",
    "OpenUrl": "open_url",
    "Set": "set",
    "Reset": "reset",
}

RESERVED_CALLS = frozenset({"Query", "Mutation"})

#: The ``$defs`` names that are action shapes in every library.
ACTION_DEF_NAMES = ("ActionExpression", "OpenUrl", "ToAssistant")


def _builtin_call_defs() -> dict[str, CallDef]:
    defs: dict[str, CallDef] = {}
    for name, (params, fn) in BUILTIN_FUNCTIONS.items():
        defs[name] = CallDef("function", [ParamDef(p) for p in params], builtin=True, lazy=fn is None)
    for name, (params, lazy) in BUILTIN_STEPS.items():
        defs[name] = CallDef("action", [ParamDef(p) for p in params], builtin=True, lazy=lazy)
    defs["Action"] = CallDef("action", [ParamDef("steps", required=True)], builtin=True, lazy=True)
    return defs


BUILTIN_CALLS: dict[str, CallDef] = _builtin_call_defs()


def is_builtin(name: str) -> bool:
    """True for a built-in function, built-in step, or ``Action``."""
    return name in BUILTIN_CALLS


def is_reserved_call(name: str) -> bool:
    return name in RESERVED_CALLS


#: Every name a library must not use (language.md, section 1.3).
RESERVED_NAMES = frozenset(BUILTIN_CALLS) | RESERVED_CALLS | {"true", "false", "null"}
