"""Wander backend tests: tool logic, prompt, and a full /api/chat run against a fake model."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

import agent
import data
import tools
from genui.lang import parse

TODAY = date(2026, 11, 1)


def d(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


# ─── data ────────────────────────────────────────────────────────────────────

def test_inventory_shape():
    stays = data.all_stays(TODAY)
    assert len(stays) == 10
    assert len({s["id"] for s in stays}) == 10
    for s in stays:
        assert 3 <= len(s["images"]) <= 4
        assert s["image"] == s["images"][0]
        assert all(re.fullmatch(r"https://images\.unsplash\.com/photo-[0-9a-f-]+\?auto=format&fit=crop&w=1200&q=80", u)
                   for u in s["images"])
        assert s["blocked"] and all(TODAY < date.fromisoformat(b) <= TODAY + timedelta(days=60) for b in s["blocked"])
        assert s["pricePerNight"] > 0 and 0 < s["rating"] <= 5 and s["maxGuests"] >= 2


# ─── tools ───────────────────────────────────────────────────────────────────

def test_search_filters():
    assert [s["id"] for s in tools.search_stays("houseboat", today=TODAY)][:2] == ["alleppey-kettuvallam", "dal-lake-houseboat"]
    assert tools.search_stays("treehouse", today=TODAY)[0]["id"] == "manali-canopy-treehouse"
    assert all(s["pricePerNight"] <= 6000 for s in tools.search_stays(max_price=6000, today=TODAY))
    assert all(s["maxGuests"] >= 4 for s in tools.search_stays(guests=4, today=TODAY))
    assert {s["id"] for s in tools.search_stays(region="kerala", today=TODAY)} == {"alleppey-kettuvallam", "wayanad-bubble-dome"}
    assert len(tools.search_stays("zzzz nothing", today=TODAY)) == 10  # falls back to everything
    assert "blocked" not in tools.search_stays(today=TODAY)[0]


def test_check_availability_pricing():
    q = tools.check_availability("manali-canopy-treehouse", d(10), d(13), today=TODAY)
    assert q["available"] and q["nights"] == 3 and q["currency"] == "INR"
    subtotal, cleaning = 8900 * 3, 1200
    gst = round((subtotal + cleaning) * 0.12)
    assert [line["amount"] for line in q["price_lines"]] == [subtotal, cleaning, gst]
    assert q["total"] == subtotal + cleaning + gst
    assert q["price_lines"][0]["label"] == "₹8,900 × 3 nights"


def test_check_availability_blocked_overlap():
    # treehouse is blocked on days 3, 4, 5; check-out on a blocked day is fine.
    assert tools.check_availability("manali-canopy-treehouse", d(1), d(3), today=TODAY)["available"]
    q = tools.check_availability("manali-canopy-treehouse", d(2), d(5), today=TODAY)
    assert not q["available"] and q["conflicts"] == [d(3), d(4)]


def test_check_availability_errors():
    for args in [("nope", d(1), d(2)), ("kasol-aframe", d(5), d(5)), ("kasol-aframe", "2026-13-01", d(2)),
                 ("kasol-aframe", d(-3), d(2))]:
        with pytest.raises(tools.ToolError):
            tools.check_availability(*args, today=TODAY)


def test_create_booking():
    b = tools.create_booking("kasol-aframe", d(10), d(12), 2, 0, "Aditya", today=TODAY)
    assert re.fullmatch(r"WND-[2-9A-HJ-NP-Z]{5}", b["code"])
    assert b == tools.create_booking("kasol-aframe", d(10), d(12), 2, 0, "Aditya", today=TODAY)  # deterministic
    assert b["guests"] == 2 and b["total"] == tools.check_availability("kasol-aframe", d(10), d(12), today=TODAY)["total"]
    assert b["image"] == data.find_stay("kasol-aframe")["image"]
    with pytest.raises(tools.ToolError, match="at most 2"):
        tools.create_booking("kasol-aframe", d(10), d(12), 2, 1, today=TODAY)
    with pytest.raises(tools.ToolError, match="Not available"):
        tools.create_booking("kasol-aframe", d(5), d(8), 1, today=TODAY)


def test_run_tool_dispatch_and_errors():
    assert json.loads(tools.run_tool("get_stay", '{"id": "kibber-mud-home"}', today=TODAY))["name"] == "Kibber Mud-Brick Homestay"
    assert "error" in json.loads(tools.run_tool("get_stay", '{"id": "x"}', today=TODAY))
    assert "error" in json.loads(tools.run_tool("nope", "{}"))
    assert "error" in json.loads(tools.run_tool("get_stay", "{bad json"))
    assert "error" in json.loads(tools.run_tool("get_stay", '{"wrong": 1}'))
    assert len(json.loads(tools.run_tool("search_stays", "", today=TODAY))) == 10


def test_tool_schemas_match_functions():
    assert [t["function"]["name"] for t in tools.TOOL_SCHEMAS] == list(tools.TOOLS)


# ─── prompt and spec ─────────────────────────────────────────────────────────

def test_system_prompt():
    prompt = agent.build_system_prompt(TODAY)
    assert "Wander" in prompt and "2026-11-01" in prompt
    for sig in ("StayCard(id: string", "DateRangePicker(label: string, checkIn: $binding<string>",
                "BookingTicket(code: string"):
        assert sig in prompt
    assert agent.library.issues() == []


def _ok(program: str) -> None:
    result = parse(program, agent.SPEC)
    assert [e.to_dict() for e in result.errors] == []
    assert result.root is not None and result.root.type_name == "Stack"


def test_flow_programs_parse_cleanly():
    s = data.find_stay("alleppey-kettuvallam", TODAY)
    _ok('root = Stack([h, t, sug])\nh = Heading("Namaste! I\'m Wander", "Extraordinary stays across India")\n'
        't = Text("Where shall we go?", "muted")\nsug = Suggestions(["Treehouses in the Himalayas", "Kerala houseboats"])')
    _ok(f'root = Stack([detail, form])\n'
        f'detail = StayDetail("{s["id"]}", "{s["name"]}", "{s["location"]}", {json.dumps(s["images"])}, "Lovely", '
        f'{json.dumps(s["amenities"])}, {s["pricePerNight"]}, {s["rating"]}, {s["reviews"]})\n'
        f'$checkIn = ""\n$checkOut = ""\n$adults = 2\n$children = 0\n'
        f'form = Form([dates, guests, go])\n'
        f'dates = DateRangePicker("Dates", $checkIn, $checkOut, {json.dumps(s["blocked"])}, 1)\n'
        f'guests = GuestPicker("Guests", $adults, $children, {s["maxGuests"]})\n'
        f'go = Button("Check availability", @ToAssistant("Check availability", {{"stayId": "{s["id"]}"}}), "primary")')
    q = tools.check_availability(s["id"], d(20), d(23), today=TODAY)
    _ok(f'root = Stack([ps, ok], "column", "lg")\nps = PriceSummary({json.dumps(q["price_lines"], ensure_ascii=False)}, {q["total"]}, "INR")\n'
        f'ok = Button("Confirm booking", @ToAssistant("Confirm booking", {{"stayId": "{s["id"]}"}}))')
    b = tools.create_booking(s["id"], d(20), d(23), 2, 1, today=TODAY)
    _ok(f'root = Stack([ticket, c])\nticket = BookingTicket("{b["code"]}", "{b["stayName"]}", "{b["location"]}", "{b["image"]}", '
        f'"{b["checkIn"]}", "{b["checkOut"]}", {b["guests"]}, {b["total"]}, "INR")\n'
        f'c = Callout("You\'re booked!", "See you on the backwaters.", "success")')


# ─── full /api/chat run against a fake model ─────────────────────────────────

def _chunk(content: str | None = None, tool_calls: list[dict] | None = None, finish: str | None = None) -> dict:
    delta: dict[str, Any] = {}
    if content is not None:
        delta["content"] = content
    if tool_calls is not None:
        delta["tool_calls"] = tool_calls
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


class _Stream:
    def __init__(self, chunks: list[dict]):
        self._it = iter(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration from None


class FakeGemini:
    """Round 1: a remark plus a search_stays call (with a Gemini thought signature).
    Round 2: an OpenUI Lang StayGrid built from the tool result, streamed in small pieces."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.program = ""
        self.chat = self
        self.completions = self

    async def create(self, **kw: Any) -> _Stream:
        self.calls.append({**kw, "messages": list(kw["messages"])})  # snapshot: the agent keeps appending
        if len(self.calls) == 1:
            return _Stream([
                _chunk("Let me look"),  # pre-tool remark: must not reach the UI
                _chunk(tool_calls=[{"index": 0, "id": "call_1", "type": "function",
                                    "function": {"name": "search_stays", "arguments": '{"query": "treehouse"}'},
                                    "extra_content": {"google": {"thought_signature": "sig123"}}}]),
                _chunk(finish="tool_calls"),
            ])
        tool_msg = next(m for m in kw["messages"] if m["role"] == "tool")
        stays = json.loads(tool_msg["content"])[:3]
        cards = ", ".join(f"c{i}" for i in range(len(stays)))
        lines = ['root = Stack([h, grid, sug])',
                 'h = Heading("Treehouses and canopy hideaways", "Hand-picked for you")',
                 f'grid = StayGrid([{cards}])']
        for i, s in enumerate(stays):
            lines.append(f'c{i} = StayCard("{s["id"]}", "{s["name"]}", "{s["location"]}", "{s["image"]}", '
                         f'{s["pricePerNight"]}, {s["rating"]}, {json.dumps(s["tags"])}, '
                         f'@ToAssistant("Show {s["name"]}", {{"stayId": "{s["id"]}"}}))')
        lines.append('sug = Suggestions(["Something under ₹6,000", "Desert domes instead"])')
        self.program = "\n".join(lines)
        pieces = [self.program[i:i + 17] for i in range(0, len(self.program), 17)]
        return _Stream([_chunk(p) for p in pieces] + [_chunk(finish="stop")])


def _events(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


@pytest.fixture
def fake(monkeypatch):
    import app as app_module

    fake = FakeGemini()
    monkeypatch.setattr(agent, "_client", fake)
    return fake, TestClient(app_module.app)


def test_health(fake):
    _, client = fake
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] and "StayCard" in r.json()["components"]


def test_chat_full_run(fake):
    model, client = fake
    body = {"threadId": "t1", "runId": "r1",
            "messages": [{"id": "m1", "role": "user", "content": "Find me a treehouse"}]}
    r = client.post("/api/chat", json=body)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = _events(r.text)
    types = [e["type"] for e in events]

    assert types[0] == "RUN_STARTED" and events[0]["threadId"] == "t1" and events[0]["runId"] == "r1"
    assert types[-1] == "RUN_FINISHED" and "RUN_ERROR" not in types
    # tool activity is surfaced before the answer
    for t in ("TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END", "TOOL_CALL_RESULT"):
        assert t in types
    start = next(e for e in events if e["type"] == "TOOL_CALL_START")
    assert start["toolCallName"] == "search_stays" and start["toolCallId"] == "call_1"
    result = json.loads(next(e for e in events if e["type"] == "TOOL_CALL_RESULT")["content"])
    assert result[0]["id"] == "manali-canopy-treehouse"
    assert types.index("TOOL_CALL_RESULT") < types.index("TEXT_MESSAGE_START")

    # the streamed text is exactly the final program (pre-tool remark dropped), in many deltas
    deltas = [e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT"]
    text = "".join(deltas)
    assert text == model.program and len(deltas) > 5
    assert "Let me look" not in text

    # the program parses with zero errors against the spec and uses only tool image URLs
    result_parse = parse(text, agent.SPEC)
    assert [e.to_dict() for e in result_parse.errors] == []
    assert set(re.findall(r"https://images\.unsplash\.com/[^\"]+", text)) <= set(data.all_image_urls())

    # model saw the Wander system prompt + tools, and the thought signature was sent back
    first, second = model.calls
    assert first["messages"][0]["role"] == "system" and "OpenUI Lang" in first["messages"][0]["content"]
    assert first["tools"] == tools.TOOL_SCHEMAS and first["stream"] is True
    assistant = next(m for m in second["messages"] if m.get("tool_calls"))
    assert assistant["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "sig123"}}


def test_chat_feeds_back_previous_errors(fake):
    model, client = fake
    body = {"messages": [
        {"id": "m1", "role": "user", "content": "hi"},
        {"id": "m2", "role": "assistant", "content": 'root = Stack([StayCard("x")])'},  # missing required props
        {"id": "m3", "role": "user", "content": "Find me a treehouse"},
    ]}
    client.post("/api/chat", json=body)
    notes = [m for m in model.calls[0]["messages"][1:] if m["role"] == "system"]
    assert notes and "previous OpenUI Lang response had these errors" in notes[0]["content"]


def test_chat_drops_stale_tool_history(fake):
    model, client = fake
    body = {"messages": [
        {"id": "m1", "role": "user", "content": "hi"},
        {"id": "m2", "role": "assistant", "content": "",
         "toolCalls": [{"id": "old", "type": "function", "function": {"name": "search_stays", "arguments": "{}"}}]},
        {"id": "m3", "role": "tool", "toolCallId": "old", "content": "[]"},
        {"id": "m4", "role": "user", "content": "Find me a treehouse"},
    ]}
    client.post("/api/chat", json=body)
    roles = [m["role"] for m in model.calls[0]["messages"]]
    assert roles == ["system", "user", "user"]


def test_missing_key_becomes_run_error(monkeypatch):
    import app as app_module

    monkeypatch.setattr(agent, "_client", None)
    monkeypatch.setattr(agent, "gemini_api_key", lambda: None)
    r = TestClient(app_module.app).post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    events = _events(r.text)
    assert events[-1]["type"] == "RUN_ERROR" and "GEMINI_API_KEY" in events[-1]["message"]
