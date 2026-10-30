"""AST node types for OpenUI Lang expressions (language.md, section 1.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterator, Union


class Node:
    """Base class of every AST node."""

    __slots__ = ()


@dataclass
class Comp(Node):
    """A call: a component call ``Card(...)``, or an ``@Name(...)`` call."""

    name: str
    args: list["AST"]
    mapped_props: dict[str, "AST"] | None = None
    #: Set on an ``@Name(...)`` call whose name is not a built-in or action.
    fn: bool = False


@dataclass
class Str(Node):
    v: str


@dataclass
class Num(Node):
    v: float | int


@dataclass
class Bool(Node):
    v: bool


@dataclass
class Null(Node):
    pass


@dataclass
class Arr(Node):
    els: list["AST"]


@dataclass
class Obj(Node):
    entries: list[tuple[str, "AST"]]


@dataclass
class Ref(Node):
    """A reference to a statement."""

    n: str


@dataclass
class Ph(Node):
    """A placeholder left where a reference could not be resolved."""

    n: str


@dataclass
class StateRef(Node):
    """A ``$name`` state variable."""

    n: str


@dataclass
class RuntimeRef(Node):
    """A reference to a query or mutation statement, resolved at runtime."""

    n: str
    ref_type: str  # "query" | "mutation"


@dataclass
class BinOp(Node):
    op: str
    left: "AST"
    right: "AST"


@dataclass
class UnaryOp(Node):
    op: str
    operand: "AST"


@dataclass
class Ternary(Node):
    cond: "AST"
    then: "AST"
    else_: "AST"


@dataclass
class Member(Node):
    obj: "AST"
    field: str


@dataclass
class Index(Node):
    obj: "AST"
    index: "AST"


@dataclass
class Assign(Node):
    """``$name = expr`` inside an expression (runtime two-way binding)."""

    target: str
    value: "AST"


AST = Union[
    Comp, Str, Num, Bool, Null, Arr, Obj, Ref, Ph, StateRef, RuntimeRef,
    BinOp, UnaryOp, Ternary, Member, Index, Assign,
]

RUNTIME_EXPR = (StateRef, RuntimeRef, BinOp, UnaryOp, Ternary, Member, Index, Assign)


def is_ast(value: Any) -> bool:
    return isinstance(value, Node)


def is_runtime_expr(node: Any) -> bool:
    return isinstance(node, RUNTIME_EXPR)


def children(node: Node) -> Iterator[Node]:
    if isinstance(node, Comp):
        yield from node.args
        if node.mapped_props:
            yield from node.mapped_props.values()
    elif isinstance(node, Arr):
        yield from node.els
    elif isinstance(node, Obj):
        for _, v in node.entries:
            yield v
    elif isinstance(node, BinOp):
        yield node.left
        yield node.right
    elif isinstance(node, UnaryOp):
        yield node.operand
    elif isinstance(node, Ternary):
        yield node.cond
        yield node.then
        yield node.else_
    elif isinstance(node, Member):
        yield node.obj
    elif isinstance(node, Index):
        yield node.obj
        yield node.index
    elif isinstance(node, Assign):
        yield node.value


def walk(node: Node, visit: Callable[[Node], None]) -> None:
    """Visit ``node`` and every descendant, depth first (pre-order)."""
    stack = [node]
    while stack:
        cur = stack.pop()
        visit(cur)
        stack.extend(reversed(list(children(cur))))


def to_literal_ast(value: Any) -> Node:
    """``{"n": [1]}`` -> ``Obj([("n", Arr([Num(1)]))])``."""
    if value is None:
        return Null()
    if isinstance(value, bool):
        return Bool(value)
    if isinstance(value, (int, float)):
        return Num(value)
    if isinstance(value, str):
        return Str(value)
    if isinstance(value, list):
        return Arr([to_literal_ast(v) for v in value])
    if isinstance(value, dict):
        return Obj([(str(k), to_literal_ast(v)) for k, v in value.items()])
    return Null()


_NO_LITERAL = object()


def literal_value(node: Node) -> Any:
    """The plain value of a literal-only AST, or ``NO_LITERAL`` for refs, calls, operators."""
    if isinstance(node, (Str, Num, Bool)):
        return node.v
    if isinstance(node, Null):
        return None
    if isinstance(node, Arr):
        out = []
        for e in node.els:
            v = literal_value(e)
            if v is _NO_LITERAL:
                return _NO_LITERAL
            out.append(v)
        return out
    if isinstance(node, Obj):
        obj: dict[str, Any] = {}
        for k, e in node.entries:
            v = literal_value(e)
            if v is _NO_LITERAL:
                return _NO_LITERAL
            obj[k] = v
        return obj
    return _NO_LITERAL


NO_LITERAL = _NO_LITERAL

__all__ = [
    "AST", "Node", "Comp", "Str", "Num", "Bool", "Null", "Arr", "Obj", "Ref", "Ph",
    "StateRef", "RuntimeRef", "BinOp", "UnaryOp", "Ternary", "Member", "Index", "Assign",
    "is_ast", "is_runtime_expr", "walk", "children", "to_literal_ast", "literal_value",
    "NO_LITERAL",
]
