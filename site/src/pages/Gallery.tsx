import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useActionToast } from "../components/ActionToast";
import { CodeIcon } from "../components/icons";
import { LazyFrame } from "../components/LazyFrame";
import { ReplayControls } from "../components/ReplayControls";
import { StreamingCode } from "../components/StreamingCode";
import { getRecording, recordings } from "../lib/recordings";
import { useReplay } from "../lib/stream";
import { useTitle } from "../lib/useTitle";

export default function Gallery() {
  useTitle("Gallery");
  const [params, setParams] = useSearchParams();
  const rec = getRecording(params.get("example")) ?? recordings[0];
  const [speed, setSpeed] = useState(1);
  const [showCode, setShowCode] = useState(params.get("code") === "1");
  const replay = useReplay(rec.source, { speed, autoplay: true });
  const { onAction, toast } = useActionToast();

  const select = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("example", id);
    setParams(next, { replace: true });
  };

  return (
    <div className="mx-auto max-w-6xl px-5 pb-10 pt-10 sm:px-8 sm:pt-14">
      <header className="mb-10 max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">Gallery</h1>
        <p className="mt-3 text-pretty text-[17px] leading-relaxed text-muted">
          Real model answers, replayed chunk by chunk through <code className="font-mono text-[0.88em] text-fg">GenUIRenderer</code>.
        </p>
      </header>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-10">
        {/* Picker */}
        <nav aria-label="Examples" className="min-w-0">
          <ul className="scrollbar-thin -mx-5 flex gap-1 overflow-x-auto px-5 pb-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0 lg:pb-0">
            {recordings.map((r) => {
              const active = r.id === rec.id;
              return (
                <li key={r.id} className="shrink-0">
                  <button
                    onClick={() => select(r.id)}
                    aria-current={active ? "page" : undefined}
                    className={`relative w-full whitespace-nowrap rounded-lg px-3 py-2 text-left text-sm transition lg:py-2.5 ${
                      active ? "bg-white/[0.06] font-medium text-fg" : "text-muted hover:bg-white/[0.03] hover:text-fg"
                    }`}
                  >
                    {active && <span aria-hidden className="absolute inset-y-2 left-0 hidden w-0.5 rounded-full bg-cyan-300 lg:block" />}
                    {r.title}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Stage */}
        <section className="min-w-0" aria-label={rec.title}>
          <div className="overflow-hidden rounded-2xl border border-line bg-ink-2">
            {/* Prompt */}
            <div className="border-b border-line px-5 py-5 sm:px-6">
              <p className="mb-1.5 text-xs font-medium text-dim">Prompt</p>
              <p className="text-pretty text-[15px] leading-relaxed text-fg">{rec.prompt}</p>
            </div>
            {/* Controls */}
            <div className="flex flex-col gap-3 border-b border-line px-5 py-3 sm:px-6 md:flex-row md:items-center">
              <ReplayControls replay={replay} speed={speed} setSpeed={setSpeed} total={rec.source.length} />
              <button
                onClick={() => setShowCode((s) => !s)}
                aria-pressed={showCode}
                className={`inline-flex h-9 shrink-0 items-center gap-2 self-start rounded-lg border px-3 text-sm font-medium transition md:self-auto ${
                  showCode ? "border-white/25 bg-white/[0.06] text-fg" : "border-line-strong text-muted hover:bg-white/5 hover:text-fg"
                }`}
              >
                <CodeIcon /> View OpenUI Lang
              </button>
            </div>
            {/* Output */}
            <div className={`grid ${showCode ? "xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]" : ""}`}>
              {showCode && (
                <div className="border-b border-line bg-black/30 xl:border-b-0 xl:border-r">
                  <StreamingCode
                    text={replay.done ? rec.source : replay.text}
                    streaming={replay.playing}
                    className="max-h-[420px] p-5 xl:max-h-[760px]"
                  />
                </div>
              )}
              <div className="min-h-[420px] min-w-0 p-4 sm:p-6">
                {replay.shown === 0 ? (
                  <div className="flex h-[360px] items-center justify-center text-sm text-dim">Waiting for the first token…</div>
                ) : (
                  <LazyFrame response={replay.text} isStreaming={replay.playing} onAction={onAction} />
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-dim">
            <span>Validated by genui: 0 errors</span>
            <span aria-hidden>·</span>
            <span>{rec.components.join(", ")}</span>
            <Link to={`/playground?example=${rec.id}`} className="ml-auto font-medium text-fg hover:underline">
              Open in playground →
            </Link>
          </div>
        </section>
      </div>
      {toast}
    </div>
  );
}
