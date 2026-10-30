import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { GenUIActionEvent } from "genui-react";

/** Shows what a click inside the generated UI would send back to the agent. */
export function useActionToast() {
  const [event, setEvent] = useState<GenUIActionEvent | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const onAction = useCallback((e: GenUIActionEvent) => {
    setEvent(e);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setEvent(null), 4200);
  }, []);
  const toast = (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4">
      <AnimatePresence>
        {event && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10 }}
            className="pointer-events-auto max-w-lg rounded-xl border border-line-strong bg-panel-2/95 px-4 py-3 text-sm shadow-2xl shadow-black/50 backdrop-blur"
            role="status"
          >
            <div className="mb-1 text-xs font-medium text-dim">
              {event.type === "continue_conversation" ? "Sent back to your agent" : `action · ${event.type}`}
            </div>
            <div className="text-fg">{event.humanFriendlyMessage || JSON.stringify(event.params)}</div>
            {event.formState && Object.keys(event.formState).length > 0 && (
              <div className="mt-1.5 truncate font-mono text-[11px] text-dim">form state: {JSON.stringify(event.formState)}</div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
  return { onAction, toast };
}
