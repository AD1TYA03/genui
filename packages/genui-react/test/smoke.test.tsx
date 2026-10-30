import { render, screen, waitFor } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
// Self-reference: resolves through package.json "exports" to the built dist/.
import { defaultLibrary, genuiLLM, GenUIRenderer, localStorageChat } from "genui-react";

const program = 'root = TextContent("Hello from genui")';

describe("GenUIRenderer", () => {
  it("renders an OpenUI Lang program in the DOM", async () => {
    render(<GenUIRenderer response={program} />);
    await waitFor(() => expect(screen.getByText("Hello from genui")).toBeTruthy());
  });

  it("renders to a string on the server", () => {
    const html = renderToString(<GenUIRenderer response={program} library={defaultLibrary} />);
    expect(html).toContain("Hello from genui");
  });

  it("renders nothing for a null response", () => {
    const { container } = render(<GenUIRenderer response={null} />);
    expect(container.textContent).toBe("");
  });
});

describe("genuiLLM", () => {
  it("POSTs the AG-UI run input to the url", async () => {
    const fetchMock = vi.fn(async () => new Response("", { status: 200 }));
    const llm = genuiLLM({
      url: "/api/chat",
      headers: { Authorization: "Bearer t" },
      body: { model: "x" },
      fetch: fetchMock as unknown as typeof fetch,
    });
    await llm.send({
      threadId: "t1",
      messages: [{ id: "m1", role: "user", content: "hi" }],
      signal: new AbortController().signal,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/chat");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer t");
    const sent = JSON.parse(String(init.body));
    expect(sent.threadId).toBe("t1");
    expect(sent.model).toBe("x");
    expect(sent.messages[0].content).toBe("hi");
    expect(sent).toHaveProperty("runId");
  });

  it("rejects unknown formats", () => {
    expect(() => genuiLLM({ url: "/x", format: "nope" as never })).toThrow(/unknown format/);
  });
});

describe("localStorageChat", () => {
  it("creates, lists and deletes threads", async () => {
    // Node 22+ ships its own (file-backed) localStorage global that shadows jsdom's; use a Map.
    const mem = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => void mem.set(k, v),
      removeItem: (k: string) => void mem.delete(k),
    });
    const { storage } = localStorageChat(genuiLLM({ url: "/x" }), "test");
    const thread = await storage.thread!.createThread({ id: "u1", role: "user", content: "Plan a trip" });
    expect(thread.title).toBe("Plan a trip");
    expect((await storage.thread!.listThreads()).threads).toHaveLength(1);
    await storage.thread!.deleteThread(thread.id);
    expect((await storage.thread!.listThreads()).threads).toHaveLength(0);
    vi.unstubAllGlobals();
  });
});
