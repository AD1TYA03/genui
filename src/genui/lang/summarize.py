"""The canonical JSON of a program (spec/fixtures/1.0/README.md, "How the tree is summarized")."""

from __future__ import annotations

from typing import Any, Mapping

from .ast import is_ast
from .evaluator import EvalContext, evaluate
from .parser import ParseResult
from .values import ActionPlan, Binding, Element

_STEP_NAMES = {
    "continue_conversation": "ToAssistant",
    "open_url": "OpenUrl",
    "set": "Set",
    "reset": "Reset",
    "run": "Run",
}


_MAX_DEPTH = 200


def summarize_value(value: Any, ctx: EvalContext | None = None, _seen: tuple = ()) -> Any:
    """Summarize an evaluated value: components as ``{type, props}`` (null props left
    out), actions as ``{actions: [{action, args}]}``, bindings as ``{$binding}``.

    A value that contains itself (``$x = @Set($x, $x)`` read back through state)
    summarizes the inner occurrence as null.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if id(value) in _seen or len(_seen) > _MAX_DEPTH:
        return None
    seen = (*_seen, id(value))
    if isinstance(value, list):
        return [summarize_value(v, ctx, seen) for v in value]
    if isinstance(value, Element):
        props = {}
        for k, v in value.props.items():
            s = summarize_value(v, ctx, seen)
            if s is not None:
                props[k] = s
        return {"type": value.type_name, "props": props}
    if isinstance(value, ActionPlan):
        return {"actions": [_summarize_step(s, ctx, seen) for s in value.steps]}
    if isinstance(value, Binding):
        return {"$binding": value.target}
    if isinstance(value, dict):
        return {str(k): summarize_value(v, ctx, seen) for k, v in value.items()}
    if is_ast(value) and ctx is not None:
        return summarize_value(evaluate(value, ctx), ctx, seen)
    return None


def _summarize_step(step: Mapping[str, Any], ctx: EvalContext | None, seen: tuple = ()) -> dict[str, Any]:
    t = step.get("type")
    if t == "continue_conversation":
        context = step.get("context")
        args = [step.get("message")] if context is None else [step.get("message"), summarize_value(context, ctx, seen)]
        return {"action": "ToAssistant", "args": args}
    if t == "open_url":
        return {"action": "OpenUrl", "args": [step.get("url")]}
    if t == "set":
        value_ast = step.get("valueAST")
        value = evaluate(value_ast, ctx) if (ctx is not None and value_ast is not None) else None
        return {"action": "Set", "args": [step.get("target"), summarize_value(value, ctx, seen)]}
    if t == "reset":
        return {"action": "Reset", "args": list(step.get("targets") or [])}
    if t == "run":
        return {"action": "Run", "args": [step.get("statementId")]}
    params = step.get("params") or {}
    name = step.get("name") or t
    keys: list[str] = list(params)
    lib = ctx.lib if ctx is not None else None
    if lib is not None and name in lib.action_schemas:
        keys = list(((lib.action_schemas[name] or {}).get("params") or {}).get("properties") or {})
    return {"action": name, "args": [summarize_value(params.get(k), ctx, seen) for k in keys]}


def summarize(
    result: ParseResult,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The canonical JSON of a parse result, evaluated at stream end.

    Keys: ``root``, ``errors`` (``{code, statementId}``), ``unresolved``,
    ``orphans``, ``incomplete``, ``state``, ``statements``, and ``errorObjects``
    (the full error objects of language.md, section 8.3). No query has returned,
    so query references read their defaults and mutations read idle.
    """
    ctx = result.eval_context(state)
    evaluation = result.evaluate(state)
    errors = [*result.errors, *evaluation.errors]
    return {
        "root": summarize_value(evaluation.root, ctx),
        "errors": [
            {"code": e.code, **({"statementId": e.statement_id} if e.statement_id is not None else {})}
            for e in errors
        ],
        "unresolved": list(result.unresolved),
        "orphans": list(result.orphans),
        "incomplete": result.incomplete,
        "state": summarize_value(dict(result.state), ctx),
        "statements": list(result.statements),
        "errorObjects": [e.to_dict() for e in errors],
    }
