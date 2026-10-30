"""Lexer for OpenUI Lang (language.md, section 1.3). Lexing never fails."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from ._js import norm_num


class T(IntEnum):
    NEWLINE = 0
    LPAREN = 1
    RPAREN = 2
    LBRACK = 3
    RBRACK = 4
    LBRACE = 5
    RBRACE = 6
    COMMA = 7
    COLON = 8
    EQUALS = 9
    TRUE = 10
    FALSE = 11
    NULL = 12
    EOF = 13
    STR = 14
    NUM = 15
    IDENT = 16  # lowercase or _ identifier: a reference
    TYPE = 17  # uppercase identifier: a component name or reference
    STATE = 18  # $name
    DOT = 19
    PLUS = 20
    MINUS = 21
    STAR = 22
    SLASH = 23
    PERCENT = 24
    EQEQ = 25
    NOTEQ = 26
    GT = 27
    LT = 28
    GTE = 29
    LTE = 30
    AND = 31
    OR = 32
    NOT = 33
    QUESTION = 34
    CALL = 35  # @name


@dataclass(slots=True)
class Token:
    t: T
    v: Any = None
    start: int = 0
    end: int = 0


_SINGLE = {
    "(": T.LPAREN, ")": T.RPAREN, "[": T.LBRACK, "]": T.RBRACK, "{": T.LBRACE, "}": T.RBRACE,
    ",": T.COMMA, ":": T.COLON, ".": T.DOT, "?": T.QUESTION, "+": T.PLUS, "*": T.STAR,
    "/": T.SLASH, "%": T.PERCENT,
}

_VALUE_TOKENS = frozenset({
    T.NUM, T.STR, T.IDENT, T.TYPE, T.RPAREN, T.RBRACK, T.TRUE, T.FALSE, T.NULL, T.STATE, T.CALL,
})


def _is_alpha(c: str) -> bool:
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def _is_digit(c: str) -> bool:
    return "0" <= c <= "9"


def _is_word(c: str) -> bool:
    return _is_alpha(c) or _is_digit(c)


def _decode_double(raw: str, closed: bool) -> str:
    text = raw if closed else raw + '"'
    try:
        value = json.loads(text, strict=False)
        if isinstance(value, str):
            return value
    except ValueError:
        pass
    # Malformed escape (e.g. a partly received \u): keep the raw text.
    s = raw
    if s.startswith('"'):
        s = s[1:]
    if s.endswith('"'):
        s = s[:-1]
    return s


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(src)
    push = tokens.append

    while i < n:
        while i < n and src[i] in " \t\r":
            i += 1
        if i >= n:
            break
        c = src[i]
        start = i

        if c == "\n":
            push(Token(T.NEWLINE, None, i, i + 1))
            i += 1
            continue

        if c in _SINGLE:
            push(Token(_SINGLE[c], None, i, i + 1))
            i += 1
            continue

        if c == "=":
            if i + 1 < n and src[i + 1] == "=":
                push(Token(T.EQEQ, None, i, i + 2))
                i += 2
            else:
                push(Token(T.EQUALS, None, i, i + 1))
                i += 1
            continue
        if c == "!":
            if i + 1 < n and src[i + 1] == "=":
                push(Token(T.NOTEQ, None, i, i + 2))
                i += 2
            else:
                push(Token(T.NOT, None, i, i + 1))
                i += 1
            continue
        if c == ">":
            if i + 1 < n and src[i + 1] == "=":
                push(Token(T.GTE, None, i, i + 2))
                i += 2
            else:
                push(Token(T.GT, None, i, i + 1))
                i += 1
            continue
        if c == "<":
            if i + 1 < n and src[i + 1] == "=":
                push(Token(T.LTE, None, i, i + 2))
                i += 2
            else:
                push(Token(T.LT, None, i, i + 1))
                i += 1
            continue
        if c == "&":
            j = i + 2 if i + 1 < n and src[i + 1] == "&" else i + 1
            push(Token(T.AND, None, i, j))
            i = j
            continue
        if c == "|":
            j = i + 2 if i + 1 < n and src[i + 1] == "|" else i + 1
            push(Token(T.OR, None, i, j))
            i = j
            continue

        if c == '"':
            i += 1
            closed = False
            while i < n:
                if src[i] == "\\":
                    i += 2
                elif src[i] == '"':
                    i += 1
                    closed = True
                    break
                else:
                    i += 1
            i = min(i, n)
            push(Token(T.STR, _decode_double(src[start:i], closed), start, i))
            continue

        if c == "'":
            i += 1
            out: list[str] = []
            while i < n:
                ch = src[i]
                if ch == "\\":
                    i += 1
                    if i < n:
                        esc = src[i]
                        out.append({"'": "'", "\\": "\\", "n": "\n", "t": "\t"}.get(esc, esc))
                        i += 1
                elif ch == "'":
                    i += 1
                    break
                else:
                    out.append(ch)
                    i += 1
            push(Token(T.STR, "".join(out), start, i))
            continue

        if c == "-":
            prev = tokens[-1] if tokens else None
            after_value = prev is not None and prev.t in _VALUE_TOKENS
            if after_value or not (i + 1 < n and _is_digit(src[i + 1])):
                push(Token(T.MINUS, None, i, i + 1))
                i += 1
                continue

        if _is_digit(c) or (c == "-" and i + 1 < n and _is_digit(src[i + 1])):
            if src[i] == "-":
                i += 1
            while i < n and _is_digit(src[i]):
                i += 1
            if i < n and src[i] == "." and i + 1 < n and _is_digit(src[i + 1]):
                i += 1
                while i < n and _is_digit(src[i]):
                    i += 1
            if i < n and src[i] in "eE":
                i += 1
                if i < n and src[i] in "+-":
                    i += 1
                while i < n and _is_digit(src[i]):
                    i += 1
            text = src[start:i]
            try:
                value: float | int = norm_num(float(text))
            except ValueError:
                value = math.nan  # dangling exponent: implementation-defined
            push(Token(T.NUM, value, start, i))
            continue

        if c == "$" and i + 1 < n and _is_alpha(src[i + 1]):
            i += 1
            while i < n and _is_word(src[i]):
                i += 1
            push(Token(T.STATE, src[start:i], start, i))
            continue

        if _is_alpha(c):
            while i < n and _is_word(src[i]):
                i += 1
            word = src[start:i]
            if word == "true":
                push(Token(T.TRUE, None, start, i))
            elif word == "false":
                push(Token(T.FALSE, None, start, i))
            elif word == "null":
                push(Token(T.NULL, None, start, i))
            else:
                push(Token(T.TYPE if "A" <= c <= "Z" else T.IDENT, word, start, i))
            continue

        if c == "@" and i + 1 < n and _is_alpha(src[i + 1]):
            i += 1
            s = i
            while i < n and _is_word(src[i]):
                i += 1
            push(Token(T.CALL, src[s:i], start, i))
            continue

        i += 1  # any other character is skipped

    tokens.append(Token(T.EOF, None, n, n))
    return tokens
