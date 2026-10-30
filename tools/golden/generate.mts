/**
 * Regenerates tests/golden/** from the TypeScript reference implementation
 * (@openuidev/lang-core). Not part of the Python package; nothing here is a
 * runtime dependency of genui.
 *
 * Usage (from a scratch dir that has `zod`, `ci-info` and `tsx` installed and a
 * copy of openui's packages/lang-core/src at ./lang-core-src):
 *
 *   LANG_CORE=/tmp/genui-golden/lang-core-src GENUI=/path/to/genui \
 *     npx tsx /path/to/genui/tools/golden/generate.mts
 *
 * Steps:
 *   1. Builds a few libraries with createLibrary() + zod and writes their
 *      toSpec() output to tests/golden/libraries/<name>.json.
 *   2. For every tests/golden/prompts/<case>.json ({library, options}) writes
 *      generateSystemPrompt({library, promptOptions}) to <case>.txt.
 */
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const LANG_CORE = process.env.LANG_CORE!;
const GENUI = process.env.GENUI!;
if (!LANG_CORE || !GENUI) throw new Error("set LANG_CORE and GENUI");
delete process.env.OPENUI_RUNTIME_TELEMETRY_ENABLED;

const imp = (p: string) => import(pathToFileURL(join(LANG_CORE, p)).href);
// zod must resolve from the scratch dir (same instance lang-core uses)
writeFileSync(join(LANG_CORE, "__genui_zod.ts"), 'export * from "zod/v4";\n');
const { z } = await imp("__genui_zod.ts");
const { createLibrary, defineComponent, defineFunction, defineAction } = await imp("library.ts");
const { generateSystemPrompt } = await imp("parser/prompt.ts");
const { action, steps } = await imp("parser/builtins.ts");
const { markReactive } = await imp("reactive.ts");

const reactive = <T extends object>(s: T): T => (markReactive(s), s);
const comp = (name: string, description: string, props: Record<string, unknown>) =>
  defineComponent({ name, description, props: z.object(props as any), component: null });

// ── Libraries ────────────────────────────────────────────────────────────────

function groupsLibrary() {
  const Text = comp("Text", "A run of text", { text: z.string(), size: z.enum(["s", "m", "l"]).optional() });
  const Image = comp("Image", "", { src: z.string(), alt: z.string().optional() });
  const Badge = comp("Badge", "A small label", { label: z.string() });
  const Chart = comp("Chart", "A line chart; values are plotted in order", {
    labels: z.array(z.string()),
    series: z.array(z.object({ name: z.string(), values: z.array(z.number()) })),
    height: z.number().default(240),
  });
  const Stack = comp("Stack", "Vertical or horizontal layout", {
    children: z.array(z.union([Text.ref, Image.ref, Badge.ref, Chart.ref])),
    direction: z.enum(["row", "column"]).optional(),
    gap: z.number().nullable(),
  });
  const Page = comp("Page", "The page shell", { title: z.string(), body: z.array(Stack.ref) });
  return createLibrary({
    id: "groups",
    root: "Page",
    components: [Page, Stack, Text, Image, Badge, Chart],
    componentGroups: [
      { name: "Layout", components: ["Page", "Stack"], notes: ["- Use Stack for every row of content.", "- Page must be the root."] },
      { name: "Content", components: ["Text", "Image", "Text", "Missing"] },
      { name: "Empty notes", components: ["Image"], notes: [] },
    ],
  });
}

function customCallsLibrary() {
  const Text = comp("Text", "A run of text", { text: z.string() });
  const Card = comp("Card", "A titled container", { title: z.string(), children: z.array(Text.ref).optional() });
  const percent = defineFunction({
    name: "Percent",
    description: "Format part / total as a percentage",
    params: z.object({ part: z.number(), total: z.number(), digits: z.number().optional() }),
    returns: z.string(),
    fn: () => "",
  });
  const join = defineFunction({
    name: "Join",
    description: "",
    params: z.object({ items: z.array(z.string()), sep: z.string().optional() }),
    fn: () => "",
  });
  const copy = defineAction({
    name: "CopyToClipboard",
    description: "Copy text to the clipboard",
    params: z.object({ text: z.string() }),
  });
  const track = defineAction({
    name: "Track",
    description: "Send an analytics event",
    params: z.object({ event: z.string(), props: z.record(z.string(), z.any()).optional() }),
  });
  return createLibrary({ root: "Card", components: [Card, Text], functions: [percent, join], actions: [copy, track] });
}

function restrictedLibrary() {
  const copy = defineAction({
    name: "CopyToClipboard",
    description: "Copy text to the clipboard",
    params: z.object({ text: z.string() }),
  });
  const Link = comp("Link", "A link that can only navigate", {
    label: z.string(),
    to: z.union([steps.OpenUrl.ref]),
  });
  const ShareButton = comp("ShareButton", "Copy or open a URL", {
    label: z.string(),
    share: z.union([copy.ref, steps.OpenUrl.ref]).optional(),
    ask: z.union([steps.ToAssistant.ref]).optional(),
  });
  const Row = comp("Row", "A row", { items: z.array(z.union([Link.ref, ShareButton.ref])) });
  return createLibrary({ id: "restricted", root: "Row", components: [Row, Link, ShareButton], actions: [copy] });
}

function bindingsLibrary() {
  const SelectItem = comp("SelectItem", "One option", { value: z.string(), label: z.string() });
  const Select = comp("Select", "A dropdown", {
    name: z.string(),
    items: z.array(SelectItem.ref),
    placeholder: z.string().nullable(),
    rules: z.object({ required: z.boolean().optional(), min: z.number().optional() }).optional(),
    value: reactive(z.string().optional()),
  });
  const Toggle = comp("Toggle", "An on/off switch", {
    label: z.string(),
    on: reactive(z.boolean().optional()),
    tags: reactive(z.array(z.string()).optional()),
  });
  const Button = comp("Button", "A clickable button", {
    label: z.string(),
    action: action().optional(),
    variant: z.enum(["primary", "secondary"]).optional(),
    meta: z.record(z.string(), z.number()).optional(),
    kind: z.literal("submit").optional(),
    count: z.literal(3).optional(),
  });
  const Form = comp("Form", "A form", {
    name: z.string(),
    fields: z.array(z.union([Select.ref, Toggle.ref])),
    submit: Button.ref.optional(),
    anything: z.any().optional(),
  });
  return createLibrary({ id: "bindings", root: "Form", components: [Form, Select, SelectItem, Toggle, Button] });
}

const libraries: Record<string, any> = {
  groups: groupsLibrary(),
  custom_calls: customCallsLibrary(),
  restricted: restrictedLibrary(),
  bindings: bindingsLibrary(),
};
for (const [name, lib] of Object.entries(libraries)) {
  writeFileSync(join(GENUI, "tests/golden/libraries", `${name}.json`), JSON.stringify(lib.toSpec(), null, 2) + "\n");
}

// ── Prompts ──────────────────────────────────────────────────────────────────

const casesDir = join(GENUI, "tests/golden/prompts");
let n = 0;
for (const file of readdirSync(casesDir).filter((f) => f.endsWith(".json")).sort()) {
  const input = JSON.parse(readFileSync(join(casesDir, file), "utf8"));
  const library = JSON.parse(readFileSync(join(GENUI, input.library), "utf8"));
  const prompt = generateSystemPrompt({ library, promptOptions: input.options ?? {} });
  writeFileSync(join(casesDir, file.replace(/\.json$/, ".txt")), prompt);
  n++;
}
console.log(`wrote ${Object.keys(libraries).length} libraries, ${n} prompts`);
