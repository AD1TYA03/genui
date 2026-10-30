"""Load and inspect an OpenUI LibrarySpec (spec/prompt.md, sections 2, 3 and 5).

A LibrarySpec is one JSON document describing the components, custom
functions and custom actions a frontend understands. The schema's key order is
the positional order of arguments, so everything here keeps JSON key order.

    >>> lib = Library.from_spec("library.json")
    >>> lib.validate()
    >>> lib.components["Button"].props[0].name
    'label'
    >>> print(lib.system_prompt(tools=["list_orders"]))
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "BUILTIN_ACTION_NAMES",
    "BUILTIN_FUNCTION_NAMES",
    "CallInfo",
    "ComponentInfo",
    "Library",
    "LibraryError",
    "PropInfo",
    "RESERVED_NAMES",
]


class LibraryError(ValueError):
    """Raised for a LibrarySpec that cannot be loaded or breaks section 3.1."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues: list[str] = list(issues) if issues else [message]


# ─── Built-in names (lang-core parser/builtins.ts) ──────────────────────────

BUILTIN_FUNCTION_NAMES: tuple[str, ...] = (
    "Count", "First", "Last", "Sum", "Avg", "Min", "Max", "Sort", "Filter",
    "Round", "Abs", "Floor", "Ceil", "Each",
)  # fmt: skip
BUILTIN_ACTION_NAMES: tuple[str, ...] = ("Run", "ToAssistant", "OpenUrl", "Set", "Reset")
#: Names no component, function or action may use (spec/prompt.md section 3.1).
RESERVED_NAMES: frozenset[str] = frozenset(
    BUILTIN_FUNCTION_NAMES + BUILTIN_ACTION_NAMES + ("Action", "Query", "Mutation")
)
#: Built-in action `$defs` names. A `$ref` to one of these (other than
#: ActionExpression) is a restricted action slot and prints as `@Name`.
_BUILTIN_ACTION_DEFS = ("ActionExpression", "OpenUrl", "ToAssistant")

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_REF = re.compile(r"#/\$defs/(.+)\Z")
_MISSING = object()


# ─── Data classes ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PropInfo:
    """One positional argument of a component, function or action."""

    name: str
    #: Signature type, e.g. ``string``, ``"a" | "b"``, ``Card[]``, ``$binding<string>``.
    type: str
    #: Listed in the schema's ``required``.
    required: bool
    #: Printed with ``?``: not required, or has a ``default``, or nullable.
    optional: bool
    #: True when the provided signature marks the prop ``$binding<...>``.
    binding: bool = False
    has_default: bool = False
    default: Any = None
    schema: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ComponentInfo:
    name: str
    signature: str
    description: str
    props: tuple[PropInfo, ...]

    @property
    def prop_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.props)


@dataclass(frozen=True)
class CallInfo:
    """A custom function (``returns`` may be set) or custom action (no returns)."""

    name: str
    signature: str
    description: str
    params: tuple[PropInfo, ...]
    returns: Mapping[str, Any] | None = None
    #: Return type as printed after ``→`` (functions only).
    return_type: str | None = None

    @property
    def param_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.params)


# ─── JSON Schema → signature types (spec/prompt.md section 5.1) ─────────────


def _js_string(value: Any) -> str:
    """``String(v)`` as JavaScript prints it, for literal / enum values."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value.is_integer() and abs(value) < 1e21:
            return str(int(value))
        text = repr(value)
        if "e" in text:
            mantissa, exp = text.split("e")
            sign = "-" if exp.startswith("-") else "+"
            text = f"{mantissa}e{sign}{exp.lstrip('+-').lstrip('0') or '0'}"
        return text
    if isinstance(value, (dict, list)):
        return "[object Object]" if isinstance(value, dict) else ",".join(_js_string(v) for v in value)
    return str(value)


def _is_null_schema(s: Any) -> bool:
    return isinstance(s, dict) and (s.get("type") == "null" or s.get("const", _MISSING) is None and len(s) == 1)


class _TypePrinter:
    """Prints a JSON Schema fragment the way lang-core's ``signature.ts`` prints
    the zod schema it came from (``resolveTypeAnnotation``)."""

    def __init__(self, action_names: set[str], defs: Mapping[str, Any]) -> None:
        self.action_names = action_names
        self.defs = defs

    def nullable_inner(self, s: Any) -> tuple[Any, bool]:
        """Strip a nullable wrapper: ``{"type": ["string", "null"]}`` or
        ``{"anyOf": [X, {"type": "null"}]}``. Returns (inner, was_nullable)."""
        if not isinstance(s, dict):
            return s, False
        t = s.get("type")
        if isinstance(t, list) and "null" in t:
            rest = [x for x in t if x != "null"]
            inner = dict(s)
            if len(rest) == 1:
                inner["type"] = rest[0]
            elif rest:
                inner["type"] = rest
            else:
                inner.pop("type")
            return inner, True
        for key in ("anyOf", "oneOf"):
            opts = s.get(key)
            if isinstance(opts, list) and any(_is_null_schema(o) for o in opts):
                rest = [o for o in opts if not _is_null_schema(o)]
                if len(rest) == 1:
                    return rest[0], True
                inner = {k: v for k, v in s.items() if k != key}
                inner[key] = rest
                return inner, True
        return s, False

    def ref_name(self, ref: str) -> str:
        m = _REF.match(ref)
        name = m.group(1) if m else ref.rsplit("/", 1)[-1]
        if name in self.action_names:
            return f"@{name}"
        return name

    def type_of(self, s: Any) -> str:
        inner, _ = self.nullable_inner(s)
        return self.base(inner)

    def base(self, s: Any) -> str:
        if not isinstance(s, dict):
            return "any"
        ref = s.get("$ref")
        if isinstance(ref, str):
            return self.ref_name(ref)
        for key in ("anyOf", "oneOf"):
            opts = s.get(key)
            if isinstance(opts, list) and opts:
                return " | ".join(self.type_of(o) for o in opts)
        enum = s.get("enum")
        if isinstance(enum, list):
            return " | ".join(f'"{_js_string(v)}"' for v in enum)
        if "const" in s:
            v = s["const"]
            return f'"{v}"' if isinstance(v, str) else _js_string(v)
        t = s.get("type")
        if t == "array":
            items = s.get("items")
            if items is None or items is True:
                return "any[]"
            item_inner, _ = self.nullable_inner(items)
            item_type = self.type_of(items)
            is_union = isinstance(item_inner, dict) and any(
                isinstance(item_inner.get(k), list) and item_inner.get(k) for k in ("anyOf", "oneOf")
            ) and "$ref" not in item_inner
            return f"({item_type})[]" if is_union else f"{item_type}[]"
        if t == "string":
            return "string"
        if t in ("number", "integer"):
            return "number"
        if t == "boolean":
            return "boolean"
        if t == "object" or "properties" in s or "additionalProperties" in s:
            props = s.get("properties")
            extra = s.get("additionalProperties")
            if not props and (isinstance(extra, dict) or extra is True):
                key = s.get("propertyNames")
                key_type = self.type_of(key) if isinstance(key, dict) and key else "string"
                value_type = self.type_of(extra) if isinstance(extra, dict) else "any"
                return f"Record<{key_type}, {value_type}>"
            if isinstance(props, dict):
                fields = [
                    f"{name}{'?' if _optional(name, sub, s.get('required')) else ''}: {self.type_of(sub)}"
                    for name, sub in props.items()
                ]
                return "{" + ", ".join(fields) + "}"
            return "{}"
        return "any"


def _optional(name: str, prop_schema: Any, required: Any) -> bool:
    """A prop prints with ``?`` when it is not required, has a default, or is nullable."""
    req = required if isinstance(required, list) else []
    if name not in req:
        return True
    if isinstance(prop_schema, dict):
        t = prop_schema.get("type")
        if "default" in prop_schema or (isinstance(t, list) and "null" in t):
            return True
        for key in ("anyOf", "oneOf"):
            opts = prop_schema.get(key)
            if isinstance(opts, list) and any(_is_null_schema(o) for o in opts):
                return True
    return False


# ─── Signature string helpers ───────────────────────────────────────────────


def _split_top_level(text: str) -> list[str]:
    """Split ``a: T, b?: {x: U, y: V}`` at top-level commas."""
    parts: list[str] = []
    depth = 0
    quote = False
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == '"':
                quote = False
        elif ch == '"':
            quote = True
        elif ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _binding_params(signature: str) -> dict[str, str]:
    """Param name -> inner type for every ``$binding<...>`` param of a signature."""
    open_paren = signature.find("(")
    if open_paren < 0:
        return {}
    depth = 0
    close = -1
    quote = False
    for i in range(open_paren, len(signature)):
        ch = signature[i]
        if quote:
            if ch == '"':
                quote = False
            continue
        if ch == '"':
            quote = True
        elif ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
            if depth == 0:
                close = i
                break
    if close < 0:
        return {}
    out: dict[str, str] = {}
    for param in _split_top_level(signature[open_paren + 1 : close]):
        name, sep, type_ = param.partition(":")
        if not sep:
            continue
        type_ = type_.strip()
        if type_.startswith("$binding<") and type_.endswith(">"):
            out[name.strip().rstrip("?")] = type_[len("$binding<") : -1]
    return out


# ─── Library ─────────────────────────────────────────────────────────────────


class Library:
    """An OpenUI component library, loaded from a LibrarySpec."""

    def __init__(self, spec: Mapping[str, Any], *, validate: bool = False) -> None:
        if not isinstance(spec, Mapping):
            raise LibraryError("A LibrarySpec must be a JSON object.")
        comps = spec.get("components")
        if not isinstance(comps, Mapping):
            raise LibraryError("LibrarySpec.components must be an object keyed by component name.")
        for key in ("functions", "actions"):
            if spec.get(key) is not None and not isinstance(spec.get(key), Mapping):
                raise LibraryError(f"LibrarySpec.{key} must be an object keyed by name.")
        if spec.get("schema") is not None and not isinstance(spec.get("schema"), Mapping):
            raise LibraryError("LibrarySpec.schema must be an object (JSON Schema).")
        if spec.get("componentGroups") is not None and not isinstance(spec.get("componentGroups"), list):
            raise LibraryError("LibrarySpec.componentGroups must be a list.")
        self._spec: dict[str, Any] = copy.deepcopy(dict(spec))
        self._components: dict[str, ComponentInfo] | None = None
        self._functions: dict[str, CallInfo] | None = None
        self._actions: dict[str, CallInfo] | None = None
        if validate:
            self.validate()

    # ── construction ──

    @classmethod
    def from_spec(
        cls, source: str | os.PathLike[str] | Mapping[str, Any] | bytes, *, validate: bool = False
    ) -> Library:
        """Load from a dict, a JSON string, JSON bytes, or a path to a JSON file.

        A string that starts with ``{`` (after whitespace) is parsed as JSON;
        any other string is a file path. Pass ``validate=True`` to raise on any
        spec section 3.1 rule violation (see :meth:`issues`). It is off by default
        because real libraries, including OpenUI's own ``react-ui`` library, break
        some of those rules and still render fine.
        """
        if isinstance(source, Mapping):
            data: Any = source
        elif isinstance(source, (bytes, bytearray)):
            data = cls._parse_json(source.decode("utf-8"))
        elif isinstance(source, str) and source.lstrip().startswith("{"):
            data = cls._parse_json(source)
        elif isinstance(source, (str, os.PathLike)):
            path = Path(source)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise LibraryError(f"Cannot read LibrarySpec file {str(path)!r}: {exc}") from exc
            data = cls._parse_json(text)
        else:
            raise LibraryError(f"Unsupported LibrarySpec source of type {type(source).__name__}.")
        return cls(data, validate=validate)

    @staticmethod
    def _parse_json(text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LibraryError(f"LibrarySpec is not valid JSON: {exc}") from exc

    # ── raw fields ──

    @property
    def id(self) -> str | None:
        return self._spec.get("id")

    @property
    def version(self) -> str | None:
        return self._spec.get("version")

    @property
    def root(self) -> str | None:
        return self._spec.get("root")

    @property
    def schema(self) -> dict[str, Any]:
        """The validation schema (JSON Schema). Empty dict when the spec has none."""
        return self._spec.get("schema") or {}

    @property
    def component_groups(self) -> list[dict[str, Any]] | None:
        return self._spec.get("componentGroups")

    @property
    def spec(self) -> dict[str, Any]:
        """The raw LibrarySpec (do not mutate)."""
        return self._spec

    def __repr__(self) -> str:
        label = self.id or "anonymous"
        return f"<Library {label} components={len(self._spec['components'])}>"

    # ── derived views ──

    def _defs(self) -> dict[str, Any]:
        defs = self.schema.get("$defs")
        return defs if isinstance(defs, dict) else {}

    def _action_names(self) -> set[str]:
        """Names a `$ref` resolves to as an action (prints `@Name`). A component
        of the same name wins, as in createLibrary()."""
        names = set(self._spec.get("actions") or {}) | set((self.schema.get("actions") or {}))
        names |= {"OpenUrl", "ToAssistant"}
        return names - set(self._spec["components"])

    def _printer(self) -> _TypePrinter:
        return _TypePrinter(self._action_names(), self._defs())

    def _component_schema(self, name: str) -> dict[str, Any] | None:
        defs = self._defs()
        entry = defs.get(name)
        if entry is None:
            ref = (self.schema.get("properties") or {}).get(name)
            if isinstance(ref, dict) and isinstance(ref.get("$ref"), str):
                m = _REF.match(ref["$ref"])
                if m:
                    entry = defs.get(m.group(1))
        return entry if isinstance(entry, dict) else None

    def _props(self, params_schema: Any, signature: str) -> tuple[PropInfo, ...]:
        if not isinstance(params_schema, dict):
            return ()
        props = params_schema.get("properties")
        if not isinstance(props, dict):
            return ()
        required = params_schema.get("required")
        req = required if isinstance(required, list) else []
        bindings = _binding_params(signature)
        printer = self._printer()
        out = []
        for name, sub in props.items():
            base = printer.type_of(sub)
            is_binding = name in bindings
            out.append(
                PropInfo(
                    name=name,
                    type=f"$binding<{base}>" if is_binding else base,
                    required=name in req,
                    optional=_optional(name, sub, required),
                    binding=is_binding,
                    has_default=isinstance(sub, dict) and "default" in sub,
                    default=sub.get("default") if isinstance(sub, dict) else None,
                    schema=sub if isinstance(sub, dict) else {},
                )
            )
        return tuple(out)

    @property
    def components(self) -> dict[str, ComponentInfo]:
        """Ordered name -> :class:`ComponentInfo` (props in positional order)."""
        if self._components is None:
            out: dict[str, ComponentInfo] = {}
            for name, entry in self._spec["components"].items():
                entry = entry if isinstance(entry, Mapping) else {}
                sig = entry.get("signature") or ""
                out[name] = ComponentInfo(
                    name=name,
                    signature=sig,
                    description=entry.get("description") or "",
                    props=self._props(self._component_schema(name), sig),
                )
            self._components = out
        return dict(self._components)

    def _calls(self, kind: str) -> dict[str, CallInfo]:
        listed = self._spec.get(kind) or {}
        schemas = self.schema.get(kind) or {}
        out: dict[str, CallInfo] = {}
        for name in list(listed) + [n for n in schemas if n not in listed]:
            entry = listed.get(name) if isinstance(listed.get(name), Mapping) else {}
            sch = schemas.get(name) if isinstance(schemas.get(name), Mapping) else {}
            sig = entry.get("signature") or ""
            returns = sch.get("returns") if kind == "functions" else None
            out[name] = CallInfo(
                name=name,
                signature=sig,
                description=entry.get("description") or sch.get("description") or "",
                params=self._props(sch.get("params"), sig),
                returns=returns,
                return_type=self._printer().type_of(returns) if returns else None,
            )
        return out

    @property
    def functions(self) -> dict[str, CallInfo]:
        """Ordered name -> :class:`CallInfo` for the custom functions."""
        if self._functions is None:
            self._functions = self._calls("functions")
        return dict(self._functions)

    @property
    def actions(self) -> dict[str, CallInfo]:
        """Ordered name -> :class:`CallInfo` for the custom actions."""
        if self._actions is None:
            self._actions = self._calls("actions")
        return dict(self._actions)

    # ── signatures ──

    def signature(self, name: str) -> str:
        """Signature of a component, custom function or custom action, rebuilt
        from the schema (spec/prompt.md 2.4 and 5.1). ``$binding<type>`` is
        taken from the provided signature, since the schema cannot express it.
        Falls back to the provided signature when the schema has no entry."""
        if name in self._spec["components"]:
            info = self.components[name]
            if self._component_schema(name) is None:
                return info.signature
            return _build_signature(name, info.props)
        for kind in ("functions", "actions"):
            calls = self.functions if kind == "functions" else self.actions
            if name in calls:
                call = calls[name]
                sch = (self.schema.get(kind) or {}).get(name)
                if not isinstance(sch, Mapping) or not isinstance(sch.get("params"), Mapping):
                    return call.signature
                sig = _build_signature(name, call.params)
                return f"{sig} → {call.return_type}" if call.return_type else sig
        raise KeyError(f"No component, function or action named {name!r}")

    # ── export ──

    def to_spec(self) -> dict[str, Any]:
        """The LibrarySpec as a dict, in its original key order (a deep copy)."""
        return copy.deepcopy(self._spec)

    def to_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("ensure_ascii", False)
        return json.dumps(self._spec, **kwargs)

    def system_prompt(self, **options: Any) -> str:
        """Shortcut for :func:`genui.prompt.system_prompt` with this library."""
        from .prompt import system_prompt

        return system_prompt(self, **options)

    # ── validation (spec/prompt.md section 3.1) ──

    def issues(self) -> list[str]:
        """Every definition-time problem, as messages (empty list = valid)."""
        problems: list[str] = []
        spec = self._spec
        components = spec["components"]
        functions = spec.get("functions") or {}
        actions = spec.get("actions") or {}
        schema = spec.get("schema")
        defs = self._defs()

        seen: dict[str, str] = {}
        for kind, names in (
            ("Component", list(components)),
            ("Function", list(functions)),
            ("Action", list(actions)),
        ):
            for name in names:
                if not isinstance(name, str) or not _IDENT.match(name):
                    problems.append(f"{kind} name {name!r} is not an identifier ([A-Za-z_][A-Za-z0-9_]*).")
                elif not name[0].isupper() or not name[0].isascii():
                    problems.append(f"{kind} name {name!r} must start with an uppercase letter.")
                if name in RESERVED_NAMES:
                    problems.append(
                        f"{kind} {name!r} uses a reserved built-in name "
                        f"(built-ins, Action, Query and Mutation are reserved). Rename it."
                    )
                elif name in seen:
                    problems.append(f"{kind} {name!r} collides with the {seen[name].lower()} of the same name.")
                else:
                    seen[name] = kind

        for name, entry in components.items():
            if not isinstance(entry, Mapping) or not isinstance(entry.get("signature"), str):
                problems.append(f"components.{name} must be an object with a string signature.")
        for kind, table in (("functions", functions), ("actions", actions)):
            for name, entry in table.items():
                if not isinstance(entry, Mapping) or not isinstance(entry.get("signature"), str):
                    problems.append(f"{kind}.{name} must be an object with a string signature.")

        root = spec.get("root")
        if root is not None and (not isinstance(root, str) or root not in components):
            problems.append(
                f"Root component {root!r} was not found in components. "
                f"Available components: {', '.join(components)}."
            )
        for group in spec.get("componentGroups") or []:
            if (
                not isinstance(group, Mapping)
                or not isinstance(group.get("name"), str)
                or not isinstance(group.get("components"), list)
            ):
                problems.append(
                    "Each componentGroups entry must be {name: string, components: string[], notes?: string[]}."
                )
                continue
            for comp in group["components"]:
                if comp not in components:
                    problems.append(f"Component group {group['name']!r} references unknown component {comp!r}.")

        if schema is not None:
            for name in components:
                if self._component_schema(name) is None:
                    problems.append(f"Component {name!r} has no entry in schema.$defs.")
            for name in list(defs):
                _check_refs(defs[name], f"$defs/{name}", defs, problems)
            # Required props before optional ones (a required prop with a default counts as optional).
            for name in components:
                _check_order("Component", name, self._component_schema(name), problems)
            for kind, label in (("functions", "Function"), ("actions", "Action")):
                for name, entry in (schema.get(kind) or {}).items():
                    params = entry.get("params") if isinstance(entry, Mapping) else None
                    _check_order(label, name, params, problems)
                    if params is not None:
                        _check_refs(params, f"{kind}/{name}/params", defs, problems)
                    if kind == "actions" and isinstance(entry, Mapping) and "returns" in entry:
                        problems.append(f"Action {name!r} must not declare returns.")
        return problems

    def validate(self) -> None:
        """Raise :class:`LibraryError` listing every section 3.1 violation."""
        problems = self.issues()
        if problems:
            label = f"Library {self.id!r}" if self.id else "Library"
            bullet = "\n".join(f"  - {p}" for p in problems)
            raise LibraryError(f"{label} is invalid:\n{bullet}", problems)


def _build_signature(name: str, props: tuple[PropInfo, ...]) -> str:
    params = [f"{p.name}{'?' if p.optional else ''}: {p.type}" for p in props]
    return f"{name}({', '.join(params)})"


def _check_order(kind: str, name: str, params: Any, problems: list[str]) -> None:
    if not isinstance(params, Mapping):
        return
    props = params.get("properties")
    if not isinstance(props, Mapping):
        return
    required = params.get("required")
    seen_optional: str | None = None
    for prop, sub in props.items():
        if _optional(prop, sub, required):
            seen_optional = seen_optional or prop
        elif seen_optional is not None:
            problems.append(
                f"{kind} {name!r}: required prop {prop!r} comes after optional prop {seen_optional!r}. "
                f"Required props must come first (give it a default to add it at the end)."
            )
    if isinstance(required, list):
        for r in required:
            if r not in props:
                problems.append(f"{kind} {name!r} lists required prop {r!r} that is not in properties.")


def _check_refs(node: Any, path: str, defs: Mapping[str, Any], problems: list[str]) -> None:
    if isinstance(node, list):
        for i, item in enumerate(node):
            _check_refs(item, f"{path}/{i}", defs, problems)
        return
    if not isinstance(node, Mapping):
        return
    ref = node.get("$ref")
    if isinstance(ref, str):
        m = _REF.match(ref)
        if not m or m.group(1) not in defs:
            problems.append(f'Unresolvable $ref "{ref}" at {path}: refs must be "#/$defs/<name>" naming a $defs entry.')
    for key, value in node.items():
        if key != "$ref":
            _check_refs(value, f"{path}/{key}", defs, problems)
