import { render } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { GenUIChat } from "genui-react";

beforeAll(() => {
  // jsdom lacks these browser APIs used by the chat layout.
  window.matchMedia ??= ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
  Element.prototype.scrollTo ??= () => {};
});

describe("GenUIChat", () => {
  it("mounts without a backend call", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { container } = render(<GenUIChat url="/api/chat" agentName="genui test" storageKey={false} className="chat" />);
    const root = container.querySelector("[data-genui-chat]");
    expect(root).toBeTruthy();
    expect(root?.className).toBe("chat");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
