import { useEffect, useRef } from "react";
import { Highlight } from "../lib/highlight";

export function StreamingCode({
  text,
  streaming,
  className = "",
  follow = true,
}: {
  text: string;
  streaming: boolean;
  className?: string;
  follow?: boolean;
}) {
  const ref = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (!follow || !streaming) return;
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [text, follow, streaming]);
  return (
    <pre
      ref={ref}
      className={`scrollbar-thin overflow-auto whitespace-pre-wrap break-words font-mono text-[12px] leading-[1.65] ${className}`}
    >
      <code>
        <Highlight code={text} lang="oui" />
        {streaming && <span className="ml-px inline-block h-[1.1em] w-[7px] translate-y-[2px] animate-blink bg-cyan-300/90 align-baseline" />}
      </code>
    </pre>
  );
}
