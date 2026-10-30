"""System prompt generation (spec/prompt.md section 4).

A line-by-line port of lang-core's ``generateSystemPrompt`` (``parser/prompt.ts``)
so that the same LibrarySpec and options give a byte-identical prompt in
Python and TypeScript. JavaScript semantics that affect the output are kept:
``??`` vs truthiness, ``{}``/``[]`` being truthy, integer-like object keys
iterating first, and ``JSON.stringify`` formatting.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping, Sequence, Union

__all__ = ["system_prompt", "ToolDescriptor"]

#: A tool: a bare name, or ``{name, description?, inputSchema, outputSchema, annotations?}``.
ToolDescriptor = Union[str, Mapping[str, Any]]


# ─── JavaScript semantics helpers ───────────────────────────────────────────


def _truthy(value: Any) -> bool:
    """JavaScript truthiness: objects and arrays are truthy even when empty."""
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value == value and value != 0  # NaN and 0 are falsy
    if isinstance(value, str):
        return value != ""
    return True


def _nn(value: Any, default: Any) -> Any:
    """JavaScript ``value ?? default``."""
    return default if value is None else value


def _length(value: Any) -> int:
    """``value?.length`` treated as a number (0 when missing)."""
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 0


_ARRAY_INDEX = re.compile(r"(0|[1-9][0-9]*)\Z")


def _js_keys(obj: Mapping[str, Any]) -> list[str]:
    """``Object.keys`` order: array-index keys ascending, then the rest in insertion order."""
    keys = list(obj.keys())
    index_keys = [k for k in keys if isinstance(k, str) and _ARRAY_INDEX.match(k) and int(k) < 2**32 - 1]
    if not index_keys:
        return keys
    index_set = set(index_keys)
    return sorted(index_keys, key=int) + [k for k in keys if k not in index_set]


def _js_items(obj: Any) -> list[tuple[str, Any]]:
    if not isinstance(obj, Mapping):
        return []
    return [(k, obj[k]) for k in _js_keys(obj)]


def _js_values(obj: Any) -> list[Any]:
    return [v for _, v in _js_items(obj)]


def _js_template(value: Any) -> str:
    """``${value}`` in a JavaScript template literal."""
    from .library import _js_string

    return _js_string(value)


def _json_stringify(value: Any) -> str:
    """``JSON.stringify`` for the plain values defaultForSchema() returns."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _includes(container: Any, item: Any) -> bool:
    if isinstance(container, (list, tuple)):
        return item in container
    if isinstance(container, str):
        return isinstance(item, str) and item in container
    return False


# ─── JSON Schema → type string helper ───────────────────────────────────────


def _json_schema_type_str(schema: Any) -> str:
    if not isinstance(schema, Mapping):
        return "any"
    t = schema.get("type")
    if t == "string":
        enum_vals = schema.get("enum")
        if _truthy(enum_vals):
            if isinstance(enum_vals, (list, tuple)):
                return " | ".join(f'"{_js_template(v)}"' for v in enum_vals)
        return "string"
    if t in ("number", "integer"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        items = schema.get("items")
        if _truthy(items):
            return f"{_json_schema_type_str(items)}[]"
        return "any[]"
    if t == "object":
        props = schema.get("properties")
        if _truthy(props) and isinstance(props, Mapping) and len(props) > 0:
            required = _nn(schema.get("required"), [])
            fields = []
            for k, v in _js_items(props):
                opt = "" if _includes(required, k) else "?"
                fields.append(f"{k}{opt}: {_json_schema_type_str(v)}")
            return "{" + ", ".join(fields) + "}"
        return "object"
    return "any"


def _default_for_schema(schema: Any) -> Any:
    if not isinstance(schema, Mapping):
        return None
    t = schema.get("type")
    if t == "string":
        return ""
    if t in ("number", "integer"):
        return 0
    if t == "boolean":
        return False
    if t == "array":
        return []
    if t == "object":
        props = schema.get("properties")
        if _truthy(props) and isinstance(props, Mapping) and len(props) > 0:
            return {k: _default_for_schema(v) for k, v in _js_items(props)}
        return {}
    return None


# ─── Built-ins (lang-core parser/builtins.ts, rendered by schemaSignature) ──

_BUILTIN_FUNCTIONS: tuple[tuple[str, str], ...] = (
    ("Count(array: any[]) → number", "Returns array length"),
    ("First(array: any[]) → any", "Returns first element of array"),
    ("Last(array: any[]) → any", "Returns last element of array"),
    ("Sum(numbers: number[]) → number", "Sum of numeric array"),
    ("Avg(numbers: number[]) → number", "Average of numeric array"),
    ("Min(numbers: number[]) → number", "Minimum value in array"),
    ("Max(numbers: number[]) → number", "Maximum value in array"),
    (
        'Sort(array: any[], field: string, direction?: "asc" | "desc") → any[]',
        'Sort array by field. Direction: "asc" (default) or "desc"',
    ),
    (
        'Filter(array: any[], field: string, operator: "==" | "!=" | ">" | "<" | ">=" | "<=" | "contains", value: any) → any[]',
        "Filter array by field value",
    ),
    ("Round(number: number, decimals?: number) → number", "Round to N decimal places (default 0)"),
    ("Abs(number: number) → number", "Absolute value"),
    ("Floor(number: number) → number", "Round down to nearest integer"),
    ("Ceil(number: number) → number", "Round up to nearest integer"),
    (
        "Each(array: any[], varName: string, template: any)",
        "Evaluate template for each element. varName is the loop variable — use it ONLY inside the template expression (inline). Do NOT create a separate statement for the template.",
    ),
)

# (name, signature, description), in prompt order
_BUILTIN_STEPS: tuple[tuple[str, str, str], ...] = (
    (
        "Run",
        "Run(ref: Query | Mutation)",
        "Execute a Mutation or re-fetch a Query (ref must be a declared Query/Mutation)",
    ),
    (
        "ToAssistant",
        "ToAssistant(message: string, context?: any)",
        'Send a message to the assistant (for conversational buttons like "Tell me more", "Explain this"). The optional context is any value (object, array, string, number) passed to the assistant as hidden data, e.g. @ToAssistant("Show details", {orderId: 42})',
    ),
    ("OpenUrl", "OpenUrl(url: string)", "Navigate to a URL"),
    ("Set", "Set(variable: $variable, value: any)", "Set a $variable to a specific value"),
    (
        "Reset",
        "Reset(variable: $variable)",
        'Reset $variables to their declared defaults; pass several to reset each (e.g. @Reset($title, $priority) restores $title="" and $priority="medium")',
    ),
)


# ─── Section generators ─────────────────────────────────────────────────────

PREAMBLE = "You are an AI assistant that responds using openui-lang, a declarative UI language. Your ENTIRE response must be valid openui-lang code — no markdown, no explanations, just openui-lang."


def _syntax_rules(root_name: str, supports_expressions: bool, bindings: bool) -> str:
    lines = [
        "## Syntax Rules",
        "",
        "1. Each statement is on its own line: `identifier = Expression`",
        f"2. `root` is the entry point — every program must define `root = {root_name}(...)`",
        '3. Expressions are: strings ("..."), numbers, booleans (true/false), null, arrays ([...]), objects ({...}), or component calls TypeName(arg1, arg2, ...)',
        "4. Use references for readability: define `name = ...` on one line, then use `name` later",
        "5. EVERY variable (except root) MUST be referenced by at least one other variable. Unreferenced variables are silently dropped and will NOT render. Always include defined variables in their parent's children/items array.",
        '6. Arguments are POSITIONAL (order matters, not names). Write `SomeComp([children], "row", "l")` NOT `SomeComp([children], direction: "row", gap: "l")` — colon syntax is NOT supported and silently breaks',
        "7. Optional arguments can be omitted from the end",
    ]
    n = 8
    if bindings:
        lines.append(
            f"{n}. Declare mutable state with `$varName = defaultValue`. Components marked with `$binding` can read/write these. Undeclared $variables are auto-created with null default."
        )
        n += 1
    if supports_expressions:
        for text in (
            'String concatenation: `"text" + $var + "more"`',
            "Dot member access: `query.field` reads a field; on arrays it extracts that field from every element",
            "Index access: `arr[0]`, `data[index]`",
            "Arithmetic operators: +, -, *, /, % (work on numbers; + is string concat when either side is a string)",
            "Comparison: ==, !=, >, <, >=, <=",
            "Logical: &&, ||, ! (prefix)",
            "Ternary: `condition ? valueIfTrue : valueIfFalse`",
            "Parentheses for grouping: `(a + b) * c`",
        ):
            lines.append(f"{n}. {text}")
            n += 1
    lines.append("- Strings use double quotes with backslash escaping")
    return "\n".join(lines)


def _function_line(signature: Any, description: Any) -> str:
    sig = _js_template(signature)
    return f"@{sig} — {_js_template(description)}" if _truthy(description) else f"@{sig}"


def _entry_line(entry: Any) -> str:
    entry = entry if isinstance(entry, Mapping) else {}
    return _function_line(entry.get("signature"), entry.get("description"))


def _builtin_functions_section(custom: list[str], tool_calls: bool) -> str:
    lines = "\n".join([_function_line(s, d) for s, d in _BUILTIN_FUNCTIONS] + custom)
    on = "Query results" if tool_calls else "data"
    return f"""## Built-in Functions

Data functions prefixed with `@` to distinguish from components. These are the ONLY functions available — do NOT invent new ones.
Use @-prefixed built-in functions (@Count, @Sum, @Avg, @Min, @Max, @Round) on {on}. Do NOT hardcode computed values.

{lines}

Builtins compose — output of one is input to the next:
`@Count(@Filter(data.rows, "field", "==", "val"))` for KPIs/chart values, `@Round(@Avg(data.rows.score), 1)`, `@Each(data.rows, "item", Comp(item.field))` for per-item rendering.
Array pluck: `data.rows.field` extracts a field from every row → use with @Sum, @Avg, charts, tables.

IMPORTANT @Each rule: The loop variable (e.g. "item") is ONLY available inside the @Each template expression. Always inline the template — do NOT extract it to a separate statement.
CORRECT: `list = @Each(rows, "t", Comp(t.name))`
WRONG: `item = Comp(t.name)` then `list = @Each(rows, "t", item)`, because t is undefined in item."""


_QUERY_SECTION = """## Query — Live Data Fetching

Fetch data from available tools. Returns defaults instantly, swaps in real data when it arrives.

```
metrics = Query("tool_name", {arg1: value, arg2: $binding}, {defaultField: 0, defaultData: []}, refreshInterval?)
```

- First arg: tool name (string)
- Second arg: arguments object (may reference $bindings — re-fetches automatically on change)
- Third arg: default data (rendered immediately before fetch resolves)
- Fourth arg (optional): refresh interval in seconds (e.g. 30 for auto-refresh every 30s)
- Use dot access on results: metrics.totalEvents, metrics.data.day (array pluck)
- Query results must use regular identifiers: `metrics = Query(...)`, NOT `$metrics = Query(...)`
- Manual refresh: `Button("Refresh", Action([@Run(query1), @Run(query2)]), "secondary")` — re-fetches the listed queries
- Refresh all queries: create Action with @Run for each query"""

_MUTATION_SECTION = """## Mutation — Write Operations

Execute state-changing tool calls (create, update, delete). Unlike Query (auto-fetches on render), Mutation fires only on button click via Action.

```
result = Mutation("tool_name", {arg1: $binding, arg2: "value"})
```

- First arg: tool name (string)
- Second arg: arguments object (evaluated with current $binding values at click time)
- result.status: "idle" | "loading" | "success" | "error"
- result.data: tool response on success
- result.error: error message on failure
- Mutation results use regular identifiers: `result = Mutation(...)`, NOT `$result`
- Show loading state: `result.status == "loading" ? TextContent("Saving...") : null`"""

_ACTION_HEADER = "## Action — Button Behavior"


def _builtin_steps(tool_calls: bool, bindings: bool) -> list[tuple[str, str, str]]:
    out = []
    for step in _BUILTIN_STEPS:
        name = step[0]
        if name == "Run" and not tool_calls:
            continue
        if name in ("Set", "Reset") and not bindings:
            continue
        out.append(step)
    return out


def _action_section(tool_calls: bool, bindings: bool, custom: list[str]) -> str:
    steps = [f"- {_function_line(sig, desc)}" for _, sig, desc in _builtin_steps(tool_calls, bindings)]
    steps += custom

    examples: list[str] = []
    if tool_calls:
        examples.append(
            """Example — mutation + refresh + reset (PREFERRED pattern):
```
$binding = "default"
result = Mutation("tool_name", {field: $binding})
data = Query("tool_name", {}, {rows: []})
onSubmit = Action([@Run(result), @Run(data), @Reset($binding)])
```"""
        )
    examples.append(
        """Example — simple nav:
```
viewBtn = Button("View", @OpenUrl("https://example.com"))
```"""
    )

    rules = [
        '- An action can be assigned to a variable or inlined: Button("Go", onSubmit) and Button("Go", Action([...])) both work'
    ]
    if tool_calls:
        rules += [
            "- If a @Run(mutation) step fails, remaining steps are skipped (halt on failure)",
            "- @Run(queryRef) re-fetches the query (fire-and-forget, cannot fail)",
        ]

    steps_text = "\n".join(steps)
    examples_text = "\n\n".join(examples)
    rules_text = "\n".join(rules)
    return f"""{_ACTION_HEADER}

An action wires a button click to operations. Pass one @-prefixed step bare, e.g. Button("Ask", @ToAssistant("Tell me more")). Put several steps in Action([...]), e.g. Button("Read", Action([@OpenUrl("https://example.com"), @ToAssistant("Summarize this page")])). Steps execute in order.
Buttons without an action automatically send their label to the assistant (equivalent to @ToAssistant(label)).

Available steps:
{steps_text}

{examples_text}

{rules_text}"""


_INTERACTIVE_FILTERS_SECTION = """## Interactive Filters

To let the user filter data with a dropdown:
1. Declare a $variable with a default: `$dateRange = "14"`
2. Create a Select with name, items, and binding: `Select("dateRange", [SelectItem("7", "Last 7 days"), ...], null, null, $dateRange)`
3. Wrap in FormControl for a label: `FormControl("Date Range", Select(...))`
4. Pass $dateRange in Query args: `Query("tool", {dateRange: $dateRange}, {defaults})`
5. When the user changes the Select, $dateRange updates and the Query automatically re-fetches

FILTER WIRING RULE: If a $binding filter is visible in the UI, EVERY relevant Query MUST reference that $binding in its args. Never show a filter dropdown while hardcoding the query args.

Rules for $variables:
- $variables hold simple values (strings or numbers), NOT arrays or objects
- $variables must be bound to a Select/Input component via the value argument (last positional arg) to be interactive
- Queries must use regular identifiers (NOT $variables): `metrics = Query(...)` not `$metrics = Query(...)`
- **Auto-declare**: You do NOT need to explicitly declare $variables. If you use `$foo` without declaring it, the parser auto-creates `$foo = null`. You can still declare explicitly to set a default: `$days = "14"`

## Forms

Simple form — no $bindings needed. Field values are managed internally by the Form via the name prop:
```
contactForm = Form("contact", submitBtn, [nameField, emailField])
nameField = FormControl("Name", Input("name", "Your name", "text", {required: true}))
emailField = FormControl("Email", Input("email", "your@email.com", "email", {required: true, email: true}))
submitBtn = Button("Submit")
```

Use $bindings when you need to read field values elsewhere (in Action context, Query args, or conditionals). They are auto-declared:
```
$role = "engineer"
contactForm = Form("contact", submitBtn, [nameField, emailField, roleField])
nameField = FormControl("Name", Input("name", "Enter your name", "text", {required: true}, $name))
emailField = FormControl("Email", Input("email", "Enter your email", "email", {required: true, email: true}, $email))
roleField = FormControl("Role", Select("role", [SelectItem("engineer", "Engineer"), SelectItem("designer", "Designer"), SelectItem("pm", "PM")], null, {required: true}, $role))
submitBtn = Button("Submit")
```

For form + mutation patterns (create, refresh, reset), see the Action section example above.

IMPORTANT: Always add validation rules to form fields used with Mutations. Use OBJECT syntax: {required: true, email: true, minLength: 8}. The renderer shows error messages automatically and blocks submit when validation fails."""

_EDIT_MODE_SECTION = """## Edit Mode

The runtime merges by statement name: same name = replace, new name = append.
Output ONLY statements that changed or are new. Everything else is kept automatically.

### Delete
To remove a component, re-declare its parent without that component in the parent's children array. The removed component and any statements only it referenced are automatically garbage-collected.

### Patch size guide
- Changing a title or label: 1 statement
- Adding a component: 2-3 statements (the new component + parent update)
- Removing a component: 1 statement (re-declare parent without the removed child)
- Adding a filter + wiring to query: 3-5 statements
- Restructuring into tabs: 5-10 statements

### Rules
- Reuse existing statement names exactly — do not rename
- Do NOT re-emit unchanged statements — the runtime keeps them
- A typical edit patch is 1-10 statements, not 20+
- If the existing code already satisfies the request, output only the root statement
- NEVER output the entire program as a patch. Only output what actually changes
- If you are about to output more than 10 statements, reconsider — most edits need fewer"""


def _streaming_rules(root_name: str, supports_expressions: bool, tool_calls: bool) -> str:
    steps = [f"1. `root = {root_name}(...)` — UI shell appears immediately"]
    if supports_expressions:
        steps.append("2. $variable declarations — state ready for bindings")
        if tool_calls:
            steps.append("3. Query statements — defaults resolve immediately so components render with data")
        n = len(steps)
        steps.append(f"{n + 1}. Component definitions — fill in with data already available")
        steps.append(f"{n + 2}. Data values — leaf content last")
    else:
        steps.append("2. Component definitions — fill in as they stream")
        steps.append("3. Data values — leaf content last")
    steps_text = "\n".join(steps)
    return f"""## Hoisting & Streaming (CRITICAL)

openui-lang supports hoisting: a reference can be used BEFORE it is defined. The parser resolves all references after the full input is parsed.

During streaming, the output is re-parsed on every chunk. Undefined references are temporarily unresolved and appear once their definitions stream in. This creates a progressive top-down reveal — structure first, then data fills in.

**Recommended statement order for optimal streaming:**
{steps_text}

Always write the root = {root_name}(...) statement first so the UI shell appears immediately, even before child data has streamed in."""


_INLINE_MODE_SECTION = """## Inline Mode

You are in inline mode. You can respond in two ways:

### 1. Code response (when the user wants to CREATE or CHANGE the UI)
Wrap openui-lang code in triple-backtick fences. You can include explanatory text before/after:

Here's your dashboard:

```openui-lang
root = RootComp([header, content])
header = SomeHeader("Title")
content = SomeContent("Hello world")
```

I created a simple layout with a header.

### 2. Text-only response (when the user asks a QUESTION)
If the user asks "what is this?", "explain the chart", "how does this work", etc. — respond with plain text. Do NOT output any openui-lang code. The existing dashboard stays unchanged.

### Rules
- When the user asks for changes, output ONLY the changed/new statements in a fenced block
- When the user asks a question, respond with text only — NO code. The dashboard stays unchanged.
- The parser extracts code from fences automatically. Text outside fences is shown as chat."""

_TOOL_WORKFLOW_SECTION = """## Data Workflow

When tools are available, follow this workflow:
1. FIRST: Call the most relevant tool to inspect the real data shape before generating code
2. Use Query() for READ operations (data that should stay live) — NEVER hardcode tool results as literal arrays or objects
3. Use Mutation() for WRITE operations (create, update, delete) — triggered by button clicks via @Run(mutationRef)
4. Use the real data from step 1 as condensed Query defaults (3-5 rows) so the UI renders immediately
5. Use @-prefixed builtins (@Count, @Filter, @Sort, @Sum) on Query results for KPIs and aggregations — the runtime evaluates these live on every refresh
6. Hardcoded arrays are ONLY for static display data (labels, options) where no tool exists

WRONG — you called a tool and got data back, but you inlined the results:
```
openCount = 2
item1 = SomeComp("first item title")
item2 = SomeComp("second item title")
list = SomeList([item1, item2])
chart = SomeChart(["A", "B"], [12, 8])
```
This is static — it shows stale data and won't update. Creating item1, item2, item3... manually is ALWAYS wrong when a tool exists.

RIGHT — use Query() for live data, Mutation() for writes, @builtins to derive values:
```
data = Query("tool_name", {}, {rows: []})
openCount = @Count(@Filter(data.rows, "field", "==", "value"))
list = @Each(data.rows, "item", SomeComp(item.title, item.field))
createResult = Mutation("create_tool", {title: $title})
submitBtn = Button("Create", Action([@Run(createResult), @Run(data), @Reset($title)]))
```
Everything derives from the Query — when data refreshes, the entire dashboard updates automatically."""


def _important_rules(root_name: str, tool_calls: bool, bindings: bool) -> str:
    verify = [
        f"1. root = {root_name}(...) is the FIRST line (for optimal streaming).",
        "2. Every referenced name is defined. Every defined name (other than root) is reachable from root.",
    ]
    if tool_calls:
        verify.append("3. Every Query result is referenced by at least one component.")
    if bindings:
        verify.append(f"{'4' if tool_calls else '3'}. Every $binding appears in at least one component or expression.")
    if tool_calls and bindings:
        verify.append("5. Every visible filter $binding appears in at least one Query args object.")
    verify_text = "\n".join(verify)
    return f"""## Important Rules
- Choose components that best represent the content (tables for comparisons, charts for trends, forms for input, etc.)

## Final Verification
Before finishing, walk your output and verify:
{verify_text}"""


# ─── Tool rendering ─────────────────────────────────────────────────────────


def _render_tool_signature(tool: Mapping[str, Any]) -> str:
    args = ""
    input_schema = tool.get("inputSchema")
    if _truthy(input_schema):
        props = input_schema.get("properties") if isinstance(input_schema, Mapping) else None
        required = _nn(input_schema.get("required") if isinstance(input_schema, Mapping) else None, [])
        if _truthy(props) and isinstance(props, Mapping) and len(props) > 0:
            args = ", ".join(
                f"{k}{'' if _includes(required, k) else '?'}: {_json_schema_type_str(v)}" for k, v in _js_items(props)
            )
    return_type = ""
    output_schema = tool.get("outputSchema")
    if _truthy(output_schema):
        return_type = f" → {_json_schema_type_str(output_schema)}"
    line = f"- {_js_template(tool.get('name'))}({args}){return_type}"
    if _truthy(tool.get("description")):
        line += f"\n  {_js_template(tool.get('description'))}"
    return line


def _render_tools_section(tools: Sequence[ToolDescriptor]) -> str:
    string_tools = [t for t in tools if isinstance(t, str)]
    spec_tools = [t for t in tools if not isinstance(t, str)]
    lines = [
        "## Available Tools",
        "",
        "Use these with Query() for read operations or Mutation() for write operations. The LLM decides which is appropriate based on the tool's purpose.",
        "",
    ]
    lines += [f"- {t}" for t in string_tools]
    lines += [_render_tool_signature(t) for t in spec_tools]

    with_output = [t for t in spec_tools if _truthy(t.get("outputSchema"))]
    if with_output:
        lines += ["", "### Default values for Query results", "", "Use these shapes as minimal Query defaults:"]
        for t in with_output:
            defaults = _default_for_schema(t.get("outputSchema"))
            lines.append(f"- {_js_template(t.get('name'))}: `{_json_stringify(defaults)}`")

    lines += [
        "",
        "CRITICAL: Use ONLY the tools listed above in Query() and Mutation() calls. Do NOT invent or guess tool names. If the user asks for functionality that doesn't match any available tool, use realistic mock data instead of fabricating a tool call.",
    ]
    return "\n".join(lines)


# ─── Component signatures ───────────────────────────────────────────────────

# A restricted action slot in a signature, e.g. `share?: @CopyToClipboard | @OpenUrl`
_RESTRICTED_SLOT = re.compile(r"[:|] @[A-Z]")


def _sig_of(comp: Any) -> str:
    sig = comp.get("signature") if isinstance(comp, Mapping) else None
    return sig if isinstance(sig, str) else ""


def _component_signatures(
    spec: Mapping[str, Any], tool_calls: bool, bindings: bool, uses_action_expression: bool
) -> str:
    components = spec.get("components") or {}
    lines = [
        "## Component Signatures",
        "",
        "Arguments marked with ? are optional. Sub-components can be inline or referenced; prefer references for better streaming.",
    ]
    if uses_action_expression:
        names = [s[0] for s in _builtin_steps(tool_calls, bindings)] + _js_keys(spec.get("actions") or {})
        all_steps = ", ".join(f"@{n}" for n in names)
        lines.append(
            f"Props typed `ActionExpression` accept one @step, or Action([@steps...]) for several. See the Action section for available steps ({all_steps})."
        )
        if any(_RESTRICTED_SLOT.search(_sig_of(c)) for c in _js_values(components)):
            lines.append("Props typed like `@OpenUrl | @ToAssistant` accept only the steps listed.")
    uses_bindings = bindings or any("$binding" in _sig_of(c) for c in _js_values(components))
    if uses_bindings:
        lines.append("Props marked `$binding<type>` accept a `$variable` reference for two-way binding.")

    def fmt(comp: Any) -> str:
        comp = comp if isinstance(comp, Mapping) else {}
        sig = _js_template(comp.get("signature"))
        desc = comp.get("description")
        return f"{sig} — {_js_template(desc)}" if _truthy(desc) else sig

    groups = spec.get("componentGroups")
    if _length(groups):
        grouped: set[str] = set()
        for group in groups:
            lines += ["", f"### {_js_template(group.get('name'))}"]
            for name in group.get("components") or []:
                if name in grouped:
                    continue
                comp = components.get(name) if isinstance(name, str) else None
                if not _truthy(comp):
                    continue
                grouped.add(name)
                lines.append(fmt(comp))
            notes = group.get("notes")
            if _length(notes):
                lines += [_js_template(n) for n in notes]
        ungrouped = [n for n in _js_keys(components) if n not in grouped]
        if ungrouped:
            lines += ["", "### Other"]
            lines += [fmt(components[n]) for n in ungrouped]
    else:
        lines.append("")
        lines += [fmt(c) for c in _js_values(components)]
    return "\n".join(lines)


# ─── Prompt assembly ────────────────────────────────────────────────────────


def _generate_prompt(spec: Mapping[str, Any]) -> str:
    """Port of ``generatePrompt(spec: PromptSpec)``. ``None`` means undefined."""
    components = spec.get("components") or {}
    root_name = _nn(spec.get("root"), "Root")
    tools = spec.get("tools")
    has_tools = bool(_length(tools))

    tool_calls = bool(_truthy(_nn(spec.get("toolCalls"), has_tools)))
    bindings = bool(_truthy(_nn(spec.get("bindings"), tool_calls)))
    supports_expressions = tool_calls or bindings

    uses_action_expression = any(
        "ActionExpression" in _sig_of(c) or _RESTRICTED_SLOT.search(_sig_of(c))
        for c in _js_values(components)
    )

    parts: list[str] = []
    parts.append(_js_template(_nn(spec.get("preamble"), PREAMBLE)))
    parts.append("")
    parts.append(_syntax_rules(root_name, supports_expressions, bindings))
    parts.append("")
    parts.append(_component_signatures(spec, tool_calls, bindings, uses_action_expression))

    custom_functions = [_entry_line(f) for f in _js_values(spec.get("functions") or {})]
    if _truthy(_nn(spec.get("builtinFunctions"), supports_expressions)):
        parts.append("")
        parts.append(_builtin_functions_section(custom_functions, tool_calls))
    elif custom_functions:
        parts.append("")
        parts.append("## Built-in Functions\n\n" + "\n".join(custom_functions))

    if tool_calls:
        parts += ["", _QUERY_SECTION, "", _MUTATION_SECTION]

    custom_actions = [f"- {_entry_line(a)}" for a in _js_values(spec.get("actions") or {})]
    if uses_action_expression:
        parts.append("")
        parts.append(_action_section(tool_calls, bindings, custom_actions))
    elif custom_actions:
        parts.append("")
        parts.append(
            f"{_ACTION_HEADER}\n\nPass one step, or Action([...]) with several steps, as a button's action.\n\nAvailable steps:\n"
            + "\n".join(custom_actions)
        )

    if tool_calls and bindings:
        parts += ["", _INTERACTIVE_FILTERS_SECTION]
    if tool_calls:
        parts += ["", _TOOL_WORKFLOW_SECTION]
    if has_tools:
        parts += ["", _render_tools_section(list(tools))]

    parts.append("")
    parts.append(_streaming_rules(root_name, supports_expressions, tool_calls))

    all_examples = list(spec.get("examples") or []) + list(spec.get("toolExamples") or [])
    if all_examples:
        parts += ["", "## Examples", ""]
        for ex in all_examples:
            parts.append(_js_template(ex))
            parts.append("")

    if _truthy(spec.get("editMode")):
        parts += ["", _EDIT_MODE_SECTION]
    if _truthy(spec.get("inlineMode")):
        parts += ["", _INLINE_MODE_SECTION]

    # Reference quirk, kept for byte-identity: no blank line before this section
    # unless examples (which end with "") were printed.
    parts.append(_important_rules(root_name, tool_calls, bindings))

    rules = spec.get("additionalRules")
    if _length(rules):
        parts.append("")
        parts += [f"- {_js_template(r)}" for r in rules]

    return "\n".join(parts)


def system_prompt(
    library: Any,
    *,
    tool_calls: bool | None = None,
    bindings: bool | None = None,
    builtin_functions: bool | None = None,
    edit_mode: bool = False,
    inline_mode: bool = False,
    tools: Iterable[ToolDescriptor] | None = None,
    preamble: str | None = None,
    examples: Iterable[str] | None = None,
    tool_examples: Iterable[str] | None = None,
    additional_rules: Iterable[str] | None = None,
) -> str:
    """Render the system prompt for a library (spec/prompt.md section 4).

    Byte-identical to lang-core's ``generateSystemPrompt({ library, promptOptions })``.

    ``library`` is a :class:`genui.library.Library`, a LibrarySpec dict, a JSON
    string, or a path. ``None`` for a flag means "not set" and takes the
    reference default: ``tool_calls`` is on when ``tools`` is non-empty,
    ``bindings`` follows ``tool_calls``, and ``builtin_functions`` is on when
    either is. Passing ``builtin_functions=False`` hides the built-ins even
    with tool calls on, as in the reference.
    """
    from .library import Library

    if isinstance(library, Library):
        spec: Mapping[str, Any] = library.spec
    elif isinstance(library, Mapping):
        spec = library
    else:
        spec = Library.from_spec(library, validate=False).spec

    options = {
        "toolCalls": tool_calls,
        "bindings": bindings,
        "builtinFunctions": builtin_functions,
        "editMode": edit_mode,
        "inlineMode": inline_mode,
        "tools": None if tools is None else list(tools),
        "preamble": preamble,
        "examples": None if examples is None else list(examples),
        "toolExamples": None if tool_examples is None else list(tool_examples),
        "additionalRules": None if additional_rules is None else list(additional_rules),
    }
    # { ...spec.library, ...spec.promptOptions }
    merged = {**dict(spec), **options}
    return _generate_prompt(merged)
