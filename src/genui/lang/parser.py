"""Batch and streaming parsing (language.md, sections 2 and 4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .ast import AST, Comp, Node, Ref, StateRef, is_ast, walk
from .builtins import is_builtin, is_reserved_call
from .errors import OpenUIError
from .evaluator import EvalContext, evaluate, evaluate_prop, evaluate_root
from .expressions import parse_expression
from .lexer import T
from .library import CompiledLibrary, CustomFunction, compile_library
from .materialize import MaterializeCtx, materialize_value, name_raw_call_args
from .source import RawStatement, autoclose, preprocess, scan_boundaries, split_statements
from .validation import push_issue
from .values import Element

ROOT_ID = "root"


# ─── statements ────────────────────────────────────────────────────────────


@dataclass
class Statement:
    """A classified statement (section 2.1): ``value``, ``state``, ``query``, or ``mutation``."""

    kind: str
    id: str
    expr: AST
    #: source text of the statement in the prepared program
    text: str = ""


@dataclass
class QueryStatement:
    statement_id: str
    tool: AST | None
    args: AST | None
    defaults: AST | None
    refresh: AST | None
    #: ``$variables`` written literally in the args (refetch triggers, section 6.1)
    deps: list[str] = field(default_factory=list)


@dataclass
class MutationStatement:
    statement_id: str
    tool: AST | None
    args: AST | None


def state_refs(node: Any) -> list[str]:
    """Every ``$name`` read in an AST, in first-seen order."""
    if not is_ast(node):
        return []
    seen: dict[str, None] = {}

    def visit(n: Node) -> None:
        if isinstance(n, StateRef):
            seen.setdefault(n.n, None)

    walk(node, visit)
    return list(seen)


def classify(raw: RawStatement, expr: AST, text: str = "") -> Statement:
    if isinstance(expr, Comp) and expr.name == "Query":
        return Statement("query", raw.id, expr, text)
    if isinstance(expr, Comp) and expr.name == "Mutation":
        return Statement("mutation", raw.id, expr, text)
    if raw.id_type == T.STATE:
        return Statement("state", raw.id, expr, text)
    return Statement("value", raw.id, expr, text)


def statements_from(segment: str, offset: int, source: str) -> list[Statement]:
    out = []
    for raw in split_statements(segment, offset):
        out.append(classify(raw, parse_expression(raw.tokens), source[raw.start:raw.end]))
    return out


# ─── result ────────────────────────────────────────────────────────────────


@dataclass
class Evaluation:
    """An evaluated program: the rendered tree and the runtime errors."""

    root: Element | None
    errors: list[OpenUIError]


@dataclass
class ParseResult:
    """The result of parsing a program (or the current snapshot of a stream).

    ``root`` is the parsed entry tree: an :class:`Element` whose props may still
    hold runtime expressions. Call :meth:`evaluate` for concrete values, or
    :func:`genui.lang.summarize` for the canonical JSON.
    """

    root: Element | None
    errors: list[OpenUIError]
    unresolved: list[str]
    orphans: list[str]
    incomplete: bool
    #: state defaults, ``{"$name": value}``
    state: dict[str, Any]
    #: statement names in program order
    statements: list[str]
    queries: list[QueryStatement] = field(default_factory=list)
    mutations: list[MutationStatement] = field(default_factory=list)
    #: set when the entry picks a component at runtime (``root = $t ? A : B``)
    root_expression: AST | None = None
    #: the entry statement id (``root``, the fallback statement, or None)
    entry: str | None = None
    #: the classified statements, by name
    statement_map: dict[str, Statement] = field(default_factory=dict, repr=False)
    library: CompiledLibrary | None = field(default=None, repr=False)

    def evaluate(
        self,
        state: Mapping[str, Any] | None = None,
        queries: Mapping[str, Any] | None = None,
        mutations: Mapping[str, Any] | None = None,
    ) -> Evaluation:
        """Evaluate the tree.

        ``state`` overrides the defaults. ``queries`` maps a query id to its
        latest result (default: the query's defaults, as before the first
        fetch). ``mutations`` maps a mutation id to ``{status, data, error}``
        (default: idle).
        """
        ctx = self.eval_context(state, queries, mutations)
        errors: list[OpenUIError] = []
        tree = evaluate_root(self.root, self.root_expression, ctx, errors, self.entry or ROOT_ID)
        return Evaluation(tree, errors)

    def eval_context(
        self,
        state: Mapping[str, Any] | None = None,
        queries: Mapping[str, Any] | None = None,
        mutations: Mapping[str, Any] | None = None,
    ) -> EvalContext:
        """The evaluation context :meth:`evaluate` uses (see there for the arguments)."""
        store: dict[str, Any] = dict(self.state)
        if state:
            store.update(state)
        query_ids = {q.statement_id: q for q in self.queries}
        mutation_ids = {m.statement_id for m in self.mutations}
        ctx: EvalContext
        resolving: set[str] = set()

        def resolve(name: str) -> Any:
            if queries is not None and name in queries:
                return queries[name]
            q = query_ids.get(name)
            if q is not None:
                if q.defaults is None or name in resolving:
                    return None  # a query's defaults that read the query itself are null
                resolving.add(name)
                try:
                    return evaluate(q.defaults, ctx)
                finally:
                    resolving.discard(name)
            if name in mutation_ids:
                if mutations is not None and name in mutations:
                    return mutations[name]
                return {"status": "idle", "data": None, "error": None}
            return None

        ctx = EvalContext(get_state=lambda n: store.get(n), resolve_ref=resolve, lib=self.library)
        return ctx


def _empty(lib: CompiledLibrary, incomplete: bool, errors: list[OpenUIError] | None = None) -> ParseResult:
    return ParseResult(None, errors or [], [], [], incomplete, {}, [], library=lib)


def _is_component_call(node: Any) -> bool:
    return (isinstance(node, Comp) and not node.fn and not is_builtin(node.name)
            and not is_reserved_call(node.name))


def _pick_entry(stmts: dict[str, Statement], root_name: str | None) -> tuple[str, bool] | None:
    if ROOT_ID in stmts:
        return ROOT_ID, False
    if root_name is None:
        return None
    for s in stmts.values():
        if s.kind == "value" and _is_component_call(s.expr) and s.expr.name == root_name:
            return s.id, True
    return None


def _resolves_to_component_call(node: Any, syms: dict[str, AST]) -> bool:
    seen: set[str] = set()
    while isinstance(node, Ref) and node.n not in seen:
        seen.add(node.n)
        node = syms.get(node.n)
    return _is_component_call(node)


def _contains_component(node: AST) -> bool:
    found = [False]

    def visit(n: Node) -> None:
        if _is_component_call(n):
            found[0] = True

    walk(node, visit)
    return found[0]


def _plain_default(value: Any, lib: CompiledLibrary) -> Any:
    """A state default is a plain value: any expression or component in it is
    evaluated once, with no state set yet."""
    ctx = EvalContext(get_state=lambda n: None, resolve_ref=lambda n: None, lib=lib)
    try:
        return evaluate_prop(value, ctx, False, None)
    except Exception:
        return None


def build_result(
    stmts: dict[str, Statement],
    incomplete: bool,
    lib: CompiledLibrary,
    partial_ref: tuple[str, set[int]] | None = None,
) -> ParseResult:
    entry = _pick_entry(stmts, lib.root)
    entry_id = entry[0] if entry else None
    syms: dict[str, AST] = {sid: s.expr for sid, s in stmts.items()}
    unreached = {sid for sid, s in stmts.items() if sid != entry_id and s.kind == "value"}
    ctx = MaterializeCtx(
        partial=incomplete,
        current_statement_id=entry_id,
        components=lib.components,
        syms=syms,
        lib=lib,
        unreached=unreached,
    )

    root: Element | None = None
    root_expression: AST | None = None
    if entry_id is not None:
        materialized = materialize_value(syms[entry_id], ctx)
        if isinstance(materialized, Element):
            root = materialized
            root.statement_id = entry_id
        elif is_ast(materialized) and _contains_component(materialized):
            root_expression = materialized

    state: dict[str, Any] = {}
    queries: list[QueryStatement] = []
    mutations: list[MutationStatement] = []
    for s in stmts.values():
        if s.kind == "state":
            state[s.id] = _plain_default(materialize_value(s.expr, ctx), lib)
        elif s.kind == "query":
            args = s.expr.args
            name_raw_call_args(args, ctx, s.id)
            queries.append(QueryStatement(
                s.id,
                args[0] if len(args) > 0 else None,
                args[1] if len(args) > 1 else None,
                args[2] if len(args) > 2 else None,
                args[3] if len(args) > 3 else None,
                state_refs(args[1]) if len(args) > 1 else [],
            ))
        elif s.kind == "mutation":
            args = s.expr.args
            name_raw_call_args(args, ctx, s.id)
            mutations.append(MutationStatement(
                s.id, args[0] if len(args) > 0 else None, args[1] if len(args) > 1 else None,
            ))

    # Auto-declare: a $name read anywhere but not declared gets the default null.
    for s in stmts.values():
        nodes = s.expr.args if s.kind in ("query", "mutation") else [s.expr]
        for node in nodes:
            for dep in state_refs(node):
                if partial_ref and dep == partial_ref[0] and id(s) in partial_ref[1]:
                    continue
                state.setdefault(dep, None)

    # Entry checks happen at stream end (streaming consumers drop parser errors until then).
    ctx.current_statement_id = entry_id
    component = lib.root or ""
    if entry is None:
        msg = (f"No root statement, and no statement calls the root component {component}"
               if component else "No root statement")
        push_issue(ctx, component, "", "no-root", msg,
                   f"Add a statement `root = {component or 'Component'}(...)`")
    elif root is None and root_expression is None and not _resolves_to_component_call(syms[entry_id], syms):
        push_issue(ctx, component, "", "no-root", "root does not evaluate to a component",
                   "Make root a component call")
    elif entry[1]:
        if root is not None:
            push_issue(ctx, component, "", "no-root",
                       f"No root statement. Rendering the first statement that calls the root "
                       f"component {component}",
                       "Name the entry statement `root`", severity="warning")
        else:
            push_issue(ctx, component, "", "no-root",
                       f"No root statement, and no statement calls the root component {component}",
                       f"Add a statement `root = {component}(...)`")

    return ParseResult(
        root=root,
        errors=ctx.errors,
        unresolved=ctx.unres,
        orphans=list(unreached) if entry is not None else [],
        incomplete=incomplete,
        state=state,
        statements=list(stmts),
        queries=queries,
        mutations=mutations,
        root_expression=root_expression,
        entry=entry_id,
        statement_map=dict(stmts),
        library=lib,
    )


def _parse_failed(lib: CompiledLibrary, incomplete: bool) -> ParseResult:
    err = OpenUIError(
        source="parser", code="parse-failed",
        message="The response has text but yields no statements",
        hint="Write statements of the form `name = expression`, starting with `root = ...`",
    )
    return _empty(lib, incomplete, [err])


def _parse_exception(lib: CompiledLibrary, exc: Exception) -> ParseResult:
    err = OpenUIError(source="parser", code="parse-exception",
                      message=f"The parser failed: {type(exc).__name__}: {exc}")
    return _empty(lib, False, [err])


# ─── batch ─────────────────────────────────────────────────────────────────


def parse(
    source: str,
    library: Mapping[str, Any] | CompiledLibrary,
    functions: Mapping[str, CustomFunction] | None = None,
) -> ParseResult:
    """Parse a complete program (the stream has ended).

    ``library`` is a LibrarySpec dict (or a :class:`CompiledLibrary`).
    ``functions`` supplies the library's custom functions, keyed by name; each
    receives one dict keyed by the param names.
    """
    lib = compile_library(library, functions)
    try:
        return _parse_prepared(preprocess(source), lib)
    except Exception as exc:  # the parser must never crash the host
        return _parse_exception(lib, exc)


def _parse_prepared(cleaned: str, lib: CompiledLibrary) -> ParseResult:
    if not cleaned:
        return _empty(lib, False)
    spans, pending = scan_boundaries(cleaned, 0, final=True)
    stmts: dict[str, Statement] = {}
    incomplete = False
    count = 0
    for i, (a, b) in enumerate(spans):
        segment = cleaned[a:b]
        if i == len(spans) - 1:
            closed, incomplete = autoclose(segment)
            src = cleaned[:a] + closed
            parsed = statements_from(closed, a, src)
        else:
            parsed = statements_from(segment, a, cleaned)
        for s in parsed:
            stmts[s.id] = s
            count += 1
    if not stmts:
        return _parse_failed(lib, incomplete)
    return build_result(stmts, incomplete, lib)


# ─── streaming ─────────────────────────────────────────────────────────────

_TAIL_STATE_RE = re.compile(r"\$\w+\Z")


class StreamParser:
    """Parse a program a chunk at a time (language.md, section 4).

    ``feed`` returns the current snapshot after each chunk; ``end`` finalizes the
    stream. The result at the end equals :func:`parse` of the joined chunks.
    Feeding after ``end`` starts a new stream.
    """

    def __init__(
        self,
        library: Mapping[str, Any] | CompiledLibrary,
        functions: Mapping[str, CustomFunction] | None = None,
    ) -> None:
        self.library = compile_library(library, functions)
        self._reset()

    def _reset(self) -> None:
        self._buf = ""
        self._cleaned = ""
        self._completed_end = 0
        self._completed: dict[str, Statement] = {}
        self._ended = False

    @property
    def text(self) -> str:
        """The raw text received so far."""
        return self._buf

    def feed(self, chunk: str) -> ParseResult:
        if self._ended:
            self._reset()
        self._buf += chunk
        return self._result(False)

    def end(self) -> ParseResult:
        """Signal the end of the stream and return the final result."""
        result = self._result(True)
        self._ended = True
        return result

    def result(self) -> ParseResult:
        """The current snapshot, without consuming new data."""
        return self._result(self._ended)

    def _refresh(self) -> None:
        nxt = preprocess(self._buf)
        if not nxt.startswith(self._cleaned[: self._completed_end]):
            self._completed_end = 0
            self._completed.clear()
        self._cleaned = nxt

    def _result(self, complete: bool) -> ParseResult:
        lib = self.library
        try:
            return self._result_inner(complete)
        except Exception as exc:  # the parser must never crash the host
            return _parse_exception(lib, exc)

    def _result_inner(self, complete: bool) -> ParseResult:
        lib = self.library
        self._refresh()
        cleaned = self._cleaned
        spans, _ = scan_boundaries(cleaned, self._completed_end, final=False)
        for a, b in spans:
            for s in statements_from(cleaned[a:b], a, cleaned):
                self._completed[s.id] = s
            self._completed_end = b + 1
        pending_start = self._completed_end
        pending = cleaned[pending_start:]
        if not pending.strip():
            if not self._completed:
                return _parse_failed(lib, False) if complete and cleaned else _empty(lib, False)
            return build_result(self._completed, False, lib)

        lead = len(pending) - len(pending.lstrip())
        body = pending.strip()
        closed, incomplete = autoclose(body)
        offset = pending_start + lead
        src = cleaned[:offset] + closed
        parsed = statements_from(closed, offset, src)
        if not parsed:
            if not self._completed:
                return _parse_failed(lib, incomplete) if complete else _empty(lib, incomplete)
            return build_result(self._completed, incomplete, lib)

        merged = dict(self._completed)
        pending_ids: set[int] = set()
        for s in parsed:
            # A pending statement that needed implicit closing never replaces a completed one.
            if s.id in self._completed and incomplete and not complete:
                continue
            merged[s.id] = s
            pending_ids.add(id(s))

        partial_ref = None
        if not complete:
            m = _TAIL_STATE_RE.search(self._buf)
            if m:
                tail = m.group(0)
                earlier = body[: -len(tail)] if body.endswith(tail) else None
                if earlier is not None and not re.search(re.escape(tail) + r"(?!\w)", earlier):
                    partial_ref = (tail, pending_ids)
        return build_result(merged, incomplete, lib, partial_ref)
