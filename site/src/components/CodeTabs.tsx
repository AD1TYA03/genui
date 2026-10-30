import { useState } from "react";
import { Highlight, type Lang } from "../lib/highlight";
import { CheckIcon, CopyIcon } from "./icons";
import { useCopy } from "./useCopy";

export interface CodeFile {
  name: string;
  lang: Lang;
  code: string;
}

export function CodeTabs({ files, className = "" }: { files: CodeFile[]; className?: string }) {
  const [active, setActive] = useState(0);
  const { copied, copy } = useCopy();
  const file = files[active];
  return (
    <div className={`overflow-hidden rounded-2xl border border-line bg-ink-2 ${className}`}>
      <div className="flex items-center gap-1 border-b border-line bg-panel/40 px-2">
        <div role="tablist" className="flex min-w-0 overflow-x-auto scrollbar-thin">
          {files.map((f, i) => (
            <button
              key={f.name}
              role="tab"
              aria-selected={i === active}
              onClick={() => setActive(i)}
              className={`relative whitespace-nowrap px-3 py-3 font-mono text-[12.5px] transition ${
                i === active ? "text-fg" : "text-dim hover:text-muted"
              }`}
            >
              {f.name}
              {i === active && <span className="absolute inset-x-3 -bottom-px h-px bg-fg" />}
            </button>
          ))}
        </div>
        <button
          onClick={() => copy(file.code)}
          className="ml-auto mr-1 flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted transition hover:bg-white/5 hover:text-fg"
          aria-label="Copy code"
        >
          {copied ? <CheckIcon className="text-emerald-300" /> : <CopyIcon />}
          <span className="hidden sm:inline">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="scrollbar-thin overflow-x-auto p-5 font-mono text-[12.5px] leading-[1.7] sm:text-[13px]">
        <code>
          <Highlight code={file.code} lang={file.lang} />
        </code>
      </pre>
    </div>
  );
}
