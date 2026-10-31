"""Source preparation and statement boundaries (language.md, sections 1.2, 1.4, 4).

Ported from the reference implementation (``@openuidev/lang-core``,
``parser/parser.ts``, ``parser/statements.ts``, ``parser/merge.ts``) so that a
Python backend reads text exactly as the TypeScript renderer does. Where the
reference differs from the spec prose, the reference wins; see ``COMPAT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lexer import T, Token, tokenize

_OPEN = {")": "(", "]": "[", "}": "{"}
_CLOSE = {"(": ")", "[": "]", "{": "}"}


# ─── Fence extraction (parser.ts: stripFences) ─────────────────────────────


def _skip_string(text: str, start: int) -> int:
    """Index after the double-quoted string at ``start``; ``start`` if none starts there."""
    if text[start] != '"':
        return start
    i = start + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
        elif c == '"':
            return i + 1
        else:
            i += 1
    return i


def strip_fences(text: str) -> str:
    """Extract code from markdown fences, or return the text as is when it has none.

    As in the reference: an opening fence is three backticks anywhere outside a
    double-quoted string (prose included); a closing fence is three backticks
    outside a double-quoted string; an unterminated fence runs to the end.
    """
    blocks: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        fence_start = -1
        while i < n:
            nxt = _skip_string(text, i)
            if nxt > i:
                i = nxt
                continue
            if text.startswith("```", i):
                fence_start = i
                break
            i += 1
        if fence_start == -1:
            break
        j = fence_start + 3
        while j < n and text[j] != "\n":
            j += 1
        if j >= n:
            # No newline after the opening fence yet (streaming): drop the language tag line.
            rest = text[fence_start + 3:]
            nl = rest.find("\n")
            blocks.append("" if nl == -1 else rest[nl + 1:])
            break
        j += 1
        close = -1
        k = j
        while k < n:
            nk = _skip_string(text, k)
            if nk > k:
                k = nk
                continue
            if text.startswith("```", k):
                close = k
                break
            k += 1
        if close != -1:
            blocks.append(text[j:close])
            i = close + 3
        else:
            blocks.append(text[j:])
            break
    if blocks:
        return "\n".join(blocks)
    if text.startswith("```"):
        j = 3
        while j < n and text[j] != "\n":
            j += 1
        start = j + 1 if j < n else 3
        body = text[start:]
        trailing = body.rfind("```")
        return body[:trailing] if trailing != -1 else body
    return text


# ─── Comment stripping (parser.ts: stripComments) ──────────────────────────


def _strip_line(line: str, in_str: str | None) -> tuple[str, str | None]:
    """One line of :func:`strip_comments`: the kept text, and the string state after it."""
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
    return (line if cut is None else line[:cut].rstrip()), in_str


def strip_comments(text: str) -> str:
    """Remove ``//`` and ``#`` comments outside strings, even multi-line strings."""
    in_str: str | None = None
    out_lines: list[str] = []
    for line in text.split("\n"):
        kept, in_str = _strip_line(line, in_str)
        out_lines.append(kept)
    return "\n".join(out_lines)


class IncrementalPreprocessor:
    """:func:`preprocess` for a growing buffer, reprocessing only the new text.

    Comment stripping is line by line (with string state carried across lines), so
    complete lines are processed once. Fences can change the whole text, so a buffer
    containing three backticks falls back to the full :func:`preprocess`.
    """

    def __init__(self) -> None:
        self._raw_done = 0  # chars of the buffer covered by `_lines` (complete lines + "\n")
        self._lines: list[str] = []
        self._joined = ""  # "\n".join(_lines) + "\n" when _lines is not empty
        self._state: str | None = None

    def __call__(self, buf: str) -> str:
        if "```" in buf:
            return preprocess(buf)
        if len(buf) < self._raw_done:  # not a continuation: start over
            self.__init__()
        nl = buf.rfind("\n")
        if nl + 1 > self._raw_done:
            added = []
            state = self._state
            for line in buf[self._raw_done:nl].split("\n"):
                kept, state = _strip_line(line, state)
                added.append(kept)
            self._lines.extend(added)
            self._joined += "\n".join(added) + "\n"
            self._state = state
            self._raw_done = nl + 1
        tail, _ = _strip_line(buf[self._raw_done:], self._state)
        return (self._joined + tail).strip()


def preprocess(text: str) -> str:
    """Fence extraction, comment stripping, trimming (section 1.2)."""
    return strip_comments(strip_fences(text.strip())).strip()


# ─── Implicit closing (statements.ts: autoClose) ───────────────────────────


def autoclose(text: str) -> tuple[str, bool]:
    """Close an unterminated string (adding ``\\`` first when the text ends
    mid-escape), then unclosed brackets in reverse order. A closing bracket that
    does not match the innermost opener is ignored. Returns ``(text, was_incomplete)``."""
    stack: list[str] = []
    in_str: str | None = None
    esc = False
    for c in text:
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if in_str:
            if c == in_str:
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


# ─── Token-level statement split (statements.ts: split) ────────────────────


@dataclass
class RawStatement:
    id: str
    id_type: T
    tokens: list[Token]
    #: offsets of the statement text (name through last expression token)
    start: int
    end: int


def split_statements(text: str, offset: int = 0) -> list[RawStatement]:
    """Split text into ``name = expression`` statements.

    A newline ends a statement at bracket depth 0 with no open ternary, unless
    the next non-newline token is ``?``. Any closing bracket lowers the depth.
    A line without the ``name =`` shape is skipped up to its next newline token.
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
        if tok.t not in (T.IDENT, T.TYPE, T.STATE):
            while pos < ntok and tokens[pos].t not in (T.NEWLINE, T.EOF):
                pos += 1
            continue
        pos += 1
        if pos >= ntok or tokens[pos].t != T.EQUALS:
            while pos < ntok and tokens[pos].t not in (T.NEWLINE, T.EOF):
                pos += 1
            continue
        pos += 1
        expr: list[Token] = []
        depth = 0
        ternary = 0
        while pos < ntok and tokens[pos].t != T.EOF:
            tt = tokens[pos].t
            if tt == T.NEWLINE and depth <= 0 and ternary <= 0:
                peek = pos + 1
                while peek < ntok and tokens[peek].t == T.NEWLINE:
                    peek += 1
                nxt = tokens[peek].t if peek < ntok else T.EOF
                if nxt == T.QUESTION or (nxt == T.COLON and ternary > 0):
                    pos += 1
                    continue
                break
            if tt == T.NEWLINE:
                pos += 1
                continue
            if tt in (T.LPAREN, T.LBRACK, T.LBRACE):
                depth += 1
            elif tt in (T.RPAREN, T.RBRACK, T.RBRACE) and depth > 0:
                depth -= 1
            elif tt == T.QUESTION and depth == 0:
                ternary += 1
            elif tt == T.COLON and depth == 0 and ternary > 0:
                ternary -= 1
            expr.append(tokens[pos])
            pos += 1
        if expr:
            out.append(RawStatement(tok.v, tok.t, expr, offset + tok.start, offset + expr[-1].end))
    return out


# ─── Streaming completion (parser.ts: scanNewCompleted) ────────────────────


def scan_completed(text: str, start: int) -> tuple[list[tuple[int, int]], int]:
    """Find statements completed in prepared streaming text, from ``start``.

    A depth-0 newline outside strings with no open ternary completes a
    statement, unless the next non-whitespace character is ``?``. Returns the
    completed ``(start, end)`` spans and the start of the pending tail.
    """
    spans: list[tuple[int, int]] = []
    depth = 0
    ternary = 0
    in_str: str | None = None
    esc = False
    seg = start
    n = len(text)
    for i in range(start, n):
        c = text[i]
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if in_str:
            if c == in_str:
                in_str = None
            continue
        if c == '"' or c == "'":
            in_str = c
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth = max(0, depth - 1)
        elif c == "?" and depth == 0:
            ternary += 1
        elif c == ":" and depth == 0 and ternary > 0:
            ternary -= 1
        elif c == "\n" and depth <= 0 and ternary <= 0:
            peek = i + 1
            while peek < n and text[peek] in " \t\r\n":
                peek += 1
            if peek < n and (text[peek] == "?" or (text[peek] == ":" and ternary > 0)):
                continue
            spans.append((seg, i))
            seg = i + 1
    return spans, seg


# ─── Merge statement chunks (merge.ts: splitStatementSource) ───────────────


def split_statement_source(text: str) -> list[str]:
    """Split text into statement chunks at depth-0 newlines outside strings.

    Unlike :func:`split_statements` this does not follow multi-line ternaries,
    as in the reference's edit merge.
    """
    chunks: list[str] = []
    depth = 0
    in_str: str | None = None
    esc = False
    start = 0
    for i, c in enumerate(text):
        if esc:
            esc = False
            continue
        if c == "\\" and in_str:
            esc = True
            continue
        if in_str:
            if c == in_str:
                in_str = None
            continue
        if c == '"' or c == "'":
            in_str = c
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth = max(0, depth - 1)
        elif c == "\n" and depth <= 0:
            chunk = text[start:i].strip()
            if chunk:
                chunks.append(chunk)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        chunks.append(tail)
    return chunks
