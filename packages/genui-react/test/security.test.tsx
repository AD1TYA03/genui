import { render } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { GenUIChat, clearChatHistory, safeUrl } from "genui-react";
import { guardWindowOpen } from "../src/safeUrl";

beforeAll(() => {
  window.matchMedia ??= ((query: string) => ({
    matches: false, media: query, onchange: null, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
  globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver;
  Element.prototype.scrollTo ??= () => {};
});

describe("safeUrl", () => {
  it("allows web, mail, phone and relative links", () => {
    for (const u of ["https://zoho.com/x", "http://a.b", "mailto:a@b.c", "tel:+911234", "/deals/42", "?q=1", "#top", "//cdn.example.com/a"])
      expect(safeUrl(u)).toBe(u);
  });
  it("rejects script and local schemes, including obfuscated ones", () => {
    for (const u of ["javascript:alert(1)", "JavaScript:alert(1)", " javascript:alert(1)", "java\tscript:alert(1)",
      "java\nscript:x", "\u0001javascript:x", "data:text/html,<script>x</script>", "vbscript:x", "file:///etc/passwd", "blob:x", "", 42, null])
      expect(safeUrl(u)).toBeUndefined();
  });
});

describe("guardWindowOpen", () => {
  afterEach(() => vi.restoreAllMocks());

  it("blocks unsafe URLs, adds noopener, and restores window.open", () => {
    const native = vi.fn(() => null);
    window.open = native as unknown as typeof window.open;
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const off = guardWindowOpen();
    expect(window.open("javascript:alert(1)", "_blank")).toBeNull();
    expect(native).not.toHaveBeenCalled();
    window.open("https://zoho.com", "_blank");
    expect(native).toHaveBeenLastCalledWith("https://zoho.com", "_blank", "noopener,noreferrer");
    window.open("https://zoho.com", "_self", "popup");
    expect(native).toHaveBeenLastCalledWith("https://zoho.com", "_self", "popup");
    off();
    off(); // idempotent
    expect(window.open).toBe(native);
  });

  it("is installed by GenUIChat while mounted", () => {
    const native = vi.fn(() => null);
    window.open = native as unknown as typeof window.open;
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const { unmount } = render(<GenUIChat storageKey={false} />);
    expect(window.open).not.toBe(native);
    window.open("javascript:alert(1)", "_blank");
    expect(native).not.toHaveBeenCalled();
    unmount();
    expect(window.open).toBe(native);
  });
});

describe("clearChatHistory", () => {
  it("removes only this namespace's threads and messages", () => {
    // An in-memory Storage: Node 22+ ships its own global localStorage that shadows jsdom's.
    const data = new Map<string, string>();
    const storage = {
      get length() { return data.size; },
      key: (i: number) => [...data.keys()][i] ?? null,
      getItem: (k: string) => data.get(k) ?? null,
      setItem: (k: string, v: string) => void data.set(k, v),
      removeItem: (k: string) => void data.delete(k),
      clear: () => data.clear(),
    };
    vi.stubGlobal("localStorage", storage);
    localStorage.setItem("genui:threads", "[]");
    localStorage.setItem("genui:messages:t1", "[]");
    localStorage.setItem("other:threads", "[]");
    localStorage.setItem("genuix:threads", "[]");
    clearChatHistory();
    expect(localStorage.getItem("genui:threads")).toBeNull();
    expect(localStorage.getItem("genui:messages:t1")).toBeNull();
    expect(localStorage.getItem("other:threads")).toBe("[]");
    expect(localStorage.getItem("genuix:threads")).toBe("[]");
    vi.unstubAllGlobals();
  });
});
