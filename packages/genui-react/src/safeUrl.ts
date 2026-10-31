// URLs in rendered UI come from the model, so treat them as untrusted input.

const ALLOWED_SCHEMES = new Set(["http:", "https:", "mailto:", "tel:"]);
// Browsers ignore ASCII control characters and whitespace inside a scheme ("java\tscript:").
const IGNORED = /[\u0000- \u007f-\u009f]/g;
const SCHEME = /^([a-z][a-z0-9+.-]*):/i;

/**
 * The URL if it is safe to open from model output, else `undefined`.
 *
 * Allows `http:`, `https:`, `mailto:`, `tel:` and relative URLs. Rejects
 * `javascript:`, `data:`, `vbscript:`, `file:` and every other scheme,
 * including control-character obfuscation.
 */
export function safeUrl(url: unknown): string | undefined {
  if (typeof url !== "string") return undefined;
  const trimmed = url.trim();
  if (!trimmed) return undefined;
  const scheme = SCHEME.exec(trimmed.replace(IGNORED, ""));
  if (scheme && !ALLOWED_SCHEMES.has(scheme[1]!.toLowerCase() + ":")) return undefined;
  return trimmed;
}

/** Open a model-provided URL in a new tab, safely: checked by {@link safeUrl}, with `noopener,noreferrer`. */
export function safeOpenUrl(url: unknown): Window | null {
  if (typeof window === "undefined") return null;
  const safe = safeUrl(url);
  return safe ? window.open(safe, "_blank", "noopener,noreferrer") : null;
}

type Open = typeof window.open;
let guards = 0;
let original: Open | null = null;

/**
 * Route `window.open` through {@link safeUrl} while at least one guard is installed.
 *
 * OpenUI's chat opens `@OpenUrl(...)` links with a bare `window.open(url, "_blank")`,
 * which neither checks the scheme nor sets `noopener`. `<GenUIChat>` installs this guard
 * while mounted. Unsafe URLs are refused (returns `null`); `_blank` opens get
 * `noopener,noreferrer` unless the caller passed features. Returns the uninstall function.
 */
export function guardWindowOpen(): () => void {
  if (typeof window === "undefined") return () => {};
  if (guards++ === 0) {
    original = window.open;
    const native = original;
    window.open = function guardedOpen(url?: string | URL, target?: string, features?: string) {
      const raw = url instanceof URL ? url.href : url;
      if (raw === undefined || raw === "") return native.call(window, raw, target, features);
      const safe = safeUrl(raw);
      if (!safe) {
        console.warn("genui-react: blocked an unsafe URL from opening:", String(raw).slice(0, 80));
        return null;
      }
      const blank = target === undefined || target === "_blank";
      return native.call(window, safe, target ?? "_blank", features ?? (blank ? "noopener,noreferrer" : undefined));
    } as Open;
  }
  let done = false;
  return () => {
    if (done) return;
    done = true;
    if (--guards === 0 && original) {
      window.open = original;
      original = null;
    }
  };
}
