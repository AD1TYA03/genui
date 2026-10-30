"""OpenUI Lang 1.0 conformance fixtures (spec/language.md, Appendix B).

Comparison rules: spec/fixtures/1.0/README.md. Level 1 (program) checks only;
``interactions.json`` needs a renderer and is out of scope here.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from genui.lang import StreamParser, merge, parse, serialize, summarize
from genui.lang.rules import check_rules

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(os.environ.get("OPENUI_FIXTURES", ROOT / "spec" / "fixtures" / "1.0"))
LIBRARY = json.loads((FIXTURES / "library.json").read_text(encoding="utf-8"))

#: Implementations of library.json's functions, which a runner supplies.
FUNCTIONS = {"Upper": lambda args: str(args.get("text") or "").upper()}

OPTIONAL = ("state", "statements", "errorObjects")
_STATEMENT_LINE = re.compile(r"^(\$?\w+)\s*=(?!=)")


def _cases() -> list[Path]:
    return sorted(p for p in FIXTURES.glob("*/*") if p.is_dir())


# ─── comparison ─────────────────────────────────────────────────────────────


def same(a: Any, b: Any) -> bool:
    """Deep equality with JSON types kept apart (``true`` is not ``1``)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) or isinstance(b, (int, float)):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b
    if isinstance(a, list) or isinstance(b, list):
        return (isinstance(a, list) and isinstance(b, list) and len(a) == len(b)
                and all(same(x, y) for x, y in zip(a, b)))
    if isinstance(a, dict) or isinstance(b, dict):
        return (isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys()
                and all(same(a[k], b[k]) for k in a))
    return a == b


def claims(expected: list[dict], actual: list[dict]) -> bool:
    """Each expected entry claims an actual entry agreeing on the keys it lists.
    Entries listing more keys go first (so ``{code}`` alone matches any statement)."""
    pool = list(actual)
    for e in sorted(expected, key=lambda d: -len(d)):
        for i, a in enumerate(pool):
            if all(same(v, a.get(k)) for k, v in e.items()):
                del pool[i]
                break
        else:
            return False
    return True


def as_set(xs: list) -> list:
    return sorted(set(xs))


COMPARE = {
    "root": same,
    "errors": lambda w, g: len(w) == len(g) and claims(w, g),
    "unresolved": lambda w, g: as_set(w) == as_set(g),
    "orphans": lambda w, g: as_set(w) == as_set(g),
    "incomplete": same,
    "state": same,
    "statements": same,
    "errorObjects": claims,
}


def check(case_id: str, expected: dict, result, statements: list[str] | None = None) -> list[str]:
    actual = summarize(result)
    if statements is not None:
        actual["statements"] = statements
    diffs = []
    for key, ok in COMPARE.items():
        if key not in expected and key in OPTIONAL:
            continue
        if not ok(expected.get(key), actual.get(key)):
            diffs.append(f"{key}: expected {json.dumps(expected.get(key))}, got {json.dumps(actual.get(key))}")
    if "-roundtrip-" in case_id:
        tree = result.evaluate().root
        if tree is not None:
            text = serialize(tree, result.library)
            again = summarize(parse(text, LIBRARY, FUNCTIONS))["root"]
            if not same(again, expected["root"]):
                diffs.append(f"roundtrip: {text!r} parses to {json.dumps(again)}")
    return diffs


# ─── running a case ─────────────────────────────────────────────────────────


def run_program(case_id: str, files: dict[str, str]) -> list[str]:
    expected = json.loads(files["expected.json"])
    if "chunks.json" in files:
        chunks = json.loads(files["chunks.json"])
        sp = StreamParser(LIBRARY, FUNCTIONS)
        for chunk in chunks:
            sp.feed(chunk)
        streamed = sp.end()
        return ([f"streamed {d}" for d in check(case_id, expected, streamed)]
                + [f"batch {d}" for d in check(case_id, expected, parse("".join(chunks), LIBRARY, FUNCTIONS))])
    if "patch.oui" in files:
        merged = merge(files["input.oui"], files["patch.oui"])
        statements = [m.group(1) for line in merged.split("\n") if (m := _STATEMENT_LINE.match(line))]
        return check(case_id, expected, parse(merged, LIBRARY, FUNCTIONS), statements)
    return check(case_id, expected, parse(files["input.oui"], LIBRARY, FUNCTIONS))


def run_validation(files: dict[str, str]) -> list[str]:
    diffs = []
    for i, case in enumerate(json.loads(files["validation.json"])["cases"]):
        error = check_rules(case["value"], case["rules"])
        if (error is None) != case["valid"]:
            diffs.append(f"case {i} {json.dumps(case['rules'])} {json.dumps(case['value'])}: got {error!r}")
    return diffs


@pytest.mark.parametrize("case", _cases(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_fixture(case: Path) -> None:
    files = {f.name: f.read_text(encoding="utf-8") for f in case.iterdir() if f.is_file()}
    case_id = f"{case.parent.name}/{case.name}"
    diffs = run_validation(files) if "validation.json" in files else run_program(case_id, files)
    assert not diffs, f"{case_id}\n  " + "\n  ".join(diffs)


def test_fixture_count() -> None:
    assert len(_cases()) >= 50  # guards against silent discovery failure


# ─── streaming equals parsing (language.md, section 4), beyond the fixture chunkings ───
# The reference (and genui, which mirrors it) can differ from a batch parse when a final
# redefinition needs implicit closing (COMPAT.md); no fixture program hits that case.


def _programs() -> list[tuple[str, str]]:
    out = []
    for case in _cases():
        case_id = f"{case.parent.name}/{case.name}"
        if (case / "input.oui").exists():
            out.append((case_id, (case / "input.oui").read_text(encoding="utf-8")))
        if (case / "patch.oui").exists():
            out.append((case_id + ":patch", (case / "patch.oui").read_text(encoding="utf-8")))
        if (case / "chunks.json").exists():
            out.append((case_id, "".join(json.loads((case / "chunks.json").read_text(encoding="utf-8")))))
    return out


def _stream(chunks: list[str]) -> dict:
    sp = StreamParser(LIBRARY, FUNCTIONS)
    for chunk in chunks:
        summarize(sp.feed(chunk))  # every intermediate frame must evaluate without raising
    return summarize(sp.end())


@pytest.mark.parametrize("case_id,text", _programs(), ids=[p[0] for p in _programs()])
def test_streaming_equals_batch(case_id: str, text: str) -> None:
    import random

    batch = summarize(parse(text, LIBRARY, FUNCTIONS))
    splits = [[text[:i], text[i:]] for i in range(len(text) + 1)]
    rng = random.Random(case_id)
    for _ in range(20):
        cuts = sorted(rng.sample(range(len(text) + 1), min(len(text) + 1, rng.randint(1, 12))))
        splits.append([text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)])])
    splits.append(list(text))  # one character at a time
    for chunks in splits:
        assert _stream(chunks) == batch, f"{case_id}: chunks {chunks!r}"
