"""ECMAScript value semantics the language requires (language.md, section 3.1).

OpenUI Lang evaluates with JavaScript rules: ``ToNumber``, ``IsLooselyEqual``,
``Number::toString``, ToBoolean truthiness, and property access on arrays and
strings. Clients in other languages MUST reproduce them, so they live here.

Value mapping: ``None`` is JS null (and undefined), ``bool`` is boolean,
``int``/``float`` are numbers (``bool`` is never a number here), ``str`` is a
string, ``list`` an array, ``dict`` an object. Anything else (component
instances, action plans) acts like an opaque object.
"""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal
from typing import Any

_MAX_SAFE = 2**53

# JS WhiteSpace + LineTerminator, as trimmed by StringToNumber.
_JS_WS = " \t\n\v\f\r                 　﻿"

_DECIMAL_RE = re.compile(r"[+-]?(?:Infinity|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\Z")
_HEX_RE = re.compile(r"0[xX][0-9a-fA-F]+\Z")
_OCT_RE = re.compile(r"0[oO][0-7]+\Z")
_BIN_RE = re.compile(r"0[bB][01]+\Z")
_INDEX_RE = re.compile(r"(?:0|[1-9]\d*)\Z")


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def norm_num(x: float | int) -> float | int:
    """Return an int for integral finite values in the safe range, else the float."""
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, int):
        if -_MAX_SAFE <= x <= _MAX_SAFE:
            return x
        return float(x)
    if math.isfinite(x) and x == int(x) and -_MAX_SAFE <= x <= _MAX_SAFE:
        return int(x)
    return x


def string_to_number(s: str) -> float | int:
    """ECMA-262 StringToNumber. May return NaN."""
    t = s.strip(_JS_WS)
    if t == "":
        return 0
    if _DECIMAL_RE.match(t):
        if t.endswith("Infinity"):
            return -math.inf if t.startswith("-") else math.inf
        return norm_num(float(t))
    if _HEX_RE.match(t):
        return norm_num(int(t[2:], 16))
    if _OCT_RE.match(t):
        return norm_num(int(t[2:], 8))
    if _BIN_RE.match(t):
        return norm_num(int(t[2:], 2))
    return math.nan


def raw_to_number(v: Any) -> float | int:
    """ECMA ToNumber for our value set (NaN possible)."""
    if v is None:
        return 0  # null -> 0 (undefined would be NaN; we do not model undefined)
    if isinstance(v, bool):
        return 1 if v else 0
    if is_number(v):
        return v
    if isinstance(v, str):
        return string_to_number(v)
    if isinstance(v, list):
        return string_to_number(to_string(v))
    return math.nan


def to_number(v: Any) -> float | int:
    """The language's ``toNumber`` (section 3.1): numbers as is, strings parsed or 0,
    true is 1, everything else 0."""
    if isinstance(v, bool):
        return 1 if v else 0
    if is_number(v):
        return v
    if isinstance(v, str):
        n = string_to_number(v)
        return 0 if isinstance(n, float) and math.isnan(n) else n
    return 0


def number_to_string(x: float | int) -> str:
    """ECMA-262 Number::toString(10)."""
    if isinstance(x, int):
        if abs(x) < 10**21:
            return str(x)
        x = float(x)
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    sign_bit, digits, exp = Decimal(repr(abs(x))).as_tuple()
    ds = "".join(str(d) for d in digits).lstrip("0")
    # strip trailing zeros into the exponent
    stripped = ds.rstrip("0")
    exp += len(ds) - len(stripped)
    ds = stripped
    k = len(ds)
    n = exp + k  # value = 0.ds * 10^n
    if k <= n <= 21:
        out = ds + "0" * (n - k)
    elif 0 < n <= 21:
        out = ds[:n] + "." + ds[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + ds
    else:
        e = n - 1
        es = ("+" if e >= 0 else "-") + str(abs(e))
        out = (ds + "e" + es) if k == 1 else (ds[0] + "." + ds[1:] + "e" + es)
    return sign + out


def to_string(v: Any) -> str:
    """ECMA ToString (``String(v)``) for our value set."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if is_number(v):
        return number_to_string(v)
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return ",".join("" if e is None else to_string(e) for e in v)
    return "[object Object]"


def truthy(v: Any) -> bool:
    """ECMA ToBoolean."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if is_number(v):
        return not (v == 0 or v != v)
    if isinstance(v, str):
        return v != ""
    return True


def typeof(v: Any) -> str:
    if v is None:
        return "object"
    if isinstance(v, bool):
        return "boolean"
    if is_number(v):
        return "number"
    if isinstance(v, str):
        return "string"
    return "object"


def strict_equal(a: Any, b: Any) -> bool:
    """``===`` (with SameValueZero-free semantics: NaN !== NaN)."""
    ta, tb = typeof(a), typeof(b)
    if ta != tb:
        return False
    if a is None or b is None:
        return a is None and b is None
    if ta == "object":
        return a is b
    return a == b


def loose_equal(a: Any, b: Any) -> bool:
    """ECMA-262 IsLooselyEqual."""
    if a is None or b is None:
        return a is None and b is None
    ta, tb = typeof(a), typeof(b)
    if ta == tb:
        if ta == "object":
            return a is b
        return a == b
    if ta == "number" and tb == "string":
        return a == string_to_number(b)
    if ta == "string" and tb == "number":
        return string_to_number(a) == b
    if ta == "boolean":
        return loose_equal(1 if a else 0, b)
    if tb == "boolean":
        return loose_equal(a, 1 if b else 0)
    if ta == "object" and tb in ("number", "string"):
        return loose_equal(to_string(a), b)
    if tb == "object" and ta in ("number", "string"):
        return loose_equal(a, to_string(b))
    return False


def _utf16_len(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def get_property(obj: Any, key: str) -> Any:
    """``obj[key]`` with a string key, for plain data. Missing gives None."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    if isinstance(obj, list):
        if key == "length":
            return len(obj)
        if _INDEX_RE.match(key):
            i = int(key)
            return obj[i] if i < len(obj) else None
        return None
    if isinstance(obj, str):
        if key == "length":
            return _utf16_len(obj)
        if _INDEX_RE.match(key):
            i = int(key)
            return obj[i] if i < len(obj) else None
        return None
    return None


def js_add(a: Any, b: Any) -> Any:
    """The language's ``+`` (section 3.2)."""
    if isinstance(a, str) or isinstance(b, str):
        return to_string("" if a is None else a) + to_string("" if b is None else b)
    return norm_num(float(to_number(a)) + float(to_number(b)))


def js_mod(a: float | int, b: float | int) -> float | int:
    if b == 0:
        return 0
    if isinstance(a, int) and isinstance(b, int):
        r = abs(a) % abs(b)
        return -r if a < 0 else r
    return norm_num(math.fmod(float(a), float(b)))


def js_round(x: float | int) -> float | int:
    """``Math.round``: halves round toward +Infinity."""
    if isinstance(x, int):
        return x
    if not math.isfinite(x):
        return x
    r = math.floor(x)
    return norm_num(float(r + 1 if x - r >= 0.5 else r))


# ─── Locale collation (``String.prototype.localeCompare`` with no arguments) ───
#
# A compact approximation of the ICU root collation: compare base letters first
# (ignoring accents and case), then accents, then case with lowercase first.
# Whitespace and punctuation sort before symbols, symbols before digits, and
# digits before letters.


#: ICU root order of ASCII punctuation and symbols (from ``localeCompare``).
_ASCII_PUNCT_ORDER = {c: i for i, c in enumerate(" _-,;:!?.'\"()[]{}@*/\\&#%`^+<=>|~$")}


def _char_class(ch: str) -> int:
    if ch in _ASCII_PUNCT_ORDER:
        return 0 if _ASCII_PUNCT_ORDER[ch] <= _ASCII_PUNCT_ORDER["#"] else 1
    cat = unicodedata.category(ch)
    if cat[0] in "ZPC":
        return 0
    if cat[0] == "S":
        return 1
    if cat[0] == "N":
        return 2
    return 3


def _collation_key(s: str) -> tuple:
    primary: list[tuple[int, int]] = []
    secondary: list[str] = []
    tertiary: list[int] = []
    for ch in s:
        decomposed = unicodedata.normalize("NFD", ch)
        base = "".join(c for c in decomposed if not unicodedata.combining(c)) or decomposed
        marks = "".join(c for c in decomposed if unicodedata.combining(c))
        for b in base:
            folded = b.casefold()
            cls = _char_class(b)
            if b in _ASCII_PUNCT_ORDER:
                order = _ASCII_PUNCT_ORDER[b]
            elif cls == 2:
                d = unicodedata.digit(b, None)
                order = d if d is not None else ord(folded[0])
            else:
                order = ord(folded[0]) if folded else ord(b)
            primary.append((cls, order))
            secondary.append(marks)
            tertiary.append(1 if b != b.lower() else 0)
            marks = ""
    return (tuple(primary), tuple(secondary), tuple(tertiary))


def locale_compare(a: str, b: str) -> int:
    ka, kb = _collation_key(a), _collation_key(b)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0 if a == b else (-1 if a < b else 1)
