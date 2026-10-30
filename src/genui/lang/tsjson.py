"""The reference implementation's object shapes, for values that are not plain data.

The TypeScript reference keeps AST nodes, element nodes, action plans, and
bindings as plain JavaScript objects. Where such an object leaks into data (a
state default that is an expression, a prop that failed to evaluate) the
renderer sees that object, so genui reproduces its JSON shape here.
"""

from __future__ import annotations

import math
from typing import Any

from .ast import (
    Arr, Assign, BinOp, Bool, Comp, Index, Member, Node, Null, Num, Obj, Ph, Ref, RuntimeRef,
    StateRef, Str, Ternary, UnaryOp,
)
from .values import ActionPlan, Binding, Element


def ast_json(node: Node) -> dict[str, Any]:
    """An AST node as the reference's ``{k: ...}`` object."""
    if isinstance(node, Comp):
        out: dict[str, Any] = {"k": "Comp", "name": node.name, "args": [ast_json(a) for a in node.args]}
        if node.mapped_props is not None:
            out["mappedProps"] = {k: ast_json(v) for k, v in node.mapped_props.items()}
        if node.fn:
            out["fn"] = True
        return out
    if isinstance(node, (Str, Num, Bool)):
        return {"k": type(node).__name__, "v": node.v}
    if isinstance(node, Null):
        return {"k": "Null"}
    if isinstance(node, Arr):
        return {"k": "Arr", "els": [ast_json(e) for e in node.els]}
    if isinstance(node, Obj):
        return {"k": "Obj", "entries": [[k, ast_json(v)] for k, v in node.entries]}
    if isinstance(node, (Ref, Ph, StateRef)):
        return {"k": type(node).__name__, "n": node.n}
    if isinstance(node, RuntimeRef):
        return {"k": "RuntimeRef", "n": node.n, "refType": node.ref_type}
    if isinstance(node, BinOp):
        return {"k": "BinOp", "op": node.op, "left": ast_json(node.left), "right": ast_json(node.right)}
    if isinstance(node, UnaryOp):
        return {"k": "UnaryOp", "op": node.op, "operand": ast_json(node.operand)}
    if isinstance(node, Ternary):
        return {"k": "Ternary", "cond": ast_json(node.cond), "then": ast_json(node.then),
                "else": ast_json(node.else_)}
    if isinstance(node, Member):
        return {"k": "Member", "obj": ast_json(node.obj), "field": node.field}
    if isinstance(node, Index):
        return {"k": "Index", "obj": ast_json(node.obj), "index": ast_json(node.index)}
    if isinstance(node, Assign):
        return {"k": "Assign", "target": node.target, "value": ast_json(node.value)}
    return {"k": "Null"}


def contains_dynamic(v: Any) -> bool:
    """materialize.ts containsDynamicValue."""
    if isinstance(v, Node) or (isinstance(v, dict) and _kind(v)):
        return True
    if isinstance(v, list):
        return any(contains_dynamic(x) for x in v)
    if isinstance(v, Element):
        return any(contains_dynamic(x) for x in v.props.values())
    if isinstance(v, dict):
        if isinstance(v.get("steps"), list):
            return True
        return any(contains_dynamic(x) for x in v.values())
    return False


def _dynamic(el: Element) -> bool:
    return el.has_dynamic_props if el.has_dynamic_props is not None else contains_dynamic(el.props)


def element_json(el: Element, finite: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "element",
        "typeName": el.type_name,
        "props": ts_json(el.props, finite=finite),
        "partial": el.partial,
        "hasDynamicProps": _dynamic(el),
    }
    if el.statement_id is not None:
        out["statementId"] = el.statement_id
    return out


def ts_json(value: Any, keep_elements: bool = False, finite: bool = True) -> Any:
    """Convert a value to the reference's JSON shape (``JSON.stringify`` semantics:
    non-finite numbers become null). With ``keep_elements``, elements are left as
    :class:`Element` instances (the renderer still renders them) and only AST
    nodes are converted."""
    if finite and isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Node):
        return ast_json(value)
    if isinstance(value, Element):
        return value if keep_elements else element_json(value, finite)
    if isinstance(value, ActionPlan):
        return {"steps": [ts_json(s, keep_elements, finite) for s in value.steps]}
    if isinstance(value, Binding):
        out: dict[str, Any] = {"__reactive": "assign", "target": value.target}
        if value.expr is not None:
            out["expr"] = ast_json(value.expr)
        return out
    if isinstance(value, list):
        return [ts_json(v, keep_elements, finite) for v in value]
    if isinstance(value, dict):
        return {str(k): ts_json(v, keep_elements, finite) for k, v in value.items()}
    return None


def object_property(obj: Any, key: str) -> Any:
    """``obj[key]`` on a reference object (element, plan, binding); None if absent."""
    if isinstance(obj, Element):
        fields = {"type": "element", "typeName": obj.type_name, "props": obj.props,
                  "partial": obj.partial, "hasDynamicProps": _dynamic(obj)}
        if obj.statement_id is not None:
            fields["statementId"] = obj.statement_id
        return fields.get(key)
    if isinstance(obj, ActionPlan):
        return obj.steps if key == "steps" else None
    if isinstance(obj, Binding):
        return {"__reactive": "assign", "target": obj.target, "expr": obj.expr}.get(key)
    return None


# ─── Duck typing, as the reference does it ─────────────────────────────────
#
# The reference recognizes runtime objects by shape, so data with the same
# shape behaves the same way. These mirror ``isElementNode``, ``isActionPlan``,
# ``isReactiveAssign``, and ``isASTNode``.

AST_KINDS = frozenset({
    "Comp", "Ref", "StateRef", "RuntimeRef", "BinOp", "UnaryOp", "Ternary", "Member", "Index",
    "Assign", "Str", "Num", "Bool", "Null", "Arr", "Obj", "Ph",
})


def _kind(v: dict) -> bool:
    k = v.get("k")
    return isinstance(k, str) and k in AST_KINDS


def is_element_like(v: Any) -> bool:
    if isinstance(v, Element):
        return True
    return (isinstance(v, dict) and v.get("type") == "element" and isinstance(v.get("typeName"), str)
            and isinstance(v.get("props"), (dict, list)) and isinstance(v.get("partial"), bool))


def as_element(v: Any) -> Element:
    """An element-shaped value as an :class:`Element` (``is_element_like`` must hold)."""
    if isinstance(v, Element):
        return v
    props = v["props"]
    if isinstance(props, list):
        props = {str(i): p for i, p in enumerate(props)}
    dyn = v.get("hasDynamicProps")
    return Element(v["typeName"], dict(props), v.get("statementId"), v["partial"],
                   dyn if isinstance(dyn, bool) else None)


def is_plan_like(v: Any) -> bool:
    return isinstance(v, ActionPlan) or (isinstance(v, dict) and isinstance(v.get("steps"), list))


def as_plan(v: Any) -> ActionPlan:
    return v if isinstance(v, ActionPlan) else ActionPlan(list(v["steps"]))


def is_binding_like(v: Any) -> bool:
    return isinstance(v, Binding) or (isinstance(v, dict) and v.get("__reactive") == "assign")


def binding_target(v: Any) -> Any:
    return v.target if isinstance(v, Binding) else v.get("target")


def is_ast_like(v: Any) -> bool:
    return isinstance(v, Node) or (isinstance(v, dict) and _kind(v))


def as_ast(v: Any) -> Node:
    """An AST-shaped value as an AST node. Raises on a malformed shape, as the
    reference's evaluator throws on one."""
    if isinstance(v, Node):
        return v
    if not isinstance(v, dict):
        raise TypeError("not an AST node")
    k = v.get("k")
    a = as_ast
    if k == "Comp":
        mapped = v.get("mappedProps")
        return Comp(v["name"], [a(x) for x in v["args"]],
                    {kk: a(x) for kk, x in mapped.items()} if isinstance(mapped, dict) else None,
                    bool(v.get("fn")))
    if k == "Str":
        return Str(v.get("v"))
    if k == "Num":
        return Num(v.get("v"))
    if k == "Bool":
        return Bool(v.get("v"))
    if k == "Null":
        return Null()
    if k == "Arr":
        return Arr([a(x) for x in v["els"]])
    if k == "Obj":
        return Obj([(str(e[0]), a(e[1])) for e in v["entries"]])
    if k in ("Ref", "Ph", "StateRef"):
        return {"Ref": Ref, "Ph": Ph, "StateRef": StateRef}[k](v.get("n"))
    if k == "RuntimeRef":
        return RuntimeRef(v.get("n"), v.get("refType"))
    if k == "BinOp":
        return BinOp(v.get("op"), a(v["left"]), a(v["right"]))
    if k == "UnaryOp":
        return UnaryOp(v.get("op"), a(v["operand"]))
    if k == "Ternary":
        return Ternary(a(v["cond"]), a(v["then"]), a(v["else"]))
    if k == "Member":
        return Member(a(v["obj"]), v.get("field"))
    if k == "Index":
        return Index(a(v["obj"]), a(v["index"]))
    if k == "Assign":
        return Assign(v.get("target"), a(v["value"]))
    raise TypeError(f"unknown AST kind {k!r}")
