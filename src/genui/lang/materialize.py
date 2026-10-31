"""Schema-aware materialization: resolve references, map positional arguments to
named props, validate, and keep runtime expressions as AST (language.md,
sections 2.3, 3.6, 8.4)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, NamedTuple

from .ast import (
    AST, Arr, Assign, BinOp, Bool, Comp, Index, Member, Node, Null, Num, Obj, Ph, Ref,
    RuntimeRef, Str, Ternary, UnaryOp, is_runtime_expr, literal_value, NO_LITERAL,
    to_literal_ast, walk,
)
from .builtins import CallDef, ParamDef, is_reserved_call
from .library import CompiledLibrary
from .validation import (
    INVALID, OMIT, IssueCtx, params_signature, push_issue, resolve_invalid, signature_hint,
    validate_value,
)
from .tsjson import contains_dynamic, is_element_like
from .values import Element

#: Most AST nodes one parse may materialize. References are inlined, so a program can
#: double its size with every line (``a1 = [a0, a0]``, ``a2 = [a1, a1]``, ...); this cap
#: stops a few hundred bytes from taking minutes and gigabytes. Real UIs use a few thousand.
MAX_NODES = 200_000


class ProgramTooLarge(Exception):
    """The program expands past :data:`MAX_NODES` nodes."""

    def __init__(self) -> None:
        super().__init__(
            f"program expands to more than {MAX_NODES:,} values (references are inlined); "
            "reuse fewer references or send less data"
        )


@dataclass
class MaterializeCtx(IssueCtx):
    syms: dict[str, AST] = field(default_factory=dict)
    lib: CompiledLibrary | None = None
    unres: list[str] = field(default_factory=list)
    visited: set[str] = field(default_factory=set)
    #: value statement ids not yet reached; what remains are orphans
    unreached: dict[str, None] | None = None
    #: nodes left before :class:`ProgramTooLarge`
    budget: int = MAX_NODES
    #: Streaming only: materialized values of finished statements, reused across snapshots
    #: (see :class:`RefCache`). ``stable`` maps each finished statement to its AST.
    cache: dict[tuple[str, bool], CachedRef] | None = None
    stable: dict[str, AST] | None = None
    #: (name, target) of every statement resolved so far, in order
    trail: list[tuple[str, AST]] = field(default_factory=list)

    def spend(self) -> None:
        self.budget -= 1
        if self.budget < 0:
            raise ProgramTooLarge


# ─── issue helpers ─────────────────────────────────────────────────────────


def _available_components(ctx: MaterializeCtx) -> str | None:
    if ctx.lib and ctx.lib.components:
        return "Available components: " + ", ".join(ctx.lib.components)
    return None


def _unknown_component(ctx: MaterializeCtx, name: str) -> None:
    hint = _available_components(ctx)
    msg = f'Unknown component "{name}" — not found in catalog or builtins'
    if hint:
        msg += ". " + hint
    push_issue(ctx, name, "", "unknown-component", msg, hint)


def _unknown_function(ctx: MaterializeCtx, name: str) -> None:
    names = sorted(n for n, d in (ctx.lib.call_defs.items() if ctx.lib else []) if d.kind == "function")
    hint = ("Available functions: " + ", ".join("@" + n for n in names)) if names else None
    push_issue(ctx, name, "", "unknown-function",
               f'Unknown function "@{name}": not a built-in or action step. The call evaluates to null', hint)


def _required_issue(ctx: MaterializeCtx, name: str, p: ParamDef, params: list[ParamDef], present: bool) -> None:
    path = f"/{p.name}"
    sig = params_signature(name, params)
    if present:
        msg = f'required field "{path}" cannot be null — signature: {sig}'
    else:
        msg = f'missing required field "{path}" — signature: {sig}'
    push_issue(ctx, name, path, "null-required" if present else "missing-required", msg,
               signature_hint(name, params))


def _excess_issue(ctx: MaterializeCtx, name: str, params: list[ParamDef], got: int) -> None:
    declared = len(params)
    push_issue(ctx, name, "", "excess-args",
               f"{name} takes {declared} arg(s), got {got} ({got - declared} excess dropped)",
               signature_hint(name, params))


# ─── references ────────────────────────────────────────────────────────────


class CachedRef(NamedTuple):
    """A statement's materialized value and everything resolving it did to the context."""

    value: Any
    deps: tuple[tuple[str, AST], ...]  # statements it resolved (itself first), with their ASTs
    errors: tuple[Any, ...]
    spent: int


def _cache_hit(name: str, target: AST, ctx: MaterializeCtx) -> CachedRef | None:
    hit = ctx.cache.get((name, ctx.partial)) if ctx.cache is not None else None
    if hit is None:
        return None
    syms = ctx.syms
    for dep, ast in hit.deps:
        if syms.get(dep) is not ast or dep in ctx.visited:
            return None
    return hit


def _replay(name: str, hit: CachedRef, ctx: MaterializeCtx) -> Any:
    ctx.budget -= hit.spent
    if ctx.budget < 0:
        raise ProgramTooLarge
    ctx.errors.extend(replace(e) for e in hit.errors)
    ctx.trail.extend(hit.deps)
    if ctx.unreached is not None:
        for dep, _ in hit.deps:
            ctx.unreached.pop(dep, None)
    value = hit.value
    if isinstance(value, Element):
        value.statement_id = name
    elif is_element_like(value):
        value["statementId"] = name
    return value


def _resolve_ref(name: str, ctx: MaterializeCtx, mode: str) -> Any:
    if name in ctx.visited or name not in ctx.syms:
        ctx.unres.append(name)
        return Ph(name) if mode == "expr" else None
    target = ctx.syms[name]
    if ctx.unreached is not None:
        ctx.unreached.pop(name, None)
    if isinstance(target, Comp) and is_reserved_call(target.name):
        return RuntimeRef(name, "mutation" if target.name == "Mutation" else "query")
    if mode == "value" and ctx.cache is not None:
        hit = _cache_hit(name, target, ctx)
        if hit is not None:
            return _replay(name, hit, ctx)
    ctx.visited.add(name)
    prev = ctx.current_statement_id
    ctx.current_statement_id = name
    marks = (len(ctx.errors), len(ctx.unres), len(ctx.trail), ctx.budget)
    ctx.trail.append((name, target))
    try:
        if mode == "value":
            result = materialize_value(target, ctx)
            if isinstance(result, Element):
                result.statement_id = name
            elif is_element_like(result):
                result["statementId"] = name  # element-shaped data, as the reference tags it
            if ctx.cache is not None:
                _remember(name, result, marks, ctx)
            return result
        return materialize_expr(target, ctx)
    finally:
        ctx.current_statement_id = prev
        ctx.visited.discard(name)


def _remember(name: str, result: Any, marks: tuple[int, int, int, int], ctx: MaterializeCtx) -> None:
    """Cache a value that depends only on finished statements and resolved every reference."""
    errors_at, unres_at, trail_at, budget_at = marks
    if len(ctx.unres) != unres_at or ctx.stable is None:
        return  # a reference is missing (it may arrive later) or a cycle was cut
    deps = tuple(ctx.trail[trail_at:])
    stable = ctx.stable
    if all(stable.get(dep) is ast for dep, ast in deps):
        ctx.cache[(name, ctx.partial)] = CachedRef(  # type: ignore[index]
            result, deps, tuple(ctx.errors[errors_at:]), budget_at - ctx.budget)


# ─── calls ─────────────────────────────────────────────────────────────────


def _call_defs(ctx: MaterializeCtx) -> dict[str, CallDef]:
    from .builtins import BUILTIN_CALLS

    return ctx.lib.call_defs if ctx.lib else BUILTIN_CALLS


def _is_runtime_call(name: str, ctx: MaterializeCtx) -> bool:
    return name in _call_defs(ctx) or is_reserved_call(name)


def name_args(args: list[AST], params: list[ParamDef]) -> dict[str, AST]:
    """``[Num 1, Ref x]`` with params ``[a, b]`` -> ``{a: Num 1, b: Ref x}``; extras dropped."""
    return {params[i].name: args[i] for i in range(min(len(params), len(args)))}


def map_call_args(name: str, args: list[AST], d: CallDef, ctx: MaterializeCtx) -> dict[str, AST] | None:
    """Check literal arguments of a library function or action when parsing.

    Returns the named args, or None when the call is invalid (it evaluates to
    null; an invalid action becomes a no-op).
    """
    params = d.params
    if len(args) > len(params):
        _excess_issue(ctx, name, params, len(args))
    mapped = name_args(args, params)
    invalid = False
    errors_before = len(ctx.errors)
    for p in params:
        arg = mapped.get(p.name)
        lit = literal_value(arg) if arg is not None else None
        if lit is NO_LITERAL:
            continue
        if lit is None:
            if not p.required or p.has_default:
                continue
            _required_issue(ctx, name, p, params, present=arg is not None)
            invalid = True
            continue
        nxt = validate_value(lit, p.schema, name, f"/{p.name}", ctx)
        if nxt is INVALID:
            nxt = resolve_invalid(p.required, p.has_default, p.default)
        if nxt is INVALID:
            invalid = True
        elif nxt is OMIT:
            mapped.pop(p.name, None)
        elif nxt is not lit:
            mapped[p.name] = to_literal_ast(nxt)
    # An action never runs with a value the model did not write.
    if d.kind == "action" and len(ctx.errors) > errors_before:
        invalid = True
    return None if invalid else mapped


def _materialize_call(node: Comp, ctx: MaterializeCtx, arg_fn) -> AST:
    args = [arg_fn(a) for a in node.args]
    d = _call_defs(ctx).get(node.name)
    if d is None or d.lazy:
        return replace(node, args=args)
    mapped = name_args(args, d.params) if d.builtin else map_call_args(node.name, args, d, ctx)
    if mapped is not None:
        return replace(node, args=args, mapped_props=mapped)
    if d.kind == "action":
        return Comp("Action", [Arr([])])  # an invalid action is an empty plan
    return Null()


def name_raw_call_args(args: list[AST], ctx: MaterializeCtx, statement_id: str) -> None:
    """Name (and check) the args of calls inside a Query/Mutation, in place."""
    prev = ctx.current_statement_id
    ctx.current_statement_id = statement_id
    seen: set[int] = set()
    defs = _call_defs(ctx)

    def visit(n: Node) -> None:
        if not isinstance(n, Comp) or id(n) in seen:
            return
        seen.add(id(n))
        d = defs.get(n.name)
        if d is None or d.lazy:
            return
        checked = None if d.builtin else map_call_args(n.name, n.args, d, ctx)
        n.mapped_props = checked if checked is not None else name_args(n.args, d.params)

    for arg in args:
        walk(arg, visit)
    ctx.current_statement_id = prev


def _materialize_lazy_builtin(node: Comp, ctx: MaterializeCtx, scoped: frozenset[str]) -> AST | None:
    d = _call_defs(ctx).get(node.name)
    if d is None or d.kind != "function" or not d.lazy or len(node.args) < 3:
        return None
    var = node.args[1]
    var_name = var.n if isinstance(var, Ref) else var.v if isinstance(var, Str) else None
    if not var_name:
        return None
    inner = scoped | {var_name}
    args = [a if i == 1 else _expr(a, ctx, inner) for i, a in enumerate(node.args)]
    return replace(node, args=args)


# ─── expressions ───────────────────────────────────────────────────────────


def _expr(node: AST, ctx: MaterializeCtx, scoped: frozenset[str]) -> AST:
    ctx.spend()
    if isinstance(node, Ref):
        return node if node.n in scoped else _resolve_ref(node.n, ctx, "expr")
    if isinstance(node, Ph):
        return node
    if isinstance(node, Comp):
        if node.fn and not _is_runtime_call(node.name, ctx):
            _unknown_function(ctx, node.name)
            return Null()
        lazy = _materialize_lazy_builtin(node, ctx, scoped)
        if lazy is not None:
            return lazy
        if _is_runtime_call(node.name, ctx):
            return _materialize_call(node, ctx, lambda a: _expr(a, ctx, scoped))
        args = [_expr(a, ctx, scoped) for a in node.args]
        params = ctx.lib.components.get(node.name) if ctx.lib else None
        if params is not None:
            return replace(node, args=args, mapped_props=name_args(args, params))
        _unknown_component(ctx, node.name)
        return replace(node, args=args)
    if isinstance(node, Arr):
        return Arr([_expr(e, ctx, scoped) for e in node.els])
    if isinstance(node, Obj):
        return Obj([(k, _expr(v, ctx, scoped)) for k, v in node.entries])
    if isinstance(node, BinOp):
        return BinOp(node.op, _expr(node.left, ctx, scoped), _expr(node.right, ctx, scoped))
    if isinstance(node, UnaryOp):
        return UnaryOp(node.op, _expr(node.operand, ctx, scoped))
    if isinstance(node, Ternary):
        return Ternary(_expr(node.cond, ctx, scoped), _expr(node.then, ctx, scoped),
                       _expr(node.else_, ctx, scoped))
    if isinstance(node, Member):
        return Member(_expr(node.obj, ctx, scoped), node.field)
    if isinstance(node, Index):
        return Index(_expr(node.obj, ctx, scoped), _expr(node.index, ctx, scoped))
    if isinstance(node, Assign):
        return Assign(node.target, _expr(node.value, ctx, scoped))
    return node  # literals, StateRef, RuntimeRef


def materialize_expr(node: AST, ctx: MaterializeCtx) -> AST:
    """Normalize an AST for runtime evaluation: resolve refs, name component args."""
    return _expr(node, ctx, frozenset())


# ─── values ────────────────────────────────────────────────────────────────


def materialize_value(node: AST, ctx: MaterializeCtx) -> Any:
    """Lower an AST in a value position.

    Returns an :class:`Element` for library components, an AST for runtime
    expressions and calls, plain values for literals, and None for dropped or
    unresolved values.
    """
    ctx.spend()
    if isinstance(node, Ref):
        return _resolve_ref(node.n, ctx, "value")
    if isinstance(node, (Str, Num, Bool)):
        return node.v
    if isinstance(node, (Null, Ph)):
        return None
    if isinstance(node, Arr):
        items: list[Any] = []
        for e in node.els:
            if isinstance(e, Ph):
                continue
            value = materialize_value(e, ctx)
            # unresolved refs and dropped components are left out; explicit null is kept
            if value is None and isinstance(e, (Comp, Ref)):
                continue
            items.append(value)
        return items
    if isinstance(node, Obj):
        return {k: materialize_value(v, ctx) for k, v in node.entries}
    if isinstance(node, Comp):
        return _materialize_component(node, ctx)
    if is_runtime_expr(node):
        return materialize_expr(node, ctx)
    return node


def _materialize_component(node: Comp, ctx: MaterializeCtx) -> Any:
    name, args = node.name, node.args
    if node.fn and not _is_runtime_call(name, ctx):
        _unknown_function(ctx, name)
        return None
    if is_reserved_call(name):
        push_issue(ctx, name, "", "inline-reserved",
                   f"{name}() must be declared as a top-level statement, not used inline as a value",
                   f"Declare it as a top-level statement: myVar = {name}(...)")
        return None
    if _is_runtime_call(name, ctx):
        lazy = _materialize_lazy_builtin(node, ctx, frozenset())
        if lazy is not None:
            return lazy
        return _materialize_call(node, ctx, lambda a: materialize_expr(a, ctx))

    params = ctx.lib.components.get(name) if ctx.lib else None
    if params is None:
        _unknown_component(ctx, name)
        return None

    props: dict[str, Any] = {}
    drop = False
    for i in range(min(len(params), len(args))):
        p = params[i]
        value = materialize_value(args[i], ctx)
        props[p.name] = value
        if p.schema is None:
            continue
        nxt = validate_value(value, p.schema, name, f"/{p.name}", ctx)
        if nxt is INVALID:
            nxt = resolve_invalid(p.required, p.has_default, p.default)
            if nxt is INVALID:
                drop = True
            elif nxt is OMIT:
                del props[p.name]
        if nxt is not INVALID and nxt is not OMIT:
            props[p.name] = nxt

    if len(args) > len(params):
        _excess_issue(ctx, name, params, len(args))

    missing = [p for p in params if p.required and props.get(p.name) is None]
    still_invalid = []
    for p in missing:
        if p.has_default:
            props[p.name] = p.default
        else:
            still_invalid.append(p)
    if still_invalid:
        for p in still_invalid:
            _required_issue(ctx, name, p, params, present=p.name in props)
        return None
    if drop:
        return None
    return Element(name, props, partial=ctx.partial, has_dynamic_props=contains_dynamic(props))
