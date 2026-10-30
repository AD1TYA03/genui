// Must be imported before @openuidev/react-lang: in demo/screenshot mode, mark the OpenUI
// devtools widget as already mounted so its floating button stays out of the frame.
if (new URLSearchParams(window.location.search).has("demo") || new URLSearchParams(window.location.search).has("shot")) {
  (globalThis as Record<symbol, unknown>)[Symbol.for("openui.devtools.autoMount")] = true;
}
export {};
