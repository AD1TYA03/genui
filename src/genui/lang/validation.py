"""Argument validation against the library schema (language.md, sections 8.2 and 8.4)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Collection

from ._js import strict_equal, typeof
from .tsjson import as_element, is_ast_like, is_element_like
from .builtins import ParamDef
from .errors import OpenUIError
from .values import ActionPlan, Binding, Element

#: Marker for a value that failed validation.
INVALID: Any = type("_Invalid", (), {"__repr__": lambda self: "INVALID"})()
#: Marker for "leave the prop out".
OMIT: Any = type("_Omit", (), {"__repr__": lambda self: "OMIT"})()

_SCALAR_TYPEOFS = ("string", "number", "boolean")


@dataclass
class IssueCtx:
    """Where validation issues go, and what they are attributed to."""

    errors: list[OpenUIError] = field(default_factory=list)
    partial: bool = False
    current_statement_id: str | None = None
    #: component names, for component-only slot detection
    components: Collection[str] = ()
    source: str = "parser"


def _dumps(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(v)


def _ref_name(s: dict) -> str | None:
    ref = s.get("$ref")
    return ref.split("/")[-1] if isinstance(ref, str) else None


def _is_composite(s: dict) -> bool:
    return "$ref" in s or "anyOf" in s or "oneOf" in s or "allOf" in s


def _scalar_info(s: dict) -> tuple[str | None, list | None]:
    if isinstance(s.get("enum"), list):
        return None, s["enum"]
    if "const" in s:
        return None, [s["const"]]
    t = s.get("type")
    if t == "string":
        return "string", None
    if t in ("number", "integer"):
        return "number", None
    if t == "boolean":
        return "boolean", None
    return None, None


def _js_type(v: Any) -> str:
    return "array" if isinstance(v, list) else typeof(v)


def type_of_schema(prop: Any) -> str | None:
    if not isinstance(prop, dict):
        return None
    ref = _ref_name(prop)
    if ref:
        return ref
    expected, enum = _scalar_info(prop)
    if enum is not None:
        return "|".join(_dumps(v) for v in enum)
    if expected:
        return expected
    t = prop.get("type")
    return t if isinstance(t, str) else None


def params_signature(name: str, params: list[ParamDef]) -> str:
    """``Header(title*: string, variant: "a"|"b")``; ``*`` marks required."""
    parts = []
    for p in params:
        marked = f"{p.name}*" if p.required else p.name
        t = type_of_schema(p.schema)
        parts.append(f"{marked}: {t}" if t else marked)
    return f"{name}({', '.join(parts)})"


def signature_hint(name: str, params: list[ParamDef] | None) -> str | None:
    if params is None:
        return None
    marked = ", ".join(f"{p.name}*" if p.required else p.name for p in params)
    return f"Signature: {name}({marked}). * marks required"


def push_issue(
    ctx: IssueCtx,
    component: str,
    path: str,
    code: str,
    message: str,
    hint: str | None = None,
    severity: str | None = None,
) -> None:
    ctx.errors.append(OpenUIError(
        source=ctx.source,
        code=code,
        message=message,
        statement_id=ctx.current_statement_id,
        component=component,
        path=path or None,
        hint=hint,
        severity=severity,
    ))


def resolve_invalid(required: bool, has_default: bool, default: Any) -> Any:
    """Invalid value: its default if any; else INVALID when required, OMIT when optional."""
    if has_default:
        return default
    return INVALID if required else OMIT


def schema_default(prop: Any) -> tuple[bool, Any]:
    if isinstance(prop, dict) and "default" in prop:
        return True, prop["default"]
    return False, None


def _mismatch(ctx: IssueCtx, component: str, path: str, expected: str, actual: str) -> None:
    push_issue(ctx, component, path, "type-mismatch",
               f'field "{path}" expects {expected} but got {actual}')


def _validate_element_position(el: Element, s: dict, component: str, path: str, ctx: IssueCtx) -> bool:
    if _is_composite(s):
        return False
    if isinstance(s.get("type"), str) or isinstance(s.get("enum"), list) or "const" in s:
        _mismatch(ctx, component, path,
                  s["type"] if isinstance(s.get("type"), str) else "a literal value",
                  f'component "{el.type_name}"')
        return True
    return False


def _slot_ref_names(s: dict) -> list[str | None]:
    options = s.get("anyOf") or s.get("oneOf") or [s]
    return [_ref_name(o) if isinstance(o, dict) else None for o in options]


def _is_only_component_slot(s: dict, ctx: IssueCtx) -> bool:
    names = _slot_ref_names(s)
    return bool(names) and all(n is not None and n in ctx.components for n in names)


def _object_view(value: Any) -> dict | None:
    """A reference object (plan, binding) seen as the plain object the reference validates."""
    if isinstance(value, ActionPlan):
        return {"steps": value.steps}
    if isinstance(value, Binding):
        return {"__reactive": "assign", "target": value.target, "expr": value.expr}
    return None


def _validate_object(value: Any, s: dict, component: str, path: str, ctx: IssueCtx) -> Any:
    view = _object_view(value)
    if view is not None:
        checked = _validate_object(view, s, component, path, ctx)
        return value if checked is view else checked
    if not isinstance(value, dict):
        _mismatch(ctx, component, path, "object", _js_type(value))
        return INVALID
    props = s.get("properties") if isinstance(s.get("properties"), dict) else {}
    required = s.get("required") if isinstance(s.get("required"), list) else []
    out: dict | None = None
    invalid = False
    if not ctx.partial:
        for key in required:
            present = key in value
            if not present or value[key] is None:
                has_def, default = schema_default(props.get(key))
                if has_def:
                    if out is None:
                        out = dict(value)
                    out[key] = default
                    continue
                code = "null-required" if present else "missing-required"
                msg = (f'required field "{path}/{key}" cannot be null' if present
                       else f'missing required field "{path}/{key}"')
                push_issue(ctx, component, f"{path}/{key}", code, msg)
                invalid = True
    for key, sub in props.items():
        if key not in value:
            continue
        nxt = validate_value(value[key], sub, component, f"{path}/{key}", ctx)
        if nxt is INVALID:
            has_def, default = schema_default(sub)
            nxt = resolve_invalid(key in required, has_def, default)
            if nxt is INVALID:
                invalid = True
                continue
        if nxt is value[key]:
            continue
        if out is None:
            out = dict(value)
        if nxt is OMIT:
            out.pop(key, None)
        else:
            out[key] = nxt
    if invalid:
        return INVALID
    return out if out is not None else value


def _validate_array(value: Any, s: dict, component: str, path: str, ctx: IssueCtx) -> Any:
    if not isinstance(value, list):
        _mismatch(ctx, component, path, "array", _js_type(value))
        return INVALID
    items = s.get("items")
    if not isinstance(items, dict):
        return value
    out: list | None = None
    for i, item in enumerate(value):
        nxt = validate_value(item, items, component, f"{path}/{i}", ctx)
        if nxt is not item and out is None:
            out = value[:i]
        if out is not None and nxt is not INVALID:
            out.append(None if nxt is OMIT else nxt)
    return out if out is not None else value


def _validate_leaf(value: Any, s: dict, component: str, path: str, ctx: IssueCtx) -> bool:
    expected, enum = _scalar_info(s)
    if expected is None and enum is None:
        return False
    if enum is not None and ctx.partial:
        return False  # a partial literal may still complete toward a member
    actual = typeof(value)
    if enum is not None:
        if actual not in _SCALAR_TYPEOFS:
            return False
        if any(strict_equal(value, e) for e in enum):
            return False
        _mismatch(ctx, component, path,
                  "one of [" + ", ".join(_dumps(e) for e in enum) + "]", _dumps(value))
        return True
    if expected != actual:
        _mismatch(ctx, component, path, expected or "", _js_type(value))
        return True
    return False


def validate_value(value: Any, schema: Any, component: str, path: str, ctx: IssueCtx) -> Any:
    """Check a materialized value against a JSON Schema fragment.

    Reports every violation, then applies the edge rule at each level: a schema
    default substitutes, a required edge makes the parent invalid, an optional
    edge or an array item is pruned. Returns the value itself when nothing
    changes, a cleaned copy, or INVALID. Never mutates.
    """
    if not isinstance(schema, dict):
        return value
    if value is None or is_ast_like(value):
        return value  # dynamic: resolved at runtime (AST-shaped data counts, as in the reference)
    if is_element_like(value):
        el = as_element(value)
        return INVALID if _validate_element_position(el, schema, component, path, ctx) else value
    if _is_composite(schema):
        if not _is_only_component_slot(schema, ctx):
            return value
        actual = ("array" if isinstance(value, list)
                  else "plain object" if isinstance(value, (dict, ActionPlan)) else typeof(value))
        _mismatch(ctx, component, path,
                  " | ".join(str(n) for n in _slot_ref_names(schema)), actual)
        return INVALID
    t = schema.get("type")
    if t == "object":
        return _validate_object(value, schema, component, path, ctx)
    if t == "array":
        return _validate_array(value, schema, component, path, ctx)
    return INVALID if _validate_leaf(value, schema, component, path, ctx) else value
