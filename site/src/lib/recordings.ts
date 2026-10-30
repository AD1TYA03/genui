import index from "../recordings/index.json";

export interface Recording {
  id: string;
  title: string;
  description: string;
  prompt: string;
  file: string;
  model: string;
  components: string[];
  recordedAt: string;
  source: string;
}

const files = import.meta.glob("../recordings/*.oui", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

export const recordings: Recording[] = index.map((r) => ({
  ...r,
  source: (files[`../recordings/${r.file}`] ?? "").trimEnd(),
}));

export function getRecording(id: string | null | undefined): Recording | undefined {
  return recordings.find((r) => r.id === id);
}
