"""Source preparation and statement boundaries (language.md, sections 1.2, 1.4, 4).

The batch parser, the streaming parser, and the edit merge all find statement
boundaries with :func:`scan_boundaries`, so they agree byte for byte.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lexer import T, Token, tokenize

_OPEN = {")": "(", "]": "[", "}": "{"}
_CLOSE = {"(": ")", "[": "]", "{": "}"}
_WS = " \t\r\n"


# ─── 1.2 Fence extraction ──────────────────────────────────────────────────


def _skip_double_string(text: str, i: int) -> int:
    """Index after the double-quoted string starting at ``i`` (or the end of text)."""
    n = len(text)
    i += 1
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
        elif c == '"':
            return i + 1
        else:
            i += 1
    return n


def strip_fences(text: str) -> str:
    """Join the contents of every fence; return ``text`` unchanged when it has none.

    A fence opens only with three backticks at the start of a line. Inside a
    fence, backticks within double-quoted strings do not close it. An
    unterminated fence runs to the end of the text.
    """
    blocks: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        # find an opener at the start of a line; prose quotes shield nothing
        opener = -1
        j = i
        while j < n:
            if (j == 0 or text[j - 1] == "\n") and text.startswith("```", j):
                opener = j
                break
            nl = text.find("\n", j)
            if nl == -1:
                break
            j = nl + 1
        if opener == -1:
            break
        nl = text.find("\n", opener + 3)
        if nl == -1:
            blocks.append("")  # the language tag line has not ended yet
            break
        body_start = nl + 1
        k = body_start
        close = -1
        while k < n:
            c = text[k]
            if c == '"':
                k = _skip_double_string(text, k)
                continue
            if c == "`" and text.startswith("```", k):
                close = k
                break
            k += 1
        if close == -1:
            blocks.append(text[body_start:])
            break
        blocks.append(text[body_start:close])
        i = close + 3
    if blocks:
        return "\n".join(blocks)
    return text


# ─── 1.2 Comment stripping ─────────────────────────────────────────────────


def strip_comments(text: str) -> str:
    """Remove ``//`` and ``#`` comments outside strings, even multi-line strings."""
    in_str: str | None = None
    out_lines: list[str] = []
    for line in text.split("\n"):
        cut = None
        i = 0
        n = len(line)
        while i < n:
            c = line[i]
            if in_str:
                if c == "\\" and i + 1 < n:
                    i += 2
                    continue
                if c == in_str:
                    in_str = None
                i += 1
                continue
            if c == '"' or c == "'":
                in_str = c
            elif c == "/" and i + 1 < n and line[i + 1] == "/":
                cut = i
                break
            elif c == "#":
                cut = i
                break
            i += 1
        out_lines.append(line if cut is None else line[:cut].rstrip())
    return "\n".join(out_lines)


def preprocess(text: str) -> str:
    """Fence extraction, comment stripping, trimming (section 1.2)."""
    return strip_comments(strip_fences(text.strip())).strip()


# ─── 4.2 Implicit closing ──────────────────────────────────────────────────


def autoclose(text: str) -> tuple[str, bool]:
    """Close an unterminated string (adding ``\\`` first when the text ends
    mid-escape), then unclosed brackets in reverse order. A closing bracket that
    does not match is skipped. Returns ``(text, was_incomplete)``."""
    stack: list[str] = []
    in_str: str | None = None
    esc = False
    for c in text:
        if esc:
            esc = False
            continue
        if in_str:
            if c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
            continue
        if c == '"' or c == "'":
            in_str = c
        elif c in _CLOSE:
            stack.append(c)
        elif c in _OPEN and stack and stack[-1] == _OPEN[c]:
            stack.pop()
    incomplete = in_str is not None or bool(stack)
    if not incomplete:
        return text, False
    out = text
    if in_str:
        if esc:
            out += "\\"
        out += in_str
    for opener in reversed(stack):
        out += _CLOSE[opener]
    return out, True


# ─── 1.4 Statement boundaries ──────────────────────────────────────────────


def scan_boundaries(text: str, start: int = 0, final: bool = True) -> tuple[list[tuple[int, int]], int]:
    """Find statement boundaries in prepared text, from ``start`` (a boundary).

    A newline ends a statement only at bracket depth zero, outside strings, with
    no open ternary, and when the next line's first non-whitespace character is
    not ``?``. A ternary is open from its ``?`` until the first operand after its
    matching ``:`` has started.

    With ``final=False`` (streaming), a newline whose lookahead has not arrived
    yet is not a boundary. Returns the completed ``(start, end)`` spans and the
    start of the pending tail.
    """
    spans: list[tuple[int, int]] = []
    stack: list[str] = []
    in_str: str | None = None
    esc = False
    ternary = 0
    else_empty = False
    seg = start
    n = len(text)
    i = start
    while i < n:
        c = text[i]
        if esc:
            esc = False
            i += 1
            continue
        if in_str:
            if c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
            i += 1
            continue
        if c == "\n":
            if not stack and ternary == 0 and not else_empty:
                peek = i + 1
                while peek < n and text[peek] in _WS:
                    peek += 1
                if peek >= n and not final:
                    return spans, seg  # the lookahead has not arrived
                if peek < n and text[peek] == "?":
                    i += 1
                    continue
                spans.append((seg, i))
                seg = i + 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == ":" and not stack and ternary > 0:
            ternary -= 1
            else_empty = True
            i += 1
            continue
        else_empty = False
        if c == '"' or c == "'":
            in_str = c
        elif c in _CLOSE:
            stack.append(c)
        elif c in _OPEN:
            if stack and stack[-1] == _OPEN[c]:
                stack.pop()
        elif c == "?" and not stack:
            ternary += 1
        i += 1
    if final and seg < n:
        spans.append((seg, n))
        seg = n
    return spans, seg


@dataclass
class RawStatement:
    id: str
    id_type: T
    tokens: list[Token]
    #: offsets of the statement text (name through last expression token)
    start: int
    end: int


def split_statements(text: str, offset: int = 0) -> list[RawStatement]:
    """Split one segment into ``name = expression`` statements.

    A line without that shape is skipped without an error, up to its next
    newline token.
    """
    tokens = tokenize(text)
    out: list[RawStatement] = []
    pos = 0
    ntok = len(tokens)
    while pos < ntok:
        while pos < ntok and tokens[pos].t == T.NEWLINE:
            pos += 1
        if pos >= ntok or tokens[pos].t == T.EOF:
            break
        tok = tokens[pos]
        if tok.t not in (T.IDENT, T.TYPE, T.STATE) or tokens[pos + 1].t != T.EQUALS:
            while pos < ntok and tokens[pos].t not in (T.NEWLINE, T.EOF):
                pos += 1
            continue
        pos += 2
        expr: list[Token] = []
        stack: list[T] = []
        ternary = 0
        else_empty = False
        while pos < ntok and tokens[pos].t != T.EOF:
            tt = tokens[pos].t
            if tt == T.NEWLINE:
                if not stack and ternary == 0 and not else_empty:
                    peek = pos + 1
                    while peek < ntok and tokens[peek].t == T.NEWLINE:
                        peek += 1
                    if tokens[peek].t == T.QUESTION:
                        pos += 1
                        continue
                    break
                pos += 1
                continue
            if tt == T.COLON and not stack and ternary > 0:
                ternary -= 1
                else_empty = True
            else:
                else_empty = False
                if tt in (T.LPAREN, T.LBRACK, T.LBRACE):
                    stack.append(tt)
                elif tt in (T.RPAREN, T.RBRACK, T.RBRACE):
                    if stack and stack[-1] == tt - 1:
                        stack.pop()
                elif tt == T.QUESTION and not stack:
                    ternary += 1
            expr.append(tokens[pos])
            pos += 1
        if expr:
            out.append(RawStatement(tok.v, tok.t, expr, offset + tok.start, offset + expr[-1].end))
    return out
