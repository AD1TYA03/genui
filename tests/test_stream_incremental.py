"""The incremental StreamParser must give exactly the snapshots of a full rebuild per chunk."""

import glob
import json
import random

import pytest

from genui.lang import StreamParser, parse, summarize

with open("spec/fixtures/1.0/library.json") as f:
    SPEC = json.load(f)

def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


FIXTURES = [_read(p) for p in sorted(glob.glob("spec/fixtures/1.0/*/*/input.oui"))]

HANDWRITTEN = [
    # forward references, the way models are told to write
    'root = Stack([a, b, c])\na = Text("one")\nb = Text("two // not a comment")\nc = Stack([a, b])',
    # redefinition: the later statement wins, and dependents must see it
    'root = Stack([x])\nx = Text("old")\ny = Stack([x])\nx = Text("new")\nz = Stack([y, x])',
    # comments, '#' and quotes across lines, a multi-line string
    'root = Stack([t]) // the page\n# a comment line\nt = Text("a \\"quoted\\" # not a comment")\nu = Text("line1\nline2 // still string")',
    # cycles and missing refs
    'root = Stack([p])\np = Stack([q])\nq = Stack([p])\nr = Stack([missing])',
    # state, bindings and expressions
    '$count = 0\nroot = Stack([label])\nlabel = Text("n = " + $count)\n$name = "x"\nother = Text($name)',
    # a fence that arrives late changes everything before it
    'prose first\n```openui\nroot = Stack([t])\nt = Text("in fence")\n```\nmore prose',
    # invalid components and props
    'root = Stack([bad, good])\nbad = Nope(1, 2)\ngood = Text()\nalso = Text("x", "y", "z")',
]


def _random_program(rng: random.Random) -> str:
    n = rng.randint(3, 25)
    names = [f"v{i}" for i in range(n)]
    lines = ["root = Stack([" + ", ".join(rng.sample(names, k=min(len(names), rng.randint(1, 5)))) + "])"]
    for name in names:
        kind = rng.random()
        if kind < 0.4:
            lines.append(f'{name} = Text("{name} {rng.randint(0, 99)}")')
        elif kind < 0.7:
            refs = ", ".join(rng.choice(names) for _ in range(rng.randint(1, 3)))  # may cycle or forward-ref
            lines.append(f"{name} = Stack([{refs}])")
        elif kind < 0.8:
            lines.append(f'{name} = Text("dup")  // redefined later' if rng.random() < 0.5 else f"{name} = Missing({name})")
        elif kind < 0.9:
            lines.append(f"${name} = {rng.randint(0, 9)}")
        else:
            lines.append(f'{name} = Text("{name}" + "#x")')
        if rng.random() < 0.15:
            lines.append(f'{rng.choice(names)} = Text("again")')
    return "\n".join(lines)


def _snapshot(result):
    return json.dumps({
        "tree": summarize(result),
        "errors": [e.to_dict() for e in result.errors],
        "unresolved": result.unresolved,
        "orphans": result.orphans,
        "incomplete": result.incomplete,
        "statements": result.statements,
    }, sort_keys=True, default=repr)


def _chunks(text: str, rng: random.Random) -> list[str]:
    out, i = [], 0
    while i < len(text):
        step = rng.choice([1, 2, 3, 5, 8, 20, 64])
        out.append(text[i:i + step])
        i += step
    return out


def _compare(text: str, rng: random.Random) -> None:
    fast, slow = StreamParser(SPEC), StreamParser(SPEC)
    slow._incremental = False
    for i, chunk in enumerate(_chunks(text, rng)):
        assert _snapshot(fast.feed(chunk)) == _snapshot(slow.feed(chunk)), f"snapshot {i} differs"
    assert _snapshot(fast.end()) == _snapshot(slow.end())


@pytest.mark.parametrize("text", FIXTURES + HANDWRITTEN)
def test_fixed_programs_match_full_rebuild(text):
    _compare(text, random.Random(0))


def test_random_programs_match_full_rebuild():
    rng = random.Random(1234)
    for _ in range(300):
        _compare(_random_program(rng), rng)


def test_final_result_matches_batch_parse_for_line_programs():
    text = "root = Stack([" + ", ".join(f"t{i}" for i in range(50)) + "])\n"
    text += "\n".join(f't{i} = Text("row {i}")' for i in range(50))
    sp = StreamParser(SPEC)
    for c in _chunks(text, random.Random(7)):
        sp.feed(c)
    assert _snapshot(sp.end()) == _snapshot(parse(text, SPEC))


def test_parser_is_reusable_after_end():
    sp = StreamParser(SPEC)
    sp.feed('root = Stack([a])\na = Text("first")\n')
    sp.end()
    sp.feed('root = Stack([b])\nb = Text("second")')
    assert _snapshot(sp.end()) == _snapshot(parse('root = Stack([b])\nb = Text("second")', SPEC))
