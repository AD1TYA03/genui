"""Incremental editing: merge an edit-mode reply into a program (language.md, section 7).

Ported from the reference (``parser/merge.ts`` ``mergeStatements``) so the
merged text is byte-identical to what the TypeScript client produces.
"""

from __future__ import annotations

from .ast import AST, Node, Null, Ref, RuntimeRef, walk
from .expressions import parse_expression
from .source import split_statement_source, split_statements, strip_fences


def _parse_statements(text: str) -> list[tuple[str, AST, str]]:
    """``(id, ast, raw)`` per statement chunk; only the first statement of a chunk counts."""
    trimmed = text.strip()
    if not trimmed:
        return []
    out = []
    for raw in split_statement_source(trimmed):
        stmts = split_statements(raw)
        if not stmts:
            continue
        out.append((stmts[0].id, parse_expression(stmts[0].tokens), raw))
    return out


def _refs(node: AST) -> set[str]:
    names: set[str] = set()

    def visit(n: Node) -> None:
        if isinstance(n, (Ref, RuntimeRef)):
            names.add(n.n)

    walk(node, visit)
    return names


def merge(previous: str, patch: str, root_id: str = "root") -> str:
    """Merge ``patch`` (the model's edit reply) into ``previous`` by statement name.

    A patch statement replaces the statement of the same name, or is appended.
    A top-level ``name = null`` deletes the statement. Afterwards, statements
    ``root`` cannot reach are removed unless there is no ``root`` statement;
    state declarations are always kept. Fenced parts of the reply are used when
    it has fences. Returns the merged program text.
    """
    existing = _parse_statements(previous)
    patch_stmts = _parse_statements(strip_fences(patch))
    if not existing:
        return "\n".join(raw for _, _, raw in patch_stmts)
    if not patch_stmts:
        return previous

    merged: dict[str, str] = {}
    asts: dict[str, AST] = {}
    order: list[str] = []
    for sid, ast, raw in existing:
        merged[sid] = raw
        asts[sid] = ast
        order.append(sid)
    for sid, ast, raw in patch_stmts:
        if isinstance(ast, Null):
            merged.pop(sid, None)
            asts.pop(sid, None)
            if sid in order:
                order.remove(sid)  # first occurrence, as Array.splice(indexOf) does
            continue
        if sid not in merged:
            order.append(sid)
        merged[sid] = raw
        asts[sid] = ast

    if root_id in asts:
        reachable = {root_id}
        queue = [root_id]
        while queue:
            ast = asts.get(queue.pop())
            if ast is None:
                continue
            for ref in _refs(ast):
                if ref not in reachable and ref in asts:
                    reachable.add(ref)
                    queue.append(ref)
        reachable.update(sid for sid in order if sid.startswith("$"))
        order = [sid for sid in order if sid in reachable]
        for sid in list(merged):
            if sid not in reachable:
                del merged[sid]

    return "\n".join(merged[sid] for sid in order if sid in merged)
