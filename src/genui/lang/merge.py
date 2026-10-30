"""Incremental editing: merge an edit-mode reply into a program (language.md, section 7)."""

from __future__ import annotations

from .ast import AST, Node, Null, Ref, RuntimeRef, walk
from .parser import ROOT_ID, Statement, statements_from
from .source import preprocess, scan_boundaries


def _read(text: str) -> list[Statement]:
    """Statements of a text, read with sections 1.2 and 1.4 (fences, comments, ternaries)."""
    cleaned = preprocess(text)
    if not cleaned:
        return []
    spans, _ = scan_boundaries(cleaned, 0, final=True)
    out: list[Statement] = []
    for a, b in spans:
        out.extend(statements_from(cleaned[a:b], a, cleaned))
    return out


def _refs(node: AST) -> set[str]:
    names: set[str] = set()

    def visit(n: Node) -> None:
        if isinstance(n, (Ref, RuntimeRef)):
            names.add(n.n)

    walk(node, visit)
    return names


def merge(previous: str, patch: str) -> str:
    """Merge ``patch`` (the model's edit reply) into ``previous`` by statement name.

    A patch statement replaces the statement of the same name, or is appended.
    A top-level ``name = null`` deletes the statement (state declarations
    included). Afterwards, statements ``root`` cannot reach are removed unless
    there is no ``root`` statement; state declarations are always kept. If the
    reply is prose plus a fenced patch, only the fenced part is merged. Returns
    the merged program text.
    """
    patch_stmts = _read(patch)
    if not patch_stmts:
        return previous
    order: list[str] = []
    texts: dict[str, str] = {}
    asts: dict[str, AST] = {}
    for s in _read(previous):
        if s.id not in texts:
            order.append(s.id)
        texts[s.id] = s.text
        asts[s.id] = s.expr
    for s in patch_stmts:
        if isinstance(s.expr, Null):
            if s.id in texts:
                order.remove(s.id)
                del texts[s.id]
                del asts[s.id]
            continue
        if s.id not in texts:
            order.append(s.id)
        texts[s.id] = s.text
        asts[s.id] = s.expr

    if ROOT_ID in asts:
        reachable = {ROOT_ID}
        queue = [ROOT_ID]
        while queue:
            for ref in _refs(asts[queue.pop()]):
                if ref not in reachable and ref in asts:
                    reachable.add(ref)
                    queue.append(ref)
        order = [sid for sid in order if sid in reachable or sid.startswith("$")]

    return "\n".join(texts[sid] for sid in order)
