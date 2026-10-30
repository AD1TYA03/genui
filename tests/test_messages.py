from genui.messages import action_user_message, build_message, parse_message, strip_markers, to_model_messages


def test_build_and_parse_roundtrip():
    raw = build_message('root = Card([t])\nt = Text("hi")', context={"formState": {"a": 1}},
                        attributes={"library": "support@1.2.0"}, end=True)
    assert raw.splitlines()[0] == "]]>openui:content?library=support%401.2.0"
    m = parse_message(raw)
    assert m.content == 'root = Card([t])\nt = Text("hi")'
    assert m.context == {"formState": {"a": 1}}
    assert m.attributes == {"library": "support@1.2.0"}
    assert m.end is True


def test_encoding_matches_urlsearchparams():
    raw = build_message("x", attributes={"k": "a b~!'()*"})
    assert raw.splitlines()[0] == "]]>openui:content?k=a+b%7E%21%27%28%29*"


def test_last_content_wins_and_retry_on_same_line():
    raw = "]]>openui:content\nold partial]]>openui:content\nroot = Text(\"new\")\n]]>openui:end"
    m = parse_message(raw)
    assert m.content == 'root = Text("new")' and m.end


def test_text_without_markers_is_content():
    assert parse_message("root = Text(\"x\")").content == 'root = Text("x")'


def test_streaming_holds_back_partial_marker():
    m = parse_message("]]>openui:content\nroot = Text(\"x\")\n]]>open", streaming=True)
    assert m.content == 'root = Text("x")'


def test_action_turn_and_model_messages():
    turn = action_user_message("Save order", {"note": "rush"}, {"orderId": 42})
    msgs = to_model_messages([
        {"role": "assistant", "content": build_message("root = Text(\"a\")", context=[{"f": 1}], end=True)},
        {"role": "user", "content": turn},
    ])
    assert msgs[0] == {"role": "assistant", "content": 'root = Text("a")'}
    assert msgs[1]["content"] == ('Save order\ncontext and form values = '
                                  '["User clicked: Save order",{"note":"rush"},{"orderId":42}]')
    assert strip_markers(turn) == "Save order"
