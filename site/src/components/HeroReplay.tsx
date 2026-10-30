import { useEffect, useRef, useState } from "react";
import { getRecording, type Recording } from "../lib/recordings";
import { useReplay } from "../lib/stream";
import { LazyFrame } from "./LazyFrame";
import { StreamingCode } from "./StreamingCode";

const SEQUENCE = ["travel-booking", "analytics-dashboard", "support-triage"]
  .map((id) => getRecording(id))
  .filter(Boolean) as Recording[];

const HOLD_MS = 4000;

export function HeroReplay() {
  const [idx, setIdx] = useState(0);
  const rec = SEQUENCE[idx];
  const replay = useReplay(rec.source, { speed: 1.8, autoplay: true, seed: 11 + idx });
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!replay.done) return;
    const t = window.setTimeout(() => setIdx((i) => (i + 1) % SEQUENCE.length), HOLD_MS);
    return () => window.clearTimeout(t);
  }, [replay.done]);

  // Follow the UI as it grows.
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    if (replay.shown === 0) el.scrollTop = 0;
    else if (replay.playing) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [replay.text, replay.playing, replay.shown]);

  return (
    <figure className="overflow-hidden rounded-2xl border border-line bg-ink-2" aria-label="Live replay of an agent response">
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <p className="min-w-0 flex-1 truncate text-[13px] text-muted">
          <span className="mr-2 text-dim">Prompt</span>
          {rec.prompt}
        </p>
        <div className="flex shrink-0 gap-1.5">
          {SEQUENCE.map((r, i) => (
            <button
              key={r.id}
              onClick={() => setIdx(i)}
              aria-label={`Replay ${r.title}`}
              aria-current={i === idx}
              className="grid size-6 place-items-center rounded"
            >
              <span className={`block h-1.5 rounded-full transition-all ${i === idx ? "w-4 bg-fg" : "w-1.5 bg-white/20"}`} />
            </button>
          ))}
        </div>
      </div>

      <div ref={scroller} className="scrollbar-thin h-[340px] overflow-y-auto overscroll-contain p-4 sm:h-[400px] sm:p-5">
        {replay.shown === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-dim">Waiting for the first token…</div>
        ) : (
          <LazyFrame response={replay.text} isStreaming={replay.playing} />
        )}
      </div>

      <figcaption className="border-t border-line bg-black/30">
        <div className="flex items-center justify-between px-4 pt-2.5 text-[11px] text-dim">
          <span className="inline-flex items-center gap-1.5">
            <span className={`size-1.5 rounded-full ${replay.playing ? "bg-cyan-300" : "bg-white/30"}`} />
            {replay.playing ? "Streaming OpenUI Lang" : "Rendered"}
          </span>
          <span className="font-mono tabular-nums">{replay.shown.toLocaleString()} chars</span>
        </div>
        <StreamingCode text={replay.text} streaming={!replay.done} className="h-[66px] px-4 pb-2.5 pt-1 text-[11px]" />
      </figcaption>
    </figure>
  );
}
