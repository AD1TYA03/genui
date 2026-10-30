import { CheckIcon, CopyIcon } from "./icons";
import { useCopy } from "./useCopy";

export function CopyPill({ command }: { command: string }) {
  const { copied, copy } = useCopy();
  return (
    <button
      type="button"
      onClick={() => copy(command)}
      className="group flex h-12 w-full items-center gap-3 rounded-xl border border-line-strong bg-panel/60 pl-4 pr-2 text-left font-mono text-[13.5px] transition hover:border-white/25 hover:bg-panel"
      aria-label={copied ? `Copied ${command}` : `Copy ${command}`}
    >
      <span className="text-dim" aria-hidden>
        $
      </span>
      <span className="text-fg">{command}</span>
      <span
        className={`ml-auto grid size-8 place-items-center rounded-lg transition ${
          copied ? "text-emerald-300" : "text-dim group-hover:text-fg"
        }`}
        aria-hidden
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </span>
      <span className="sr-only" aria-live="polite">
        {copied ? "Copied to clipboard" : ""}
      </span>
    </button>
  );
}
