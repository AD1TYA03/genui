import type { ReplayState } from "../lib/stream";
import { PauseIcon, PlayIcon, ReplayIcon, SkipIcon } from "./icons";

export const SPEEDS = [0.5, 1, 2, 4] as const;

export function ReplayControls({
  replay,
  speed,
  setSpeed,
  total,
}: {
  replay: ReplayState;
  speed: number;
  setSpeed: (s: number) => void;
  total: number;
}) {
  const { playing, done, shown } = replay;
  return (
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:gap-3">
      <button
        onClick={playing ? replay.pause : done ? replay.replay : replay.play}
        className="inline-flex h-9 min-w-[96px] items-center justify-center gap-2 rounded-lg bg-fg px-3.5 text-sm font-semibold text-ink transition hover:bg-white"
      >
        {playing ? <PauseIcon /> : done ? <ReplayIcon /> : <PlayIcon />}
        {playing ? "Pause" : done ? "Replay" : shown > 0 ? "Resume" : "Play"}
      </button>
      <button
        onClick={replay.replay}
        className="grid size-9 place-items-center rounded-lg border border-line-strong text-muted transition hover:bg-white/5 hover:text-fg"
        aria-label="Restart"
        title="Restart"
      >
        <ReplayIcon />
      </button>
      <button
        onClick={replay.finish}
        disabled={done}
        className="grid size-9 place-items-center rounded-lg border border-line-strong text-muted transition hover:bg-white/5 hover:text-fg disabled:opacity-40"
        aria-label="Skip to end"
        title="Skip to end"
      >
        <SkipIcon />
      </button>
      <div className="flex h-9 items-center rounded-lg border border-line-strong p-0.5" role="radiogroup" aria-label="Playback speed">
        {SPEEDS.map((s) => (
          <button
            key={s}
            role="radio"
            aria-checked={speed === s}
            onClick={() => setSpeed(s)}
            className={`h-full rounded-md px-2.5 font-mono text-xs transition ${
              speed === s ? "bg-white/10 text-fg" : "text-dim hover:text-muted"
            }`}
          >
            {s}×
          </button>
        ))}
      </div>
      <div className="flex min-w-[180px] flex-1 basis-[180px] items-center gap-3">
        <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/[0.07]">
          <div className="absolute inset-y-0 left-0 rounded-full bg-cyan-300 transition-[width] duration-100" style={{ width: `${(shown / total) * 100}%` }} />
        </div>
        <span className="whitespace-nowrap font-mono text-[11px] tabular-nums text-dim">
          {shown.toLocaleString()} / {total.toLocaleString()} chars
        </span>
      </div>
    </div>
  );
}
