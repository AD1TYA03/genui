"""The canonical JSON of a program (spec/fixtures/1.0/README.md, "How the tree is summarized")."""

from __future__ import annotations

from typing import Any, Mapping

from .ast import is_ast
from .evaluator import EvalContext, evaluate
from .parser import ParseResult
from .tsjson import ast_json, ts_json
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
        # the reference runner recognizes these shapes in data too
        if value.get("type") == "element":
            props = value.get("props") if isinstance(value.get("props"), dict) else {}
            out: dict[str, Any] = {"props": {}}
            if value.get("typeName") is not None:
                out = {"type": value.get("typeName"), "props": {}}
            for k, v in props.items():
                s = summarize_value(v, ctx, seen)
                if s is not None:
                    out["props"][k] = s
            return out
        if isinstance(value.get("steps"), list):
            return {"actions": [_summarize_step(s, ctx, seen) for s in value["steps"]]}
        if value.get("__reactive") == "assign":
            return {"$binding": value.get("target")}
        return {str(k): summarize_value(v, ctx, seen) for k, v in value.items()}
    if is_ast(value):
        # An unevaluated expression (a prop that threw) is the reference's AST object.
        return summarize_value(ast_json(value), ctx, seen)
    return None


def _summarize_step(step: Any, ctx: EvalContext | None, seen: tuple = ()) -> dict[str, Any]:
    if not isinstance(step, dict):
        return {"args": []}
    t = step.get("type")
    if t == "continue_conversation":
        context = step.get("context")
        args = [step.get("message")] if context is None else [step.get("message"), ts_json(context)]
        return {"action": "ToAssistant", "args": args}
    if t == "open_url":
        return {"action": "OpenUrl", "args": [step.get("url")]}
    if t == "set":
        value_ast = step.get("valueAST")
        value = evaluate(value_ast, ctx) if (ctx is not None and value_ast is not None) else None
        # as in the reference runner, the context and the Set value are raw values (JSON only)
        return {"action": "Set", "args": [step.get("target"), ts_json(value)]}
    if t == "reset":
        return {"action": "Reset", "args": list(step.get("targets") or [])}
    if t == "run":
        return {"action": "Run", "args": [step.get("statementId")]}
    params = step.get("params") or {}
    name = step.get("name")
    keys: list[str] = list(params) if isinstance(params, dict) else []
    lib = ctx.lib if ctx is not None else None
    if lib is not None and name in lib.action_schemas:
        keys = list(((lib.action_schemas[name] or {}).get("params") or {}).get("properties") or {})
    args = [summarize_value(params.get(k) if isinstance(params, dict) else None, ctx, seen) for k in keys]
    # a step with no name (data posing as a step) has no `action` key, as in the reference's JSON
    return {"action": name, "args": args} if name is not None else {"args": args}


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
        "state": ts_json(dict(result.state)),
        "statements": list(result.statements),
        "errorObjects": [e.to_dict() for e in errors],
    }
