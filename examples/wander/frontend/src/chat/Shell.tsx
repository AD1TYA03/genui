import { useThread } from "@openuidev/react-headless";
import type { AssistantMessage as AGAssistantMessage, Message, ToolMessage } from "@openuidev/react-headless";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ChatBridgeContext, cx } from "../components/bridge";
import { IconAlert, IconArrowUp, IconCheck, IconCompass, IconRefresh, IconStop } from "../components/icons";
import {
  CompassRose,
  CompassSpinner,
  DESTINATION_SKETCHES,
  DESTINATION_TINTS,
  IndiaMap,
  MountainTreehouse,
  PostageStamp,
  Shikara,
  SketchDefs,
  SketchDivider,
  SketchLoader,
  Swash,
} from "../components/sketches";
import { SuggestionChips } from "../components/ui";
import { AssistantMessage } from "./AssistantMessage";
import { DESTINATIONS, STARTER_CHIPS } from "./destinations";
import { groupTurns, readMessage, summarizeContext, textOf, toolLabel, type Turn } from "./messages";

const ease = [0.22, 1, 0.36, 1] as const;

/* ------------------------------------------------------------------ brand */
function Monogram({ className }: { className?: string }) {
  return (
    <span className={cx("relative grid size-10 place-items-center", className)}>
      <CompassRose className="size-full" />
    </span>
  );
}

function Header({ onNew, hasMessages, demo }: { onNew: () => void; hasMessages: boolean; demo: boolean }) {
  return (
    <header className="sticky top-0 z-40">
      <div className="absolute inset-0 bg-bg/85 backdrop-blur-md" />
      <svg
        viewBox="0 0 1200 6"
        preserveAspectRatio="none"
        className="absolute inset-x-0 bottom-0 h-1.5 w-full text-ink/25"
        fill="none"
        stroke="currentColor"
        aria-hidden
      >
        <path d="M0 3 C200 1 400 5 600 3 S1000 1 1200 3.5" strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="relative mx-auto flex h-16 max-w-[1180px] items-center justify-between px-5 sm:px-8">
        <button
          type="button"
          onClick={onNew}
          aria-label="Wander — start over"
          className="flex items-center gap-2.5 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-teal/60 focus-visible:ring-offset-4 focus-visible:ring-offset-bg"
        >
          <Monogram className="size-9" />
          <span className="flex items-baseline gap-2.5">
            <span className="font-display text-[27px] font-medium italic leading-none tracking-tight text-ink">Wander</span>
            <span className="hidden font-hand text-[19px] leading-none text-terracotta sm:inline">stays worth the journey</span>
          </span>
        </button>
        <div className="flex items-center gap-2">
          {demo && (
            <span className="hidden -rotate-3 rounded-[4px] border-[1.5px] border-terracotta/70 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-terracotta sm:inline">
              Demo
            </span>
          )}
          <AnimatePresence>
            {hasMessages && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                type="button"
                onClick={onNew}
                className="inline-flex h-9 items-center gap-2 rounded-full border-[1.5px] border-ink/70 bg-surface px-3.5 text-[13.5px] font-medium text-ink shadow-[2px_2px_0_var(--ink)] transition-all hover:-translate-y-px hover:shadow-[3px_3px_0_var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60 active:translate-y-0 active:shadow-[1px_1px_0_var(--ink)]"
              >
                <IconCompass size={15} /> New trip
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}

/* ------------------------------------------------------------- empty state */
function HeroJournal() {
  return (
    <div className="relative mx-auto w-full max-w-[520px] pt-4">
      {/* the journal page */}
      <motion.div
        initial={{ opacity: 0, y: 24, rotate: 0 }}
        animate={{ opacity: 1, y: 0, rotate: -1.6 }}
        transition={{ duration: 1, delay: 0.1, ease }}
        className="paper-card relative rounded-[6px] px-5 pb-6 pt-7 sm:px-8"
        style={{
          backgroundImage:
            "radial-gradient(circle, color-mix(in oklab, var(--ink) 13%, transparent) 1px, transparent 1.3px)",
          backgroundSize: "18px 18px",
        }}
      >
        <span className="tape -top-3 left-1/2 -translate-x-1/2 -rotate-2" style={{ ["--tape" as string]: "var(--sky)" }} />
        <div className="flex items-start justify-between">
          <div>
            <p className="font-hand text-[24px] leading-none text-ink">The long way round</p>
            <p className="mt-1 font-mono text-[10.5px] uppercase tracking-[0.2em] text-ink-3">Srinagar → Alleppey · 7 stops</p>
          </div>
          <CompassRose className="-mr-1 -mt-2 size-16 text-ink sm:size-[72px]" />
        </div>
        <IndiaMap className="mx-auto -mt-2 w-full max-w-[400px]" />
      </motion.div>
      {/* stamps + notes stuck on the page */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8, rotate: 0 }}
        animate={{ opacity: 1, scale: 1, rotate: 7 }}
        transition={{ duration: 0.7, delay: 0.9, ease }}
        className="absolute -right-1 bottom-24 w-[88px] sm:-right-8 sm:bottom-20 sm:w-[128px]"
      >
        <PostageStamp value="₹25" tint="var(--sage)" className="aspect-[4/5]">
          <MountainTreehouse className="size-full" />
        </PostageStamp>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1, rotate: -8 }}
        transition={{ duration: 0.7, delay: 1.1, ease }}
        className="absolute -left-2 bottom-3 w-[84px] sm:-left-10 sm:bottom-6 sm:w-[112px]"
      >
        <PostageStamp value="₹10" tint="var(--teal)" className="aspect-[5/4]">
          <Shikara className="size-full" />
        </PostageStamp>
      </motion.div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto w-full max-w-[1180px] px-5 pb-10 pt-6 sm:px-8 sm:pt-12">
      <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease }}>
          <p className="inline-flex items-center gap-2 font-mono text-[11.5px] uppercase tracking-[0.2em] text-ink-2">
            <span className="h-px w-8 bg-ink/40" />
            Hand-picked stays across India
          </p>
          <h1 className="mt-5 font-display text-[50px] font-normal leading-[0.98] tracking-[-0.025em] text-ink text-balance sm:text-[76px]">
            Your concierge for{" "}
            <span className="relative inline-block italic text-terracotta">
              extraordinary
              <Swash className="absolute -bottom-2 left-1 h-3 w-[96%] text-mustard" />
            </span>{" "}
            stays
          </h1>
          <p className="mt-6 max-w-[500px] text-[17px] leading-relaxed text-ink-2 text-pretty">
            Tell Wander the feeling you’re after. It finds the treehouse, the houseboat or the dome under the stars — and
            books it, right here.
          </p>
          <div className="relative mt-8">
            <p className="mb-2 flex items-center gap-2 font-hand text-[22px] leading-none text-teal">
              try one of these
              <svg viewBox="0 0 40 24" className="h-5 w-9 text-teal" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" aria-hidden>
                <path d="M2 4 C12 4 24 8 30 18 M24 17 l6 2 l1 -6" />
              </svg>
            </p>
            <SuggestionChips items={STARTER_CHIPS} onPick={onPick} />
          </div>
        </motion.div>
        <HeroJournal />
      </div>

      <SketchDivider className="mt-16 sm:mt-24" label="or begin with a place" />

      <div className="mt-10 grid grid-cols-2 gap-x-4 gap-y-7 sm:gap-x-6 sm:gap-y-8 lg:grid-cols-3 lg:gap-x-8 lg:gap-y-10">
        {DESTINATIONS.map((d, i) => {
          const Art = DESTINATION_SKETCHES[i % DESTINATION_SKETCHES.length];
          const tint = DESTINATION_TINTS[i % DESTINATION_TINTS.length];
          const tilt = [-1.2, 0.8, -0.5, 1, -0.9, 0.6][i % 6];
          return (
            <motion.button
              key={d.title}
              type="button"
              onClick={() => onPick(d.prompt)}
              initial={{ opacity: 0, y: 24, rotate: 0 }}
              animate={{ opacity: 1, y: 0, rotate: tilt }}
              whileHover={{ y: -6, rotate: tilt * -0.6, transition: { duration: 0.35 } }}
              transition={{ duration: 0.8, delay: 0.3 + i * 0.07, ease }}
              className="group/tile paper-card relative flex flex-col rounded-[4px] p-2 pb-3 sm:p-3 sm:pb-4 text-left outline-none transition-shadow duration-300 hover:shadow-card-hover focus-visible:ring-2 focus-visible:ring-teal/70 focus-visible:ring-offset-4 focus-visible:ring-offset-bg"
            >
              <span
                className="tape -top-2.5 left-4 w-12 -rotate-6 sm:left-6 sm:w-16"
                style={{ ["--tape" as string]: tint }}
              />
              <div
                className="relative overflow-hidden rounded-[2px] border border-ink/10"
                style={{ background: `color-mix(in oklab, ${tint} 9%, var(--surface))` }}
              >
                <Art className="aspect-[3/2] w-full transition-transform duration-700 group-hover/tile:scale-[1.04]" />
                <span className="absolute right-2 top-2 hidden font-mono text-[10px] uppercase tracking-[0.18em] text-ink-3 sm:inline">
                  No. {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="flex items-end justify-between gap-3 px-0.5 pt-2.5 sm:px-1 sm:pt-3.5">
                <div className="min-w-0">
                  <p className="truncate font-mono text-[9.5px] uppercase tracking-[0.14em] text-ink-3 sm:text-[10.5px] sm:tracking-[0.18em]">{d.region}</p>
                  <p className="mt-1 font-display text-[18px] leading-[1.08] tracking-[-0.01em] text-ink sm:text-[24px]">{d.title}</p>
                  <p className="mt-1 font-hand text-[17px] leading-tight text-terracotta sm:text-[20px]">{d.blurb}</p>
                </div>
                <span className="mb-1 hidden size-9 shrink-0 place-items-center sm:grid rounded-full border-[1.5px] border-ink/60 text-ink transition-all duration-300 group-hover/tile:rotate-45 group-hover/tile:bg-ink group-hover/tile:text-surface">
                  <IconArrowUp size={15} className="rotate-45" />
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- user turn */
function UserBubble({ message }: { message: Message }) {
  const { content, context } = useMemo(() => readMessage(textOf(message.content)), [message.content]);
  const chips = summarizeContext(context);
  const isAction = Array.isArray(context);
  return (
    <motion.div
      initial={{ opacity: 0, y: 12, rotate: 0 }}
      animate={{ opacity: 1, y: 0, rotate: 0.6 }}
      transition={{ duration: 0.45, ease }}
      className="flex justify-end"
    >
      <div className="flex max-w-[86%] flex-col items-end gap-2 sm:max-w-[66%]">
        <div className="relative rounded-[3px] bg-[#fffdf7] px-5 pb-3.5 pt-4 text-[16px] leading-relaxed text-ink shadow-card">
          <span className="tape -top-2.5 right-6 h-5 w-14 rotate-3" style={{ ["--tape" as string]: "var(--sky)" }} />
          <span
            aria-hidden
            className="pointer-events-none absolute inset-x-4 bottom-2 top-4 bg-[repeating-linear-gradient(180deg,transparent_0_25px,color-mix(in_oklab,var(--sky)_35%,transparent)_25px_26px)]"
          />
          <p className="relative">
            {isAction && <span className="mr-1.5 font-hand text-[19px] text-terracotta">tapped:</span>}
            {content}
          </p>
        </div>
        {chips.length > 0 && (
          <div className="flex flex-wrap justify-end gap-1.5">
            {chips.map((c) => (
              <span
                key={c}
                className="rounded-[3px] border border-dashed border-ink/30 bg-surface/70 px-2.5 py-1 font-mono text-[11.5px] text-ink-2"
              >
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* -------------------------------------------------------------- agent turn */
function ToolTrail({ calls, done }: { calls: { id: string; name: string }[]; done: Set<string> }) {
  if (!calls.length) return null;
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5" aria-label="What the concierge did">
      {calls.map((c) => {
        const finished = done.has(c.id);
        return (
          <motion.li
            key={c.id}
            layout
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={cx("inline-flex items-center gap-1.5 font-hand text-[21px] leading-none", finished ? "text-ink-3" : "text-teal")}
          >
            {finished ? (
              <span className="grid size-5 place-items-center rounded-full border-[1.5px] border-current">
                <IconCheck size={11} strokeWidth={2.6} />
              </span>
            ) : (
              <CompassSpinner className="size-6 text-teal" />
            )}
            {toolLabel(c.name, finished)}
            {!finished && "…"}
          </motion.li>
        );
      })}
    </ul>
  );
}

function ThinkingSkeleton({ label }: { label: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col gap-5"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <CompassSpinner className="size-8" />
        <span className="font-hand text-[26px] leading-none text-ink">{label}…</span>
      </div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={cx("rounded-[4px] bg-surface/70 p-3 pb-10 shadow-card", i > 0 && "hidden sm:block")}
            style={{ rotate: `${[-1, 0.8, -0.4][i]}deg` }}
          >
            <div className="grid aspect-[4/3] place-items-center rounded-[2px] border border-dashed border-ink/20">
              <SketchLoader className="w-4/5 opacity-70" />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function AgentTurn({ turn, live, running }: { turn: Turn; live: boolean; running: boolean }) {
  const assistants = turn.agent.filter((m): m is AGAssistantMessage => m.role === "assistant");
  const toolResults = new Set(
    turn.agent.filter((m): m is ToolMessage => m.role === "tool").map((m) => m.toolCallId),
  );
  const calls = assistants.flatMap((m) => (m.toolCalls ?? []).map((tc) => ({ id: tc.id, name: tc.function.name })));
  const withContent = assistants.filter((m) => textOf(m.content).trim().length > 0);
  const lastContentId = withContent[withContent.length - 1]?.id;
  const lastAssistant = assistants[assistants.length - 1];
  const pendingTool = calls.find((c) => !toolResults.has(c.id));
  const streamingId = live && running ? lastAssistant?.id : undefined;
  const showSkeleton = live && running && (!withContent.length || (lastAssistant && !textOf(lastAssistant.content).trim()));
  const label = pendingTool ? toolLabel(pendingTool.name, false) : calls.length ? "Sketching your options" : "Thinking";

  return (
    <div className="flex flex-col gap-6">
      <ToolTrail calls={calls} done={running && live ? toolResults : new Set(calls.map((c) => c.id))} />
      {withContent.map((m) => (
        <AssistantMessage key={m.id} message={m} isStreaming={m.id === streamingId && m.id === lastContentId} />
      ))}
      <AnimatePresence>{showSkeleton && <ThinkingSkeleton key="sk" label={label} />}</AnimatePresence>
    </div>
  );
}

/* ---------------------------------------------------------------- composer */
function Composer({
  onSend,
  onStop,
  running,
  showChips,
}: {
  onSend: (t: string) => void;
  onStop: () => void;
  running: boolean;
  showChips: boolean;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);
  const submit = () => {
    const t = value.trim();
    if (!t || running) return;
    onSend(t);
    setValue("");
  };
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30">
      <div className="h-10 bg-gradient-to-t from-bg to-transparent" />
      <div className="pointer-events-auto bg-bg pb-[max(env(safe-area-inset-bottom),14px)]">
        <div className="mx-auto max-w-[860px] px-4 sm:px-8">
          <AnimatePresence>
            {showChips && !running && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                className="-mx-4 mb-3 overflow-x-auto px-4 scrollbar-none sm:mx-0 sm:px-0"
              >
                <SuggestionChips items={STARTER_CHIPS} onPick={onSend} className="flex-nowrap sm:flex-wrap [&>button]:shrink-0" />
              </motion.div>
            )}
          </AnimatePresence>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
            className="group/composer flex items-end gap-2 rounded-[18px] border-[1.5px] border-ink/75 bg-surface p-2 pl-5 shadow-[3px_4px_0_color-mix(in_oklab,var(--ink)_85%,transparent)] transition-shadow focus-within:shadow-[4px_5px_0_var(--terracotta)]"
          >
            <textarea
              ref={ref}
              rows={1}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder="Where would you like to wake up?"
              aria-label="Message Wander"
              className="max-h-[180px] min-h-[24px] flex-1 resize-none self-center bg-transparent py-2 text-[16px] leading-6 text-ink outline-none placeholder:text-ink-3"
            />
            {running ? (
              <button
                type="button"
                onClick={onStop}
                aria-label="Stop"
                className="grid size-11 shrink-0 place-items-center rounded-full bg-ink/8 text-ink transition-colors hover:bg-ink/14 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60"
              >
                <IconStop />
              </button>
            ) : (
              <button
                type="submit"
                aria-label="Send"
                disabled={!value.trim()}
                className="grid size-11 shrink-0 place-items-center rounded-full bg-ink text-surface transition-all duration-300 hover:scale-105 hover:bg-terracotta focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60 focus-visible:ring-offset-2 active:scale-95 disabled:scale-100 disabled:bg-ink/25 disabled:hover:bg-ink/25"
              >
                <IconArrowUp size={19} strokeWidth={2.1} />
              </button>
            )}
          </form>
          <p className="mt-2.5 text-center text-[11.5px] text-ink-3">
            Wander is a demo concierge for genui — stays and bookings are simulated.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- shell */
export function Shell({ demo = false }: { demo?: boolean }) {
  const messages = useThread((s) => s.messages);
  const isRunning = useThread((s) => s.isRunning);
  const threadError = useThread((s) => s.threadError);
  const processMessage = useThread((s) => s.processMessage);
  const cancelMessage = useThread((s) => s.cancelMessage);
  const setMessages = useThread((s) => s.setMessages);

  const send = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      void processMessage({ role: "user", content: text });
    },
    [processMessage],
  );
  const bridge = useMemo(() => ({ send, busy: isRunning }), [send, isRunning]);
  const turns = useMemo(() => groupTurns(messages), [messages]);
  const empty = messages.length === 0;

  // Keep the newest turn in view while streaming, unless the reader scrolled up.
  const stick = useRef(true);
  useEffect(() => {
    const onScroll = () => {
      stick.current = window.innerHeight + window.scrollY >= document.body.scrollHeight - 220;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const lastLen = useRef(0);
  useEffect(() => {
    const grew = messages.length > lastLen.current;
    const userJustSent = grew && messages[messages.length - 1]?.role === "user";
    lastLen.current = messages.length;
    if (userJustSent) stick.current = true;
    if (stick.current && !empty)
      requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: userJustSent ? "smooth" : "auto" }));
  }, [messages, empty]);

  const retry = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const idx = messages.lastIndexOf(lastUser);
    setMessages(messages.slice(0, idx));
    void processMessage({ role: "user", content: textOf(lastUser.content) });
  };

  return (
    <ChatBridgeContext.Provider value={bridge}>
      <SketchDefs />
      <div className="ambient" />
      <div className="grain" />
      <div className="relative z-10 flex min-h-dvh flex-col">
        <Header onNew={() => setMessages([])} hasMessages={!empty} demo={demo} />
        <main className={cx("flex-1", empty ? "pb-48" : "pb-56")}>
          {empty ? (
            <EmptyState onPick={send} />
          ) : (
            <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-10 px-5 pt-8 sm:px-8 sm:pt-12">
              {turns.map((t, i) => {
                const live = i === turns.length - 1;
                return (
                  <section key={t.user?.id ?? `t${i}`} className="flex flex-col gap-7">
                    {i > 0 && <SketchDivider className="mb-2 sm:pl-14" />}
                    {t.user && <UserBubble message={t.user} />}
                    {(t.agent.length > 0 || (live && isRunning)) && (
                      <div className="flex gap-4">
                        <div className="hidden pt-0.5 sm:block">
                          <Monogram className="size-10" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <AgentTurn turn={t} live={live} running={isRunning} />
                        </div>
                      </div>
                    )}
                  </section>
                );
              })}
              <AnimatePresence>
                {threadError && !isRunning && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-start gap-3 rounded-[4px] border-[1.5px] border-dashed border-terracotta/60 bg-[#f8e3d8] p-4 sm:ml-14"
                  >
                    <IconAlert size={18} className="mt-0.5 shrink-0 text-terracotta" />
                    <div className="min-w-0 flex-1">
                      <p className="font-hand text-[22px] leading-none text-ink">The concierge lost the thread</p>
                      <p className="mt-1 break-words text-[13.5px] text-ink-2">{threadError.message}</p>
                    </div>
                    <button
                      type="button"
                      onClick={retry}
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-full border-[1.5px] border-ink/60 bg-surface px-3 py-1.5 text-[13px] font-medium text-ink hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/60"
                    >
                      <IconRefresh size={14} /> Retry
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </main>
        <Composer onSend={send} onStop={cancelMessage} running={isRunning} showChips={false} />
      </div>
    </ChatBridgeContext.Provider>
  );
}
