"""Reading a LibrarySpec for parsing and evaluation (prompt.md, section 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .builtins import ACTION_DEF_NAMES, BUILTIN_CALLS, CallDef, ParamDef

_BINDING_RE = re.compile(r"(\w+)\??\s*:\s*\$binding<")

#: A custom function implementation: receives one dict keyed by the ``params`` names.
CustomFunction = Callable[[dict[str, Any]], Any]


def _inline_action_refs(node: Any, defs: Mapping[str, Any], depth: int = 0) -> Any:
    """``{"$ref": "#/$defs/ActionExpression"}`` -> its body, so action slots validate inline."""
    if depth > 32:
        return node
    if isinstance(node, list):
        return [_inline_action_refs(v, defs, depth + 1) for v in node]
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if isinstance(ref, str):
        return _inline_action_refs(defs[ref], defs, depth + 1) if ref in defs else node
    return {k: _inline_action_refs(v, defs, depth + 1) for k, v in node.items()}


def _compile_params(definition: Any, defs: Mapping[str, Any]) -> list[ParamDef]:
    if not isinstance(definition, dict):
        return []
    properties = definition.get("properties") or {}
    required = definition.get("required") or []
    params = []
    for key, prop in properties.items():
        has_default = isinstance(prop, dict) and "default" in prop
        params.append(ParamDef(
            name=key,
            required=key in required,
            default=prop.get("default") if has_default else None,
            has_default=has_default,
            schema=_inline_action_refs(prop, defs) if defs else prop,
        ))
    return params


@dataclass
class CompiledLibrary:
    """A LibrarySpec compiled for the parser: positional params, call registry, bindings."""

    spec: dict[str, Any]
    schema: dict[str, Any]
    root: str | None
    components: dict[str, list[ParamDef]]
    call_defs: dict[str, CallDef]
    #: component name -> names of its bindable props (``$binding<...>`` in the signature)
    bindable: dict[str, frozenset[str]]
    #: ``schema.functions`` entries (JSON Schema params/returns)
    function_schemas: dict[str, Any]
    #: ``schema.actions`` entries
    action_schemas: dict[str, Any]
    #: runner-supplied implementations of custom functions
    functions: dict[str, CustomFunction] = field(default_factory=dict)

    @property
    def component_names(self) -> list[str]:
        return list(self.components)

    def with_functions(self, functions: Mapping[str, CustomFunction] | None) -> "CompiledLibrary":
        if not functions:
            return self
        merged = dict(self.functions)
        merged.update(functions)
        return CompiledLibrary(
            self.spec, self.schema, self.root, self.components, self.call_defs, self.bindable,
            self.function_schemas, self.action_schemas, merged,
        )

    def is_bindable(self, component: str, prop: str) -> bool:
        return prop in self.bindable.get(component, ())


def compile_library(
    library: Mapping[str, Any] | CompiledLibrary,
    functions: Mapping[str, CustomFunction] | None = None,
) -> CompiledLibrary:
    """Compile a LibrarySpec (or a bare ``schema`` document) for the parser.

    ``functions`` supplies implementations for the library's custom functions,
    keyed by name. Each receives one dict keyed by the function's param names.
    """
    if isinstance(library, CompiledLibrary):
        return library.with_functions(functions)
    spec = dict(library)
    schema = spec.get("schema") if isinstance(spec.get("schema"), dict) else None
    if schema is None:
        schema = spec  # a bare JSON Schema document
    defs_all: dict[str, Any] = schema.get("$defs") or {}
    props = schema.get("properties")
    component_set = set(props) if isinstance(props, dict) else None
    action_schemas: dict[str, Any] = schema.get("actions") or {}
    function_schemas: dict[str, Any] = schema.get("functions") or {}

    # Action $defs (ActionExpression, OpenUrl, custom actions) are data shapes, never components.
    action_defs: dict[str, Any] = {}
    for name in [*ACTION_DEF_NAMES, *action_schemas]:
        body = defs_all.get(name)
        if body is not None and (component_set is None or name not in component_set):
            action_defs[f"#/$defs/{name}"] = body

    components: dict[str, list[ParamDef]] = {}
    for name, definition in defs_all.items():
        if component_set is not None:
            if name not in component_set:
                continue
        elif f"#/$defs/{name}" in action_defs:
            continue
        components[name] = _compile_params(definition, action_defs)

    call_defs: dict[str, CallDef] = dict(BUILTIN_CALLS)
    for name, fn in function_schemas.items():
        call_defs[name] = CallDef("function", _compile_params((fn or {}).get("params"), action_defs))
    for name, act in action_schemas.items():
        call_defs[name] = CallDef("action", _compile_params((act or {}).get("params"), action_defs))

    bindable: dict[str, frozenset[str]] = {}
    for name, entry in (spec.get("components") or {}).items():
        signature = entry.get("signature", "") if isinstance(entry, dict) else ""
        found = frozenset(_BINDING_RE.findall(signature))
        if found:
            bindable[name] = found

    root = spec.get("root") if isinstance(spec.get("root"), str) else None
    return CompiledLibrary(
        spec=spec,
        schema=schema,
        root=root,
        components=components,
        call_defs=call_defs,
        bindable=bindable,
        function_schemas=function_schemas,
        action_schemas=action_schemas,
        functions=dict(functions or {}),
    )
