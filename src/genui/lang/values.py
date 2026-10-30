"""Runtime value types: component instances, action plans, bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ast import AST


@dataclass
class Element:
    """A component instance: the type and its arguments mapped to named props.

    After parsing, props may still hold AST nodes (runtime expressions). After
    evaluation they hold plain values, nested elements, action plans, and
    bindings.
    """

    type_name: str
    props: dict[str, Any]
    #: the statement this component was bound to, if any
    statement_id: str | None = None
    #: True when parsed from input that needed implicit closing
    partial: bool = False


@dataclass
class ActionPlan:
    """An ``Action``: an ordered list of steps (language.md, section 6.3).

    Each step is a dict with a ``type``: ``run`` (``statementId``, ``refType``),
    ``continue_conversation`` (``message``, ``context``), ``open_url`` (``url``),
    ``set`` (``target``, ``valueAST``), ``reset`` (``targets``), or
    ``custom_action`` (``name``, ``params``).
    """

    steps: list[dict[str, Any]] = field(default_factory=list)


class CustomStep(dict):
    """A custom action step made by a real call (data can never pose as one)."""


@dataclass
class Binding:
    """A two-way binding of a bindable prop to ``$target`` (section 5.2)."""

    target: str
    expr: AST | None = None


def is_element(v: Any) -> bool:
    return isinstance(v, Element)
