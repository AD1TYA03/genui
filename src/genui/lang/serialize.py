"""Serialize a rendered tree back to OpenUI Lang (language.md, section 9.2)."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Mapping

from ._js import is_number, number_to_string
from .ast import (
    AST, Arr, Assign, BinOp, Bool, Comp, Index, Member, Null, Num, Obj, Ph, Ref, RuntimeRef,
    StateRef, Str, Ternary, UnaryOp,
)
from .builtins import BUILTIN_CALLS
from .library import CompiledLibrary, compile_library
from .values import ActionPlan, Binding, Element

_PREC = {
    "||": 2, "&&": 3, "==": 4, "!=": 4, ">": 5, "<": 5, ">=": 5, "<=": 5,
    "+": 6, "-": 6, "*": 7, "/": 7, "%": 7,
}
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _num(x: float | int) -> str:
    if isinstance(x, float) and not math.isfinite(x):
        return "null"
    return number_to_string(x)


def _key(k: str) -> str:
    return k if _NAME_RE.match(k) and k not in ("true", "false", "null") else _str(k)


def _prec(node: AST) -> int:
    if isinstance(node, Ternary) or isinstance(node, Assign):
        return 1
    if isinstance(node, BinOp):
        return _PREC.get(node.op, 0)
    if isinstance(node, UnaryOp):
        return 8
    return 10


def serialize_ast(node: AST, lib: CompiledLibrary | None = None) -> str:
    """Serialize an expression, adding parentheses where parsing back would regroup."""
    calls = lib.call_defs if lib else BUILTIN_CALLS
    s = lambda n: serialize_ast(n, lib)  # noqa: E731

    if isinstance(node, Str):
        return _str(node.v)
    if isinstance(node, Num):
        return _num(node.v)
    if isinstance(node, Bool):
        return "true" if node.v else "false"
    if isinstance(node, Null):
        return "null"
    if isinstance(node, (Ph, StateRef, RuntimeRef, Ref)):
        return node.n
    if isinstance(node, Arr):
        return "[" + ", ".join(s(e) for e in node.els) + "]"
    if isinstance(node, Obj):
        return "{" + ", ".join(f"{_key(k)}: {s(v)}" for k, v in node.entries) + "}"
    if isinstance(node, BinOp):
        p = _PREC.get(node.op, 0)
        left = s(node.left)
        if _prec(node.left) < p:
            left = f"({left})"
        right = s(node.right)
        if _prec(node.right) <= p:
            right = f"({right})"
        return f"{left} {node.op} {right}"
    if isinstance(node, UnaryOp):
        inner = s(node.operand)
        if _prec(node.operand) < 8:
            inner = f"({inner})"
        return f"{node.op}{inner}"
    if isinstance(node, Ternary):
        cond = s(node.cond)
        if _prec(node.cond) <= 1:
            cond = f"({cond})"
        return f"{cond} ? {s(node.then)} : {s(node.else_)}"
    if isinstance(node, Member):
        obj = s(node.obj)
        if _prec(node.obj) < 10:
            obj = f"({obj})"
        return f"{obj}.{node.field}"
    if isinstance(node, Index):
        obj = s(node.obj)
        if _prec(node.obj) < 10:
            obj = f"({obj})"
        return f"{obj}[{s(node.index)}]"
    if isinstance(node, Assign):
        return f"{node.target} = {s(node.value)}"
    if isinstance(node, Comp):
        args = ", ".join(s(a) for a in node.args)
        if node.name in calls and node.name != "Action":
            return f"@{node.name}({args})"
        return f"{node.name}({args})"
    return "null"


class _Serializer:
    def __init__(self, lib: CompiledLibrary) -> None:
        self.lib = lib
        self.statements: list[tuple[str, str]] = []
        self.registered: set[str] = set()

    def value(self, v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if is_number(v):
            return _num(v)
        if isinstance(v, str):
            return _str(v)
        if isinstance(v, Element):
            if v.statement_id:
                if v.statement_id not in self.registered:
                    self.registered.add(v.statement_id)
                    expr = self.element(v)
                    self.statements.append((v.statement_id, f"{v.statement_id} = {expr}"))
                return v.statement_id
            return self.element(v)
        if isinstance(v, ActionPlan):
            steps = [self.step(st) for st in v.steps]
            steps = [st for st in steps if st]
            if len(steps) == 1:
                return steps[0]
            return "Action([" + ", ".join(steps) + "])"
        if isinstance(v, Binding):
            return v.target
        if isinstance(v, (Comp, Str, Num, Bool, Null, Arr, Obj, Ref, Ph, StateRef, RuntimeRef,
                          BinOp, UnaryOp, Ternary, Member, Index, Assign)):
            return serialize_ast(v, self.lib)
        if isinstance(v, list):
            return "[" + ", ".join(self.value(e) for e in v) + "]"
        if isinstance(v, dict):
            return "{" + ", ".join(f"{_key(str(k))}: {self.value(x)}" for k, x in v.items()) + "}"
        return "null"

    def step(self, st: Mapping[str, Any]) -> str:
        t = st.get("type")
        if t == "continue_conversation":
            args = [self.value(st.get("message"))]
            if st.get("context") is not None:
                args.append(self.value(st.get("context")))
            return f"@ToAssistant({', '.join(args)})"
        if t == "open_url":
            return f"@OpenUrl({self.value(st.get('url'))})"
        if t == "set":
            value_ast = st.get("valueAST")
            val = serialize_ast(value_ast, self.lib) if value_ast is not None else "null"
            return f"@Set({st.get('target')}, {val})"
        if t == "reset":
            return f"@Reset({', '.join(st.get('targets') or [])})"
        if t == "run":
            return f"@Run({st.get('statementId')})"
        if t == "custom_action":
            name = st.get("name")
            params = st.get("params") or {}
            schema = (self.lib.action_schemas.get(name) or {}).get("params") or {}
            keys = list((schema.get("properties") or {}).keys()) or list(params)
            args = [self.value(params.get(k)) for k in keys]
            while args and args[-1] == "null":
                args.pop()
            return f"@{name}({', '.join(args)})"
        return ""

    def element(self, el: Element) -> str:
        params = self.lib.components.get(el.type_name)
        if params is None:
            args = [self.value(v) for v in el.props.values()]
            return f"{el.type_name}({', '.join(args)})"
        args = [self.value(el.props.get(p.name)) for p in params]
        while args and args[-1] == "null" and not params[len(args) - 1].required:
            args.pop()
        return f"{el.type_name}({', '.join(args)})"


def serialize(
    tree: Element,
    library: Mapping[str, Any] | CompiledLibrary,
    state: Mapping[str, Any] | None = None,
) -> str:
    """Serialize a rendered tree to source text.

    The entry statement comes first, then every other named component as its own
    statement (children before parents), then non-null state declarations.
    """
    lib = compile_library(library)
    ser = _Serializer(lib)
    root_expr = ser.element(tree)
    root_id = tree.statement_id or "root"
    lines = [f"{root_id} = {root_expr}"]
    lines.extend(text for sid, text in ser.statements if sid != root_id)
    for name, value in (state or {}).items():
        if value is not None:
            lines.append(f"{name} = {ser.value(value)}")
    return "\n".join(lines)
