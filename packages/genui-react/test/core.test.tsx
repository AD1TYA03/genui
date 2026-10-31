import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { z } from "zod";
// Self-reference: resolves through package.json "exports" to the built dist/core.js.
import { GenUIRenderer, createLibrary, defineComponent, genuiLLM, safeUrl } from "genui-react/core";

const Deal = defineComponent({
  name: "Deal",
  description: "A CRM deal",
  props: z.object({ title: z.string(), amount: z.number() }),
  component: ({ props }) => <div>{`${props.title}: ${props.amount}`}</div>,
});
const library = createLibrary({ components: [Deal], root: "Deal" });

describe("genui-react/core", () => {
  it("renders a custom component library", async () => {
    render(<GenUIRenderer response='root = Deal("Acme", 5000)' library={library} />);
    await waitFor(() => expect(screen.getByText("Acme: 5000")).toBeTruthy());
  });

  it("exports the transport and safety helpers", () => {
    expect(typeof genuiLLM({ url: "/api/chat" }).send).toBe("function");
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
  });

  it("never imports OpenUI's default component library", () => {
    const dist = join(__dirname, "..", "dist");
    const seen = new Set<string>();
    const visit = (file: string) => {
      if (seen.has(file)) return;
      seen.add(file);
      const code = readFileSync(join(dist, file), "utf8");
      expect(code, `${file} imports react-ui`).not.toMatch(/@openuidev\/react-ui/);
      for (const m of code.matchAll(/from\s+['"]\.\/([^'"]+)['"]|import\s+['"]\.\/([^'"]+)['"]/g)) visit(m[1] ?? m[2]!);
    };
    visit("core.js");
    expect(seen.size).toBeGreaterThan(1); // followed the shared chunk too
    expect(readdirSync(dist)).toContain("core.d.ts");
  });
});
