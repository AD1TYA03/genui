"""Evaluation of AST nodes and element trees (language.md, sections 3, 5.2, 6.3)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable

from . import _js
from .ast import (
    AST, Arr, Assign, BinOp, Bool, Comp, Index, Member, Node, Null, Num, Obj, Ph, Ref,
    RuntimeRef, StateRef, Str, Ternary, UnaryOp, is_ast, to_literal_ast,
)
from .builtins import (
    ACTION_STEP_TYPES, BUILTIN_CALLS, BUILTIN_FUNCTIONS, ParamDef,
)
from .errors import OpenUIError
from .library import CompiledLibrary
from .validation import INVALID, IssueCtx, schema_default, validate_value
from .values import ActionPlan, Binding, CustomStep, Element


@dataclass
class EvalContext:
    """What evaluation reads: the state store, references, and the library."""

    get_state: Callable[[str], Any]
    resolve_ref: Callable[[str], Any]
    lib: CompiledLibrary | None = None
    report_error: Callable[[str], None] | None = None


def _is_step(name: str, lib: CompiledLibrary | None) -> bool:
    d = BUILTIN_CALLS.get(name)
    return d is not None and d.kind == "action"


def evaluate(node: AST, ctx: EvalContext) -> Any:
    """Evaluate an AST node to a runtime value."""
    if isinstance(node, (Str, Num, Bool)):
        return node.v
    if isinstance(node, (Null, Ph)):
        return None
    if isinstance(node, StateRef):
        return ctx.get_state(node.n)
    if isinstance(node, (Ref, RuntimeRef)):
        return ctx.resolve_ref(node.n)
    if isinstance(node, Arr):
        # An unresolved reference as a direct array element is left out (section 2.3).
        return [evaluate(e, ctx) for e in node.els if not isinstance(e, Ph)]
    if isinstance(node, Obj):
        return {k: evaluate(v, ctx) for k, v in node.entries}
    if isinstance(node, Comp):
        return _evaluate_call(node, ctx)
    if isinstance(node, BinOp):
        return _evaluate_binop(node, ctx)
    if isinstance(node, UnaryOp):
        v = evaluate(node.operand, ctx)
        if node.op == "!":
            return not _js.truthy(v)
        if node.op == "-":
            return _js.norm_num(-float(_js.to_number(v)))
        return None
    if isinstance(node, Ternary):
        return evaluate(node.then if _js.truthy(evaluate(node.cond, ctx)) else node.else_, ctx)
    if isinstance(node, Member):
        obj = evaluate(node.obj, ctx)
        if obj is None or isinstance(obj, (Element, ActionPlan, Binding)):
            return None
        if isinstance(obj, list):
            if node.field == "length":
                return len(obj)
            return [None if item is None else _js.get_property(item, node.field) for item in obj]
        return _js.get_property(obj, node.field)
    if isinstance(node, Index):
        obj = evaluate(node.obj, ctx)
        idx = evaluate(node.index, ctx)
        if obj is None or idx is None or isinstance(obj, (Element, ActionPlan, Binding)):
            return None
        if isinstance(obj, list):
            return _js.get_property(obj, _js.number_to_string(_js.to_number(idx)))
        return _js.get_property(obj, _js.to_string(idx))
    if isinstance(node, Assign):
        return Binding(node.target, node.value)
    return None


def _evaluate_binop(node: BinOp, ctx: EvalContext) -> Any:
    op = node.op
    if op == "&&":
        left = evaluate(node.left, ctx)
        return evaluate(node.right, ctx) if _js.truthy(left) else left
    if op == "||":
        left = evaluate(node.left, ctx)
        return left if _js.truthy(left) else evaluate(node.right, ctx)
    left = evaluate(node.left, ctx)
    right = evaluate(node.right, ctx)
    if op == "+":
        return _js.js_add(left, right)
    if op in ("==", "!="):
        eq = _js.loose_equal(left, right)
        return eq if op == "==" else not eq
    a, b = _js.to_number(left), _js.to_number(right)
    if op == "-":
        return _js.norm_num(float(a) - float(b))
    if op == "*":
        return _js.norm_num(float(a) * float(b))
    if op == "/":
        return 0 if b == 0 else _js.norm_num(float(a) / float(b))
    if op == "%":
        return _js.js_mod(a, b)
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    return None


def _name_args(node: Comp, params: list[ParamDef]) -> dict[str, AST]:
    if node.mapped_props is not None:
        return node.mapped_props
    return {params[i].name: node.args[i] for i in range(min(len(params), len(node.args)))}


def _evaluate_args(node: Comp, ctx: EvalContext, params: list[ParamDef] | None = None) -> dict[str, Any]:
    if params is None:
        d = BUILTIN_CALLS.get(node.name)
        params = d.params if d else []
    return {k: evaluate(v, ctx) for k, v in _name_args(node, params).items()}


def _call_args(node: Comp, ctx: EvalContext, params_schema: dict) -> dict[str, Any]:
    """A library call's args; an explicit null for an optional param is omitted."""
    names = list((params_schema.get("properties") or {}).keys())
    args = _evaluate_args(node, ctx, [ParamDef(n) for n in names])
    required = params_schema.get("required") or []
    return {k: v for k, v in args.items() if not (v is None and k not in required)}


def _check_value(value: Any, schema: Any, name: str, path: str, ctx: EvalContext, strict: bool = False) -> Any:
    issues = IssueCtx(source="runtime")
    checked = validate_value(value, schema, name, path, issues)
    for e in issues.errors:
        if ctx.report_error:
            ctx.report_error(f"@{name}: {e.message}")
    return INVALID if strict and issues.errors else checked


def _misses_required(args: dict[str, Any], params_schema: dict) -> bool:
    props = params_schema.get("properties") or {}
    for key in params_schema.get("required") or []:
        if args.get(key) is None and not schema_default(props.get(key))[0]:
            return True
    return False


def _call_function(name: str, node: Comp, ctx: EvalContext) -> Any:
    lib = ctx.lib
    assert lib is not None
    schema = lib.function_schemas.get(name) or {}
    params_schema = schema.get("params") or {}
    raw = _call_args(node, ctx, params_schema)
    if _misses_required(raw, params_schema):
        return None
    args = _check_value(raw, params_schema, name, "", ctx)
    if args is INVALID:
        return None
    fn = lib.functions.get(name)
    if fn is None:
        if ctx.report_error:
            ctx.report_error(f"@{name} has no implementation")
        return None
    try:
        result = fn(dict(args))
    except Exception as exc:  # a custom function must never crash the host
        if ctx.report_error:
            ctx.report_error(f"@{name} threw: {exc}")
        return None
    returns = schema.get("returns")
    if returns is None:
        return result
    checked = _check_value(result, returns, name, "/returns", ctx)
    return None if checked is INVALID else checked


def _evaluate_call(node: Comp, ctx: EvalContext) -> Any:
    name = node.name
    builtin = BUILTIN_FUNCTIONS.get(name)
    if builtin is not None:
        params, fn = builtin
        if fn is None:
            return _evaluate_each(node, ctx)
        return fn(**_evaluate_args(node, ctx))
    if _is_step(name, ctx.lib):
        return _evaluate_action_call(node, ctx)
    lib = ctx.lib
    if lib is not None and name in lib.function_schemas:
        return _call_function(name, node, ctx)
    if lib is not None and name in lib.action_schemas:
        params_schema = (lib.action_schemas[name] or {}).get("params") or {}
        args = _call_args(node, ctx, params_schema)
        if _misses_required(args, params_schema):
            return ActionPlan([])
        params = _check_value(args, params_schema, name, "", ctx, strict=True)
        if params is INVALID:
            return ActionPlan([])
        return ActionPlan([CustomStep(type="custom_action", name=name, params=dict(params))])
    if node.mapped_props is not None:
        props: dict[str, Any] = {}
        for key, val in node.mapped_props.items():
            if isinstance(val, StateRef) and lib is not None and lib.is_bindable(name, key):
                props[key] = Binding(val.n, StateRef("$value"))
            else:
                props[key] = evaluate(val, ctx)
        return Element(name, props)
    return None  # an unknown component in a computed expression renders nothing


def _flatten_plans(values: list[Any]) -> ActionPlan:
    steps: list[dict[str, Any]] = []
    for v in values:
        if isinstance(v, ActionPlan):
            steps.extend(v.steps)
        elif isinstance(v, dict) and "type" in v:
            steps.append(v)
    return own_steps(ActionPlan(steps))


def own_steps(plan: ActionPlan) -> ActionPlan:
    """Drop custom steps no real call made, so data cannot pose as a custom action."""
    def own(s: Any) -> bool:
        return not (isinstance(s, dict) and s.get("type") == "custom_action" and not isinstance(s, CustomStep))

    if all(own(s) for s in plan.steps):
        return plan
    return ActionPlan([s for s in plan.steps if own(s)])


def _evaluate_action_call(node: Comp, ctx: EvalContext) -> ActionPlan:
    name, args = node.name, node.args
    if name == "Action":
        lst = evaluate(args[0], ctx) if args else []
        return _flatten_plans(lst if isinstance(lst, list) else [])
    step: dict[str, Any] | None
    if name == "ToAssistant":
        a = _evaluate_args(node, ctx)
        message = a.get("message")
        step = {"type": ACTION_STEP_TYPES[name], "message": _js.to_string("" if message is None else message)}
        if a.get("context") is not None:
            step["context"] = a["context"]
    elif name == "OpenUrl":
        url = _evaluate_args(node, ctx).get("url")
        step = {"type": ACTION_STEP_TYPES[name], "url": _js.to_string("" if url is None else url)}
    else:
        step = _evaluate_lazy_step(name, args)
    return ActionPlan([step] if step else [])


def _evaluate_lazy_step(name: str, args: list[AST]) -> dict[str, Any] | None:
    if name == "Run":
        ref = args[0] if args else None
        if not isinstance(ref, RuntimeRef):
            return None
        return {"type": "run", "statementId": ref.n, "refType": ref.ref_type}
    if name == "Set":
        if len(args) < 2 or not isinstance(args[0], StateRef):
            return None
        return {"type": "set", "target": args[0].n, "valueAST": args[1]}
    if name == "Reset":
        targets = [a.n for a in args if isinstance(a, StateRef)]
        if not targets:
            return None
        return {"type": "reset", "targets": targets}
    return None


def _substitute(node: AST, var: str, value: Any) -> AST:
    """Replace ``Ref(var)`` with the element's literal value (captures it for deferred steps)."""
    if isinstance(node, Ref):
        return to_literal_ast(value) if node.n == var else node
    if isinstance(node, Member):
        sub = _substitute(node.obj, var, value)
        if isinstance(sub, Obj):
            for k, v in sub.entries:
                if k == node.field:
                    return v
        return Member(sub, node.field)
    if isinstance(node, Index):
        return Index(_substitute(node.obj, var, value), _substitute(node.index, var, value))
    if isinstance(node, BinOp):
        return BinOp(node.op, _substitute(node.left, var, value), _substitute(node.right, var, value))
    if isinstance(node, UnaryOp):
        return UnaryOp(node.op, _substitute(node.operand, var, value))
    if isinstance(node, Ternary):
        return Ternary(_substitute(node.cond, var, value), _substitute(node.then, var, value),
                       _substitute(node.else_, var, value))
    if isinstance(node, Arr):
        return Arr([_substitute(e, var, value) for e in node.els])
    if isinstance(node, Obj):
        return Obj([(k, _substitute(v, var, value)) for k, v in node.entries])
    if isinstance(node, Comp):
        mapped = ({k: _substitute(v, var, value) for k, v in node.mapped_props.items()}
                  if node.mapped_props is not None else None)
        return replace(node, args=[_substitute(a, var, value) for a in node.args], mapped_props=mapped)
    if isinstance(node, Assign):
        return Assign(node.target, _substitute(node.value, var, value))
    return node


def _evaluate_each(node: Comp, ctx: EvalContext) -> Any:
    args = node.args
    if len(args) < 3:
        return []
    arr = evaluate(args[0], ctx)
    if not isinstance(arr, list):
        return []
    v = args[1]
    var = v.n if isinstance(v, Ref) else v.v if isinstance(v, Str) else None
    if not var:
        return []
    out = []
    for item in arr:
        sub = _substitute(args[2], var, item)
        outer = ctx.resolve_ref

        def resolve(n: str, _item: Any = item, _outer: Callable = outer) -> Any:
            return _item if n == var else _outer(n)

        out.append(evaluate(sub, replace(ctx, resolve_ref=resolve)))
    return out


# ─── element trees ─────────────────────────────────────────────────────────


def evaluate_prop(value: Any, ctx: EvalContext, bindable: bool, errors: list[OpenUIError] | None) -> Any:
    if value is None or not isinstance(value, (list, dict, Node, Element, ActionPlan, Binding)):
        return value
    if is_ast(value):
        if isinstance(value, StateRef) and bindable:
            return Binding(value.n, StateRef("$value"))
        result = evaluate(value, ctx)
        if isinstance(result, Element):
            return evaluate_element(result, ctx, errors)
        if isinstance(result, list):
            return [evaluate_element(i, ctx, errors) if isinstance(i, Element) else i for i in result]
        if isinstance(result, Binding) and not bindable:
            return ctx.get_state(result.target)
        if isinstance(result, ActionPlan):
            return own_steps(result)
        return result
    if isinstance(value, list):
        return [evaluate_prop(v, ctx, bindable, errors) for v in value]
    if isinstance(value, Element):
        return evaluate_element(value, ctx, errors)
    if isinstance(value, (ActionPlan, Binding)):
        return value
    return {k: evaluate_prop(v, ctx, bindable, errors) for k, v in value.items()}


def evaluate_element(el: Element, ctx: EvalContext, errors: list[OpenUIError] | None = None) -> Element:
    """Evaluate every prop of an element tree to concrete values."""
    lib = ctx.lib
    out: dict[str, Any] = {}
    current = [""]

    def report(msg: str) -> None:
        if errors is not None:
            key = current[0]
            errors.append(OpenUIError(
                source="runtime",
                code="runtime-error",
                message=f'Evaluating prop "{key}" on {el.type_name} failed: {msg}',
                statement_id=el.statement_id,
                component=el.type_name,
                hint=f'Check the expression used for prop "{key}"',
            ))

    prop_ctx = replace(ctx, report_error=report)
    for key, value in el.props.items():
        current[0] = key
        bindable = lib.is_bindable(el.type_name, key) if lib else False
        try:
            out[key] = evaluate_prop(value, prop_ctx, bindable, errors)
        except Exception as exc:  # evaluation must never crash the host
            out[key] = None
            report(str(exc) or type(exc).__name__)
    return replace(el, props=out)


def evaluate_root(
    root: Element | None,
    root_expression: AST | None,
    ctx: EvalContext,
    errors: list[OpenUIError] | None = None,
    entry_id: str | None = "root",
) -> Element | None:
    """Evaluate the entry: the root element, or the component a runtime entry picks."""
    if root is not None:
        return evaluate_element(root, ctx, errors)
    if root_expression is None:
        return None
    try:
        value = evaluate(root_expression, ctx)
    except Exception:
        value = None
    if isinstance(value, Element):
        return evaluate_element(value, ctx, errors)
    if errors is not None:
        errors.append(OpenUIError(
            source="runtime",
            code="no-root",
            message="root does not evaluate to a component",
            statement_id=entry_id,
            hint="Make root evaluate to a component call",
        ))
    return None


__all__ = ["EvalContext", "evaluate", "evaluate_element", "evaluate_prop", "evaluate_root", "own_steps"]
