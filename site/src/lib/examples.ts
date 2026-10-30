import index from "../examples/index.json";

/** Example OpenUI Lang programs offered as presets in the playground editor. */
export interface Example {
  id: string;
  title: string;
  file: string;
  source: string;
}

const files = import.meta.glob("../examples/*.oui", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export const examples: Example[] = index.map((e) => ({
  ...e,
  source: (files[`../examples/${e.file}`] ?? "").trimEnd(),
}));

export function getExample(id: string | null | undefined): Example | undefined {
  return examples.find((e) => e.id === id);
}
