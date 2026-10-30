# genui.lang compatibility with the OpenUI TypeScript reference

`genui.lang` follows the reference implementation (`@openuidev/lang-core`
1.0, `packages/lang-core/src/parser` and `src/runtime`) wherever it differs
from the prose of `spec/language.md`. That way a Python backend agrees with the
TypeScript renderer. All 59 conformance fixtures in `spec/fixtures/1.0` pass.

It was checked by differential testing against the reference sources: about
30,000 random programs, random chunkings, and random edit merges. Parse
results, evaluated trees, errors (including message text), unresolved names,
orphans, `incomplete`, state defaults, streaming results, and merged text were
all compared.

## Where the reference differs from the spec prose (genui follows the reference)

- **Fences:** an opening fence is three backticks anywhere outside a
  double-quoted string, not only at the start of a line. Double-quoted strings
  in prose also shield backticks.
- **Multi-line ternaries:** a newline right after a ternary's `:` ends the
  statement. The edit merge does not follow multi-line ternaries at all.
- **Brackets:** when splitting statements, any closing bracket lowers the
  depth, matched or not. Implicit closing only pops a matching opener.
- **Stream end:** a pending statement that needed implicit closing never
  replaces a completed statement with the same name, even at stream end. In
  that case the streamed result differs from a batch parse of the same text
  (the reference behaves the same way).
- **Arrays in computed expressions:** an unresolved reference evaluates to
  `null` in place. It is not left out.
- **Edit merge:** text is read raw. Comments are not stripped, the patch only
  has its fences extracted, and the first statement of each chunk is used. A
  duplicate name in the existing program is emitted twice.
- **Errors and state:** a prop that throws keeps its unevaluated value, and its
  summary is the AST's JSON. `parse-failed` is never reported, and an empty
  program has `incomplete: true`. State defaults are stored as materialized:
  expressions are kept in the reference's AST JSON shape (`{"k": ...}`) and
  components as elements.
- **Shape-based objects:** data shaped like a runtime object is treated as one.
  `{steps: [...]}` is an action plan, `{type: "element", typeName, props,
  partial}` is an element, `{__reactive: "assign"}` is a binding, and
  `{k: <kind>}` is an AST node. Any object with a `type` key inside
  `Action([...])` is a step.
- **Summary:** `@ToAssistant`'s context and `@Set`'s value are emitted raw
  (JSON only), as the reference conformance runner does.

## Known remaining differences

1. **JavaScript `undefined` is not modelled.** It is `None`, like `null`. The
   difference shows in two places. `@Sort` moves `undefined` elements to the
   end without comparing them. JSON output drops object keys whose value is
   `undefined`, for example `{k: "s".name}` gives `{}` in the reference and
   `{"k": null}` here.
2. **`@Sort` string collation** approximates ICU root collation
   (`localeCompare` with no arguments). It matches exactly for ASCII
   (punctuation order taken from ICU), letters, and common Latin accents. Other
   scripts and rarer characters may order differently.
3. **Self-containing values** (`$x = Stack([$x])`). The reference overflows its
   stack and reports `runtime-error` on the enclosing prop after nesting
   thousands of levels deep. genui detects the cycle on the first repeat and
   reports `runtime-error` there, so the nesting depth in the tree differs.
4. **Exceptions are always contained.** The reference's `parser.parse()`
   rethrows parser exceptions, and `evaluateRoot` can throw from a runtime
   entry. genui returns a `parse-exception` error, or a runtime `no-root`,
   instead.
5. **Serialization** (`serialize`, the reference's `jsonToOpenUI`). genui
   writes action plans as `@Step(...)` / `Action([...])` and bindings as
   `$name`, quotes object keys that are not valid names, and adds parentheses
   when operator precedence needs them. The reference writes plans and
   bindings as raw objects (`{steps: [...]}`, `{__reactive: ...}`), which do
   not parse back. Output is identical for trees without actions, bindings, or
   such keys.
6. **Hints.** genui adds a `hint` to parser errors (signatures, available
   names). The reference only does this through its deprecated
   `enrichErrors`. `message` text matches the reference.
7. **Element-shaped data outside props.** An element-shaped object literal is
   recognized as the entry and in props, as in the reference. Only AST-shaped
   object literals used *as the entry* are not walked for components.
8. **Validation rule `pattern`** uses Python `re`. ECMAScript `$` and named
   groups are translated. Other JS-only regex syntax may behave differently.
