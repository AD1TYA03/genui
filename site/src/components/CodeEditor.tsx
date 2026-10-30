import { useMemo, useRef, type KeyboardEvent } from "react";
import { Highlight } from "../lib/highlight";

const LINE_H = 21; // px, keep in sync with leading below

export function CodeEditor({
  value,
  onChange,
  errorLines,
  label = "OpenUI Lang editor",
}: {
  value: string;
  onChange: (v: string) => void;
  errorLines: Set<number>;
  label?: string;
}) {
  const ta = useRef<HTMLTextAreaElement>(null);
  // Tab indents; press Escape first to let Tab move focus out (no keyboard trap).
  const released = useRef(false);
  const lines = useMemo(() => value.split("\n"), [value]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") {
      released.current = true;
      return;
    }
    if (e.key !== "Tab") released.current = false;
    if (e.key === "Tab" && !e.shiftKey && !released.current) {
      e.preventDefault();
      const el = e.currentTarget;
      const { selectionStart: s, selectionEnd: end } = el;
      const next = value.slice(0, s) + "  " + value.slice(end);
      onChange(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = s + 2;
      });
    }
  };

  return (
    <div className="scrollbar-thin relative h-full overflow-auto bg-black/25" onClick={() => ta.current?.focus()}>
      <div className="flex min-h-full w-max min-w-full font-mono text-[12.5px]" style={{ lineHeight: `${LINE_H}px` }}>
        <div
          aria-hidden
          className="sticky left-0 z-10 select-none border-r border-line bg-ink-2 py-4 pl-3 pr-3 text-right tabular-nums text-dim/70"
        >
          {lines.map((_, i) => (
            <div key={i} className={errorLines.has(i) ? "text-red-300" : undefined}>
              {i + 1}
            </div>
          ))}
        </div>
        <div className="relative flex-1">
          {/* error line highlights */}
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-4">
            {[...errorLines].map((l) => (
              <div key={l} className="absolute inset-x-0 bg-red-500/10" style={{ top: l * LINE_H, height: LINE_H }} />
            ))}
          </div>
          <span id="editor-kbd-hint" className="sr-only">
            Tab inserts two spaces. Press Escape, then Tab, to leave the editor.
          </span>
          <pre aria-hidden className="relative whitespace-pre py-4 pl-4 pr-8 text-fg">
            <Highlight code={value + "\n"} lang="oui" />
          </pre>
          <textarea
            ref={ta}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            aria-label={label}
            aria-describedby="editor-kbd-hint"
            wrap="off"
            className="absolute inset-0 resize-none overflow-hidden whitespace-pre bg-transparent py-4 pl-4 pr-8 text-transparent caret-cyan-300 outline-none selection:bg-violet-500/40"
            style={{ lineHeight: `${LINE_H}px` }}
          />
        </div>
      </div>
    </div>
  );
}
