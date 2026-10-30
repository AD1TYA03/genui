from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from genui.library import Library, LibraryError

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "spec/fixtures/1.0/library.json"
GOLDEN_LIBS = sorted((ROOT / "tests/golden/libraries").glob("*.json"))
# Libraries built by the TS reference with createLibrary() + zod (toSpec output)
ZOD_LIBS = [p for p in GOLDEN_LIBS if p.stem != "minimal"]


def spec() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ── loading ──


def test_from_path_dict_json_bytes():
    a = Library.from_spec(FIXTURE)
    b = Library.from_spec(str(FIXTURE))
    c = Library.from_spec(spec())
    d = Library.from_spec(FIXTURE.read_text(encoding="utf-8"))
    e = Library.from_spec(FIXTURE.read_bytes())
    assert a.to_spec() == b.to_spec() == c.to_spec() == d.to_spec() == e.to_spec()


def test_metadata():
    lib = Library.from_spec(FIXTURE)
    assert lib.id == spec()["id"]
    assert lib.version == spec()["version"]
    assert lib.root == "Stack"
    assert lib.component_groups is None
    assert "$defs" in lib.schema


def test_bad_inputs():
    with pytest.raises(LibraryError, match="not valid JSON"):
        Library.from_spec("{nope")
    with pytest.raises(LibraryError, match="Cannot read"):
        Library.from_spec("/does/not/exist.json")
    with pytest.raises(LibraryError, match="components"):
        Library.from_spec({"root": "X"})


def test_to_spec_round_trip_keeps_key_order():
    raw = FIXTURE.read_text(encoding="utf-8")
    lib = Library.from_spec(raw)
    assert json.dumps(lib.to_spec()) == json.dumps(json.loads(raw))
    assert list(lib.to_spec()["schema"]["$defs"]["Button"]["properties"]) == ["label", "action", "variant", "share"]
    out = lib.to_spec()
    out["components"].clear()
    assert lib.components  # a copy


def test_input_not_aliased():
    data = spec()
    lib = Library.from_spec(data)
    data["components"].clear()
    assert "Button" in lib.components


# ── components / functions / actions ──


def test_components_in_order_with_props():
    lib = Library.from_spec(FIXTURE)
    assert list(lib.components) == list(spec()["components"])
    button = lib.components["Button"]
    assert button.description == "A clickable button"
    assert button.signature == spec()["components"]["Button"]["signature"]
    assert button.prop_names == ("label", "action", "variant", "share")
    label, action, variant, share = button.props
    assert (label.required, label.optional, label.type) == (True, False, "string")
    assert (action.required, action.optional, action.type) == (False, True, "ActionExpression")
    assert variant.type == '"primary" | "secondary"'
    assert share.type == "@CopyToClipboard | @OpenUrl"
    value = lib.components["Input"].props[2]
    assert value.name == "value" and value.binding and value.type == "$binding<string>"


def test_functions_and_actions():
    lib = Library.from_spec(FIXTURE)
    upper = lib.functions["Upper"]
    assert upper.signature == "Upper(text: string) → string"
    assert upper.param_names == ("text",)
    assert upper.return_type == "string"
    copy_ = lib.actions["CopyToClipboard"]
    assert copy_.returns is None and copy_.param_names == ("text",)


def test_defaults_and_nullable():
    lib = Library.from_spec(ROOT / "tests/golden/libraries/groups.json", validate=False)
    height = lib.components["Chart"].props[2]
    assert height.required and height.optional and height.has_default and height.default == 240
    gap = lib.components["Stack"].props[2]
    assert gap.required and gap.optional and gap.type == "number"


# ── signatures rebuilt from the schema ──


@pytest.mark.parametrize("path", ZOD_LIBS, ids=[p.stem for p in ZOD_LIBS])
def test_signature_matches_reference(path: Path):
    """Signatures rebuilt from JSON Schema equal what lang-core printed from zod."""
    data = json.loads(path.read_text(encoding="utf-8"))
    lib = Library.from_spec(data, validate=False)
    for kind in ("components", "functions", "actions"):
        for name, entry in (data.get(kind) or {}).items():
            assert lib.signature(name) == entry["signature"], (kind, name)


def test_fixture_signatures():
    lib = Library.from_spec(FIXTURE)
    for name, entry in spec()["components"].items():
        if name in ("Stack", "Card", "Form", "Select", "Table"):
            continue  # fixture signatures print component lists as any[]; its schema has $refs (schema wins)
        assert lib.signature(name) == entry["signature"], name
    assert lib.signature("Stack") == (
        "Stack(children: (Stack | Card | Text | Tag | Metric | Button | Form | Input | Select | "
        'SelectItem | Table | Col)[], direction?: "row" | "column")'
    )
    assert lib.signature("Table") == "Table(columns: Col[])"
    assert lib.signature("Select") == "Select(name: string, items: SelectItem[], value?: $binding<string>)"
    assert lib.signature("Upper") == "Upper(text: string) → string"
    assert lib.signature("CopyToClipboard") == "CopyToClipboard(text: string)"
    with pytest.raises(KeyError):
        lib.signature("Nope")


def test_schema_wins_over_signature():
    data = spec()
    data["components"]["Metric"]["signature"] = "Metric(label: string)"
    assert Library.from_spec(data).signature("Metric") == "Metric(label: string, value: number)"


def test_signature_without_schema_falls_back():
    lib = Library.from_spec(ROOT / "tests/golden/libraries/minimal.json")
    assert lib.signature("Field") == "Field(name: string, value?: $binding<number>)"
    assert lib.components["Field"].props == ()


# ── validation (section 3.1) ──


def test_valid_libraries():
    for path in [FIXTURE, *GOLDEN_LIBS]:
        if path.stem == "groups":
            continue
        Library.from_spec(path).validate()


def test_groups_golden_has_unknown_member():
    # The TS reference accepts it (and the prompt skips it); section 3.1 does not.
    lib = Library.from_spec(ROOT / "tests/golden/libraries/groups.json", validate=False)
    assert lib.issues() == ["Component group 'Content' references unknown component 'Missing'."]


def bad(mutate) -> LibraryError:
    data = spec()
    mutate(data)
    with pytest.raises(LibraryError) as info:
        Library.from_spec(data)
    return info.value


def test_lowercase_component():
    def m(d):
        d["components"]["metric"] = d["components"].pop("Metric")
        d["schema"]["$defs"]["metric"] = d["schema"]["$defs"]["Metric"]

    assert "uppercase" in str(bad(m))


def test_non_identifier_name():
    def m(d):
        d["components"]["My-Comp"] = {"signature": "My-Comp()"}
        d["schema"]["$defs"]["My-Comp"] = {"type": "object", "properties": {}}

    assert "identifier" in str(bad(m))


def test_lowercase_function_and_action():
    def m(d):
        d["functions"]["upper"] = d["functions"].pop("Upper")
        d["actions"]["copy"] = d["actions"].pop("CopyToClipboard")

    err = bad(m)
    assert any("Function name 'upper'" in i for i in err.issues)
    assert any("Action name 'copy'" in i for i in err.issues)


@pytest.mark.parametrize("name", ["Query", "Mutation", "Action", "Count", "Each", "OpenUrl", "Reset"])
def test_reserved_component_names(name):
    def m(d):
        d["components"][name] = {"signature": f"{name}()"}
        d["schema"]["$defs"][name] = {"type": "object", "properties": {}}

    assert "reserved" in str(bad(m))


def test_reserved_function_name():
    assert "reserved" in str(bad(lambda d: d["functions"].__setitem__("Sum", {"signature": "Sum()"})))


def test_collision_between_component_and_function():
    assert "collides" in str(bad(lambda d: d["functions"].__setitem__("Card", {"signature": "Card()"})))


def test_required_after_optional():
    def m(d):
        props = d["schema"]["$defs"]["Metric"]
        props["properties"] = {"value": {"type": "number"}, "label": {"type": "string"}}
        props["required"] = ["label"]

    assert "required prop 'label' comes after optional prop 'value'" in str(bad(m))


def test_required_with_default_may_come_last():
    data = spec()
    d = data["schema"]["$defs"]["Text"]
    d["properties"]["size"] = {"type": "number", "default": 1}
    d["required"] = ["text", "size"]
    Library.from_spec(data)


def test_function_param_order():
    def m(d):
        p = d["schema"]["functions"]["Upper"]["params"]
        p["properties"] = {"a": {"type": "string"}, "text": {"type": "string"}}
        p["required"] = ["text"]

    assert "Function 'Upper'" in str(bad(m))


def test_root_must_exist():
    assert "Root component 'Nope'" in str(bad(lambda d: d.__setitem__("root", "Nope")))


def test_group_components_must_exist():
    err = bad(lambda d: d.__setitem__("componentGroups", [{"name": "G", "components": ["Card", "Ghost"]}]))
    assert "unknown component 'Ghost'" in str(err)


def test_unresolved_ref():
    def m(d):
        d["schema"]["$defs"]["Table"]["properties"]["columns"]["items"] = {"$ref": "#/$defs/Column"}

    assert 'Unresolvable $ref "#/$defs/Column"' in str(bad(m))


def test_component_without_schema_entry():
    assert "no entry in schema.$defs" in str(bad(lambda d: d["components"].__setitem__("Extra", {"signature": "Extra()"})))


def test_reports_all_issues_and_skip_validation():
    data = spec()
    data["root"] = "Nope"
    data["functions"]["Sum"] = {"signature": "Sum()"}
    lib = Library.from_spec(data, validate=False)
    assert len(lib.issues()) == 2
    with pytest.raises(LibraryError) as info:
        lib.validate()
    assert len(info.value.issues) == 2
    assert isinstance(info.value, ValueError)


def test_deepcopy_independent():
    lib = Library.from_spec(FIXTURE)
    assert copy.deepcopy(lib.to_spec()) == lib.to_spec()
