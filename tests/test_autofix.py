import json

from genui import Library, autofix, parse_message, strip_markers
from genui.lang import OpenUIError
from genui.stream import StreamError, ToolCallStart, ToolResult, to_agui

LIB = Library.from_spec("spec/fixtures/1.0/library.json")
GOOD = 'root = Stack([t])\nt = Text("fixed")'
BAD = 'root = Stack([t])\nt = Nope("broken")'


class FakeModel:
    """Replies with the scripted texts in order, recording the `fix` turns it receives."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, fix):
        self.calls.append(fix)
        reply = self.replies.pop(0)

        async def stream():
            for item in (reply if isinstance(reply, list) else [reply[i:i + 7] for i in range(0, len(reply), 7)]):
                yield item

        return stream()


async def text_of(source):
    out = [json.loads(line[6:]) async for line in to_agui(source)]
    return "".join(e.get("delta", "") for e in out if e["type"] == "TEXT_MESSAGE_CONTENT"), out


async def test_valid_program_is_not_retried():
    model = FakeModel(GOOD)
    text, _ = await text_of(autofix(model, LIB))
    assert text == GOOD and model.calls == [[]]


async def test_broken_program_is_corrected_in_place():
    model = FakeModel(BAD, GOOD)
    text, _ = await text_of(autofix(model, LIB))
    # the frontend reads the last content section: the corrected program
    assert strip_markers(text) == GOOD
    assert parse_message(text).content == GOOD
    fix = model.calls[1]
    assert fix[0] == {"role": "assistant", "content": BAD}
    assert fix[1]["role"] == "user" and "unknown-component" in fix[1]["content"] and "]]>" not in fix[1]["content"]


async def test_retries_are_bounded():
    model = FakeModel(BAD, BAD, BAD)
    text, _ = await text_of(autofix(model, LIB, max_retries=2))
    assert len(model.calls) == 3 and text.count("]]>openui:content") == 2


async def test_buffer_mode_only_sends_the_final_program():
    model = FakeModel(BAD, GOOD)
    text, _ = await text_of(autofix(model, LIB, buffer=True))
    assert text == GOOD


async def test_program_is_the_text_after_the_last_tool_event():
    model = FakeModel(["Let me look that up. ", ToolCallStart("c1", "search"), ToolResult("c1", "{}"), GOOD])
    _, events = await text_of(autofix(model, LIB))
    assert model.calls == [[]]  # the preamble is not mistaken for a broken program
    assert any(e["type"] == "TOOL_CALL_START" for e in events)


async def test_stream_error_stops_without_retry():
    model = FakeModel([BAD, StreamError("rate limited")], GOOD)
    _, events = await text_of(autofix(model, LIB))
    assert events[-1]["type"] == "RUN_ERROR" and len(model.calls) == 1


async def test_custom_check_and_sync_generate():
    calls = []

    def generate(fix):
        calls.append(fix)
        return ["root = Stack([])"] if not fix else [GOOD]

    def check(text):
        return [] if "fixed" in text else [OpenUIError("parser", "custom", "must say fixed")]

    text, _ = await text_of(autofix(generate, LIB, check=check))
    assert len(calls) == 2 and strip_markers(text) == GOOD
