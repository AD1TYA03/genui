import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { useActionToast } from "../components/ActionToast";
import { CodeEditor } from "../components/CodeEditor";
import { BoltIcon, CheckIcon, ShareIcon } from "../components/icons";
import { LazyFrame } from "../components/LazyFrame";
import { useCopy } from "../components/useCopy";
import { LINKS } from "../lib/links";
import { getRecording, recordings } from "../lib/recordings";
import { encodeProgram, readHashProgram } from "../lib/share";
import { useTitle } from "../lib/useTitle";

interface LangError {
  source?: string;
  code?: string;
  message?: string;
  statementId?: string;
  component?: string;
  path?: string;
  hint?: string;
  severity?: "warning";
}

function initialProgram(exampleId: string | null) {
  return readHashProgram() ?? (getRecording(exampleId) ?? recordings[0]).source;
}

export default function Playground() {
  useTitle("Playground");
  const [params, setParams] = useSearchParams();
  const [code, setCode] = useState(() => initialProgram(params.get("example")));
  const [exampleId, setExampleId] = useState(() =>
    readHashProgram() ? "" : (getRecording(params.get("example")) ?? recordings[0]).id,
  );
  const deferred = useDeferredValue(code);
  const [errors, setErrors] = useState<LangError[]>([]);
  const { copied, copy } = useCopy();
  const { onAction, toast } = useActionToast();

  // Keep the URL hash shareable as you type.
  const hashTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    window.clearTimeout(hashTimer.current);
    hashTimer.current = window.setTimeout(() => {
      const ex = exampleId ? getRecording(exampleId) : undefined;
      const url = new URL(window.location.href);
      url.hash = ex && ex.source === code ? "" : `code=${encodeProgram(code)}`;
      window.history.replaceState(window.history.state, "", url);
    }, 250);
    return () => window.clearTimeout(hashTimer.current);
  }, [code, exampleId]);

  const pickExample = (id: string) => {
    const rec = getRecording(id);
    if (!rec) return;
    setExampleId(id);
    setCode(rec.source);
    const next = new URLSearchParams(params);
    next.set("example", id);
    setParams(next, { replace: true });
  };

  const onError = useCallback((errs: unknown[]) => setErrors(errs as LangError[]), []);

  const errorLines = useMemo(() => {
    const lines = code.split("\n");
    const set = new Set<number>();
    for (const e of errors) {
      if (!e.statementId || e.severity === "warning") continue;
      const idx = lines.findIndex((l) => new RegExp(`^\\s*${e.statementId!.replace(/[$]/g, "\\$")}\\s*=`).test(l));
      if (idx >= 0) set.add(idx);
    }
    return set;
  }, [errors, code]);

  const isExample = !!exampleId && getRecording(exampleId)?.source === code;
  const hardErrors = errors.filter((e) => e.severity !== "warning");
  const warnings = errors.filter((e) => e.severity === "warning");
  const share = () => {
    const url = new URL(window.location.href);
    url.search = "";
    url.hash = `code=${encodeProgram(code)}`;
    copy(url.toString());
  };

  return (
    <div className="flex flex-col lg:h-[calc(100dvh-4rem)]">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3 sm:px-6">
        <h1 className="mr-2 text-[15px] font-semibold tracking-tight">Playground</h1>
        <label className="relative">
          <span className="sr-only">Load example</span>
          <select
            value={isExample ? exampleId : ""}
            onChange={(e) => pickExample(e.target.value)}
            className="h-9 appearance-none rounded-lg border border-line-strong bg-panel pl-3 pr-9 text-sm text-fg outline-none transition hover:border-white/25"
          >
            {!isExample && <option value="">Custom program</option>}
            {recordings.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </select>
          <svg className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-dim" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
            <path d="m6 9 6 6 6-6" />
          </svg>
        </label>
        <span
          className={`inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 font-mono text-[11px] ${
            hardErrors.length ? "bg-red-500/10 text-red-300" : "bg-emerald-400/10 text-emerald-300"
          }`}
          aria-live="polite"
        >
          <span className={`size-1.5 rounded-full ${hardErrors.length ? "bg-red-400" : "bg-emerald-400"}`} />
          {hardErrors.length ? `${hardErrors.length} error${hardErrors.length > 1 ? "s" : ""}` : "valid"}
          {warnings.length > 0 && <span className="text-amber-300">· {warnings.length} warning{warnings.length > 1 ? "s" : ""}</span>}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={share}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-line-strong px-3 text-sm font-medium text-muted transition hover:bg-white/5 hover:text-fg"
          >
            {copied ? <CheckIcon className="text-emerald-300" /> : <ShareIcon />}
            {copied ? "Link copied" : "Share"}
          </button>
          <a
            href={LINKS.stackblitz}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-fg px-3 text-sm font-semibold text-ink transition hover:bg-white"
          >
            <BoltIcon /> <span>Open in StackBlitz</span>
          </a>
        </div>
      </div>

      {/* Split */}
      <div className="grid min-h-0 flex-1 lg:grid-cols-2">
        <div className="flex min-h-0 flex-col border-b border-line lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between border-b border-line px-4 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-dim sm:px-6">
            <span>OpenUI Lang</span>
            <span className="normal-case tracking-normal">{code.split("\n").length} lines</span>
          </div>
          <div className="h-[46vh] min-h-0 lg:h-auto lg:flex-1">
            <CodeEditor value={code} onChange={setCode} errorLines={errorLines} />
          </div>
          {errors.length > 0 && (
            <div className="scrollbar-thin max-h-48 overflow-auto border-t border-line bg-red-950/20 px-4 py-3 sm:px-6" role="alert">
              <ul className="space-y-2">
                {errors.slice(0, 20).map((e, i) => (
                  <li key={i} className="font-mono text-[12px] leading-relaxed">
                    <span className={e.severity === "warning" ? "text-amber-300" : "text-red-300"}>
                      {e.severity === "warning" ? "warning" : "error"}
                      {e.code ? ` ${e.code}` : ""}
                    </span>
                    {e.statementId && <span className="text-dim"> · {e.statementId}</span>}
                    <span className="text-fg/90" title={e.message}> {e.message && e.message.length > 160 ? `${e.message.slice(0, 160)}…` : e.message}</span>
                    {e.hint && <div className="line-clamp-2 text-dim">hint: {e.hint}</div>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="flex min-h-0 flex-col">
          <div className="flex items-center justify-between border-b border-line px-4 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-dim sm:px-6">
            <span>Live render · GenUIRenderer</span>
            <span className="normal-case tracking-normal">defaultLibrary</span>
          </div>
          <div className="scrollbar-thin min-h-[50vh] flex-1 overflow-auto p-4 sm:p-6 lg:min-h-0">
            <LazyFrame response={deferred} onAction={onAction} onError={onError} />
          </div>
        </div>
      </div>
      {toast}
    </div>
  );
}
