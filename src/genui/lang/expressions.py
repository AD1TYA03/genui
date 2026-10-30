"""Pratt expression parser for OpenUI Lang (language.md, sections 1.5 and 1.6)."""

from __future__ import annotations

from ._js import number_to_string
from .ast import (
    AST, Arr, Assign, BinOp, Bool, Comp, Index, Member, Null, Num, Obj, Ref, StateRef, Str,
    Ternary, UnaryOp,
)
from .builtins import is_builtin
from .lexer import T, Token

PREC_TERNARY = 1
PREC_OR = 2
PREC_AND = 3
PREC_EQ = 4
PREC_CMP = 5
PREC_ADD = 6
PREC_MUL = 7
PREC_UNARY = 8
PREC_MEMBER = 9

_INFIX: dict[T, tuple[int, str]] = {
    T.QUESTION: (PREC_TERNARY, "?"),
    T.OR: (PREC_OR, "||"),
    T.AND: (PREC_AND, "&&"),
    T.EQEQ: (PREC_EQ, "=="),
    T.NOTEQ: (PREC_EQ, "!="),
    T.GT: (PREC_CMP, ">"),
    T.LT: (PREC_CMP, "<"),
    T.GTE: (PREC_CMP, ">="),
    T.LTE: (PREC_CMP, "<="),
    T.PLUS: (PREC_ADD, "+"),
    T.MINUS: (PREC_ADD, "-"),
    T.STAR: (PREC_MUL, "*"),
    T.SLASH: (PREC_MUL, "/"),
    T.PERCENT: (PREC_MUL, "%"),
    T.DOT: (PREC_MEMBER, "."),
    T.LBRACK: (PREC_MEMBER, "["),
}

_EOF = Token(T.EOF)


def key_text(tok: Token) -> str:
    """An object key or member field: names, strings, numbers, component names, ``$`` names."""
    if tok.t in (T.IDENT, T.TYPE, T.STR):
        return str(tok.v)
    if tok.t == T.NUM:
        return number_to_string(tok.v)
    if tok.t == T.STATE:
        return str(tok.v)[1:]
    return "?"


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def cur(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else _EOF

    def peek(self, k: int = 1) -> Token:
        i = self.pos + k
        return self.tokens[i] if i < len(self.tokens) else _EOF

    def adv(self) -> Token:
        tok = self.cur()
        self.pos += 1
        return tok

    def eat(self, t: T) -> None:
        if self.cur().t == t:
            self.pos += 1

    def expr(self, min_prec: int = 0) -> AST:
        left = self.prefix()
        while True:
            info = _INFIX.get(self.cur().t)
            if info is None or info[0] <= min_prec:
                break
            left = self.infix(left)
        return left

    def prefix(self) -> AST:
        tok = self.cur()
        t = tok.t
        if t == T.STR:
            self.adv()
            return Str(tok.v)
        if t == T.NUM:
            self.adv()
            return Num(tok.v)
        if t == T.TRUE:
            self.adv()
            return Bool(True)
        if t == T.FALSE:
            self.adv()
            return Bool(False)
        if t == T.NULL:
            self.adv()
            return Null()
        if t == T.LBRACK:
            return self.array()
        if t == T.LBRACE:
            return self.obj()
        if t == T.STATE:
            self.adv()
            if self.cur().t == T.EQUALS:
                self.adv()
                return Assign(tok.v, self.expr(0))
            return StateRef(tok.v)
        if t == T.TYPE:
            # Built-ins need the @ prefix; only Action works without it.
            if self.peek().t == T.LPAREN and (not is_builtin(tok.v) or tok.v == "Action"):
                return self.call()
            self.adv()
            return Ref(tok.v)
        if t == T.CALL:
            if self.peek().t == T.LPAREN:
                node = self.call()
                if not is_builtin(node.name):
                    node.fn = True
                return node
            self.adv()
            return Ref(tok.v)
        if t == T.IDENT:
            self.adv()
            return Ref(tok.v)
        if t == T.NOT:
            self.adv()
            return UnaryOp("!", self.expr(PREC_UNARY))
        if t == T.MINUS:
            self.adv()
            return UnaryOp("-", self.expr(PREC_UNARY))
        if t == T.LPAREN:
            self.adv()
            inner = self.expr(0)
            self.eat(T.RPAREN)
            return inner
        self.adv()  # unknown token: skip it
        return Null()

    def infix(self, left: AST) -> AST:
        tok = self.adv()
        prec, op = _INFIX[tok.t]
        if tok.t == T.QUESTION:
            then = self.expr(0)
            self.eat(T.COLON)
            return Ternary(left, then, self.expr(0))
        if tok.t == T.DOT:
            return Member(left, key_text(self.adv()))
        if tok.t == T.LBRACK:
            index = self.expr(0)
            self.eat(T.RBRACK)
            return Index(left, index)
        return BinOp(op, left, self.expr(prec))

    def call(self) -> Comp:
        name = self.adv().v
        self.eat(T.LPAREN)
        args: list[AST] = []
        while self.cur().t not in (T.RPAREN, T.EOF):
            args.append(self.expr(0))
            if self.cur().t == T.COMMA:
                self.adv()
        self.eat(T.RPAREN)
        return Comp(name, args)

    def array(self) -> Arr:
        self.adv()
        els: list[AST] = []
        while self.cur().t not in (T.RBRACK, T.EOF):
            els.append(self.expr(0))
            if self.cur().t == T.COMMA:
                self.adv()
        self.eat(T.RBRACK)
        return Arr(els)

    def obj(self) -> Obj:
        self.adv()
        entries: list[tuple[str, AST]] = []
        while self.cur().t not in (T.RBRACE, T.EOF):
            key = key_text(self.adv())
            self.eat(T.COLON)
            entries.append((key, self.expr(0)))
            if self.cur().t == T.COMMA:
                self.adv()
        self.eat(T.RBRACE)
        return Obj(entries)


def parse_expression(tokens: list[Token]) -> AST:
    """Parse expression tokens into an AST. Trailing tokens are ignored."""
    return _Parser(tokens).expr(0)
