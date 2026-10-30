"""OpenUI Lang 1.0: parser, program model, evaluation, and validation.

A community Python implementation of the language in ``spec/language.md``
(not affiliated with Thesys). Standard library only. Behaviour follows the
TypeScript reference where it differs from the spec prose; see ``COMPAT.md``.

Quick start::

    from genui.lang import parse, summarize

    result = parse('root = Stack([Text("Hi")])', library_spec)
    summarize(result)["root"]
    # {"type": "Stack", "props": {"children": [{"type": "Text", "props": {"text": "Hi"}}]}}

Streaming::

    sp = StreamParser(library_spec)
    for chunk in chunks:
        snapshot = sp.feed(chunk)
    final = sp.end()      # equals parse("".join(chunks), library_spec), see COMPAT.md
"""

from .errors import OpenUIError
from .library import CompiledLibrary, CustomFunction, compile_library
from .merge import merge
from .parser import (
    Evaluation,
    MutationStatement,
    ParseResult,
    QueryStatement,
    Statement,
    StreamParser,
    parse,
)
from .rules import check_rules
from .serialize import serialize
from .source import preprocess
from .summarize import summarize, summarize_value
from .values import ActionPlan, Binding, Element

__all__ = [
    "parse",
    "StreamParser",
    "ParseResult",
    "Evaluation",
    "summarize",
    "summarize_value",
    "merge",
    "serialize",
    "check_rules",
    "compile_library",
    "preprocess",
    "CompiledLibrary",
    "CustomFunction",
    "OpenUIError",
    "Element",
    "ActionPlan",
    "Binding",
    "Statement",
    "QueryStatement",
    "MutationStatement",
]
