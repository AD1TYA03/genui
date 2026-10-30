import {
  defineComponent,
  reactive,
  useFormValidation,
  useIsStreaming,
  useStateField,
} from "@openuidev/react-lang";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { z } from "zod/v4";
import { cx, formatShortDate, nightsBetween, parseISODate, toISODate } from "./bridge";
import { IconCalendar, IconChevronLeft, IconChevronRight, IconMinus, IconPlus, IconUsers } from "./icons";
import { fadeUp } from "./ui";

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
function addMonths(d: Date, n: number) {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}
function addDays(d: Date, n: number) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
}
function sameDay(a: Date | null, b: Date | null) {
  return !!a && !!b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function today() {
  const n = new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}

function useIsWide() {
  const [wide, setWide] = useState(() => (typeof window === "undefined" ? true : window.innerWidth >= 680));
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 680px)");
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return wide;
}

/** Wrap any picker in the labelled card used inside Forms. */
function FieldCard({
  icon,
  label,
  aside,
  error,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  aside?: React.ReactNode;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div {...fadeUp} className="min-w-0">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 font-hand text-[25px] font-semibold leading-none text-ink">
          <span className="text-terracotta">{icon}</span>
          {label}
        </p>
        {aside}
      </div>
      {children}
      <AnimatePresence>
        {error ? (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-2.5 text-[13.5px] font-medium text-terracotta"
            role="alert"
          >
            {error}
          </motion.p>
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}

/** A hand-drawn diagonal strike for unavailable nights. */
function SketchStrike() {
  return (
    <svg viewBox="0 0 24 24" className="pointer-events-none absolute inset-0 m-auto size-7 text-terracotta" fill="none" aria-hidden>
      <path d="M5.5 18.5 C9 14.5 13 10.5 18.8 5.2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M6.6 19.4 C10 15.6 14 11.4 18.4 7" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round" opacity="0.6" />
    </svg>
  );
}

/* ---------------------------- DateRangePicker ---------------------------- */
export const DateRangePicker = defineComponent({
  name: "DateRangePicker",
  description:
    'Two-month range calendar for check-in/check-out. Bind both dates to $variables declared first, e.g. $checkIn = "" and $checkOut = "". Blocked dates are shown struck through and cannot be selected or spanned.',
  props: z.object({
    label: z.string().describe('Field label, e.g. "When are you going?"'),
    checkIn: reactive(z.string().describe("Check-in date YYYY-MM-DD; bind to $checkIn")),
    checkOut: reactive(z.string().describe("Check-out date YYYY-MM-DD; bind to $checkOut")),
    blocked: z.array(z.string()).optional().describe("Unavailable nights as YYYY-MM-DD (from check_availability)"),
    minNights: z.number().optional().describe("Minimum stay length in nights, default 1"),
  }),
  component: ({ props }) => {
    const isStreaming = useIsStreaming();
    const validation = useFormValidation();
    const inField = useStateField("checkIn", props.checkIn);
    const outField = useStateField("checkOut", props.checkOut);
    const checkIn = parseISODate(inField.value);
    const checkOut = parseISODate(outField.value);
    const minNights = Math.max(1, Math.floor(props.minNights ?? 1));
    const blockedSet = useMemo(
      () => new Set((props.blocked ?? []).filter((s): s is string => typeof s === "string")),
      [props.blocked],
    );
    const isBlocked = (d: Date) => blockedSet.has(toISODate(d));
    const t0 = today();
    const wide = useIsWide();

    const [view, setView] = useState(() => startOfMonth(checkIn ?? t0));
    const [hover, setHover] = useState<Date | null>(null);
    const [focus, setFocus] = useState<Date>(() => checkIn ?? t0);
    const [hint, setHint] = useState<string | null>(null);
    const gridRef = useRef<HTMLDivElement>(null);
    const latest = useRef({ checkIn: inField.value, checkOut: outField.value });
    latest.current = { checkIn: inField.value, checkOut: outField.value };

    // Jump the calendar to a check-in that arrives from the model / hydration (not user clicks).
    const ci = typeof inField.value === "string" ? inField.value : "";
    const userPicked = useRef(false);
    useEffect(() => {
      if (userPicked.current) {
        userPicked.current = false;
        return;
      }
      const d = parseISODate(ci);
      if (d) {
        setView(startOfMonth(d));
        setFocus(d);
      }
    }, [ci]);

    useEffect(() => {
      if (!validation || isStreaming) return;
      validation.registerField("dates", [{ type: "required" }], () =>
        parseISODate(latest.current.checkIn) && parseISODate(latest.current.checkOut) ? "ok" : "",
      );
      return () => validation.unregisterField("dates");
    }, [validation, isStreaming]);
    const rawError = validation?.getFieldError("dates");
    const error = rawError ? "Pick your check-in and check-out dates to continue." : undefined;

    const rangeHasBlocked = (a: Date, b: Date) => {
      for (let d = a; d < b; d = addDays(d, 1)) if (isBlocked(d)) return true;
      return false;
    };

    const select = (d: Date) => {
      if (isStreaming || d < t0 || isBlocked(d)) return;
      setHint(null);
      if (!checkIn || (checkIn && checkOut) || d <= checkIn) {
        userPicked.current = true;
        inField.setValue(toISODate(d));
        outField.setValue("");
        return;
      }
      const n = nightsBetween(toISODate(checkIn), toISODate(d));
      if (rangeHasBlocked(checkIn, d)) {
        setHint("That range crosses unavailable nights — try different dates.");
        return;
      }
      if (n < minNights) {
        setHint(`Minimum stay is ${minNights} night${minNights > 1 ? "s" : ""}.`);
        return;
      }
      outField.setValue(toISODate(d));
      validation?.clearFieldError("dates");
    };

    const moveFocus = (d: Date) => {
      setFocus(d);
      if (d < view) setView(startOfMonth(d));
      else if (d >= addMonths(view, wide ? 2 : 1)) setView(addMonths(startOfMonth(d), wide ? -1 : 0));
      requestAnimationFrame(() => {
        gridRef.current?.querySelector<HTMLButtonElement>(`[data-date="${toISODate(d)}"]`)?.focus();
      });
    };

    const onKey = (e: KeyboardEvent<HTMLButtonElement>, d: Date) => {
      const map: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
      if (e.key in map) {
        e.preventDefault();
        moveFocus(addDays(d, map[e.key]));
      } else if (e.key === "PageDown" || e.key === "PageUp") {
        e.preventDefault();
        const nd = new Date(d.getFullYear(), d.getMonth() + (e.key === "PageDown" ? 1 : -1), d.getDate());
        moveFocus(nd);
      } else if (e.key === "Home" || e.key === "End") {
        e.preventDefault();
        const dow = (d.getDay() + 6) % 7;
        moveFocus(addDays(d, e.key === "Home" ? -dow : 6 - dow));
      }
    };

    const previewEnd = checkIn && !checkOut && hover && hover > checkIn ? hover : null;
    const end = checkOut ?? previewEnd;
    const nights = checkIn && checkOut ? nightsBetween(toISODate(checkIn), toISODate(checkOut)) : 0;
    const months = wide ? [view, addMonths(view, 1)] : [view];
    const canPrev = addMonths(view, -1) >= startOfMonth(t0);

    const renderMonth = (m: Date) => {
      const first = startOfMonth(m);
      const lead = (first.getDay() + 6) % 7;
      const daysIn = new Date(m.getFullYear(), m.getMonth() + 1, 0).getDate();
      const cells: (Date | null)[] = [
        ...Array.from({ length: lead }, () => null),
        ...Array.from({ length: daysIn }, (_, i) => new Date(m.getFullYear(), m.getMonth(), i + 1)),
      ];
      while (cells.length % 7) cells.push(null);
      return (
        <div key={toISODate(first)} className="min-w-0 flex-1">
          <p className="mb-3 text-center font-display text-[21px] italic text-ink">
            {first.toLocaleDateString("en-GB", { month: "long" })}{" "}
            <span className="text-ink-3">{first.getFullYear()}</span>
          </p>
          <div className="grid grid-cols-7 gap-y-1 text-center" role="grid">
            {WEEKDAYS.map((w) => (
              <span key={w} className="pb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-3">
                {w}
              </span>
            ))}
            {cells.map((d, i) => {
              if (!d) return <span key={`e${i}`} />;
              const past = d < t0;
              const blocked = isBlocked(d);
              const disabled = past || blocked;
              const isStart = sameDay(d, checkIn);
              const isEnd = sameDay(d, end);
              const inRange = !!checkIn && !!end && d > checkIn && d < end;
              const edge = isStart || isEnd;
              const rangeBg = (inRange || (isStart && end) || (isEnd && checkIn)) && !sameDay(checkIn, end);
              const isFocus = sameDay(d, focus);
              const isToday = sameDay(d, t0);
              return (
                <div key={toISODate(d)} className="relative h-11" role="gridcell">
                  {rangeBg && (
                    <span
                      className={cx(
                        "absolute inset-y-1 bg-teal/14",
                        isStart ? "left-1/2 right-0" : isEnd ? "left-0 right-1/2" : "inset-x-0",
                      )}
                    />
                  )}
                  <button
                    type="button"
                    data-date={toISODate(d)}
                    tabIndex={isFocus ? 0 : -1}
                    disabled={disabled || isStreaming}
                    aria-pressed={edge}
                    aria-label={`${d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })}${blocked ? ", unavailable" : ""}${isStart ? ", check-in" : ""}${isEnd ? ", check-out" : ""}`}
                    onClick={() => {
                      setFocus(d);
                      select(d);
                    }}
                    onMouseEnter={() => setHover(d)}
                    onFocus={() => setHover(d)}
                    onKeyDown={(e) => onKey(e, d)}
                    className={cx(
                      "relative mx-auto grid size-11 place-items-center rounded-full text-[14px] tabular-nums outline-none transition-all duration-200",
                      "focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
                      edge
                        ? "bg-ink font-semibold text-surface shadow-[2px_2px_0_var(--terracotta)]"
                        : disabled
                          ? blocked && !past
                            ? "cursor-not-allowed text-ink-3"
                            : "cursor-not-allowed text-ink-3/45"
                          : inRange
                            ? "font-medium text-ink hover:bg-teal/20"
                            : "text-ink hover:bg-ink/8",
                    )}
                  >
                    <span>{d.getDate()}</span>
                    {blocked && !past && <SketchStrike />}
                    {isToday && !edge && <span className="absolute bottom-1.5 size-1 rounded-full bg-terracotta" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      );
    };

    return (
      <FieldCard
        icon={<IconCalendar size={15} />}
        label={props.label ?? "Dates"}
        error={error}
        aside={
          checkIn || checkOut ? (
            <button
              type="button"
              onClick={() => {
                userPicked.current = true;
                inField.setValue("");
                outField.setValue("");
                setHint(null);
              }}
              className="text-[12.5px] font-medium text-ink-3 underline-offset-4 transition-colors hover:text-ink hover:underline"
            >
              Clear dates
            </button>
          ) : null
        }
      >
        <div className="overflow-hidden rounded-[6px] border-[1.5px] border-ink/20 bg-[#fffdf8]">
          {/* summary row */}
          <div className="grid grid-cols-[1fr_auto_1fr] items-stretch border-b-[1.5px] border-dashed border-ink/15">
            {[
              { k: "Check-in", v: checkIn, active: !checkIn || !!checkOut },
              null,
              { k: "Check-out", v: checkOut, active: !!checkIn && !checkOut },
            ].map((cell, i) =>
              cell ? (
                <div key={cell.k} className={cx("px-4 py-3.5 sm:px-5", i === 2 && "text-right")}>
                  <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-3">{cell.k}</p>
                  <p
                    className={cx(
                      "mt-0.5 truncate text-[16px] font-medium sm:text-[17px]",
                      cell.v ? "text-ink" : cell.active ? "text-terracotta" : "text-ink-3",
                    )}
                  >
                    {cell.v ? formatShortDate(toISODate(cell.v), true) : cell.active ? "Select date" : "—"}
                  </p>
                </div>
              ) : (
                <div key="mid" className="flex items-center px-2">
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={nights}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      className={cx(
                        "whitespace-nowrap rounded-full px-3 py-1 text-[12px] font-semibold",
                        nights ? "bg-teal/12 text-teal" : "bg-ink/5 text-ink-3",
                      )}
                    >
                      {nights ? `${nights} night${nights > 1 ? "s" : ""}` : "→"}
                    </motion.span>
                  </AnimatePresence>
                </div>
              ),
            )}
          </div>
          {/* calendar */}
          <div className="relative px-3 pb-4 pt-4 sm:px-5" ref={gridRef} onMouseLeave={() => setHover(null)}>
            <button
              type="button"
              aria-label="Previous month"
              disabled={!canPrev}
              onClick={() => setView((v) => addMonths(v, -1))}
              className="absolute left-3 top-3.5 grid size-9 place-items-center rounded-full text-ink-2 transition-colors hover:bg-ink/8 hover:text-ink disabled:opacity-25 sm:left-5"
            >
              <IconChevronLeft size={18} />
            </button>
            <button
              type="button"
              aria-label="Next month"
              onClick={() => setView((v) => addMonths(v, 1))}
              className="absolute right-3 top-3.5 grid size-9 place-items-center rounded-full text-ink-2 transition-colors hover:bg-ink/8 hover:text-ink sm:right-5"
            >
              <IconChevronRight size={18} />
            </button>
            <div className="flex gap-8">{months.map(renderMonth)}</div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 px-1 text-[12px] text-ink-3">
              <span className="flex items-center gap-3">
                {blockedSet.size > 0 && (
                  <span className="flex items-center gap-1.5">
                    <span className="relative inline-grid w-5 place-items-center text-ink-3">14<SketchStrike /></span> Unavailable
                  </span>
                )}
                {minNights > 1 && <span>Min. {minNights} nights</span>}
              </span>
              <AnimatePresence>
                {hint ? (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-terracotta"
                  >
                    {hint}
                  </motion.span>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </FieldCard>
    );
  },
});

/* ------------------------------ GuestPicker ------------------------------ */
function Stepper({
  title,
  caption,
  value,
  min,
  canInc,
  onChange,
  disabled,
}: {
  title: string;
  caption: string;
  value: number;
  min: number;
  canInc: boolean;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const btn =
    "grid size-10 place-items-center rounded-full border-[1.5px] border-ink/60 bg-surface text-ink transition-all duration-200 hover:bg-ink hover:text-surface active:scale-90 disabled:pointer-events-none disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal/70 focus-visible:ring-offset-2";
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3.5 sm:px-5">
      <div>
        <p className="text-[15px] font-medium text-ink">{title}</p>
        <p className="text-[12.5px] text-ink-3">{caption}</p>
      </div>
      <div className="flex items-center gap-3" role="group" aria-label={title}>
        <button
          type="button"
          className={btn}
          aria-label={`Fewer ${title.toLowerCase()}`}
          disabled={disabled || value <= min}
          onClick={() => onChange(value - 1)}
        >
          <IconMinus size={16} />
        </button>
        <span className="relative h-7 w-7 overflow-hidden text-center" aria-live="polite">
          <AnimatePresence initial={false} mode="popLayout">
            <motion.span
              key={value}
              initial={{ y: 14, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -14, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 font-display text-[22px] tabular-nums leading-7 text-ink"
            >
              {value}
            </motion.span>
          </AnimatePresence>
        </span>
        <button
          type="button"
          className={btn}
          aria-label={`More ${title.toLowerCase()}`}
          disabled={disabled || !canInc}
          onClick={() => onChange(value + 1)}
        >
          <IconPlus size={16} />
        </button>
      </div>
    </div>
  );
}

function toCount(v: unknown, fallback: number) {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN;
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : fallback;
}

export const GuestPicker = defineComponent({
  name: "GuestPicker",
  description:
    "Adults/children steppers. Bind to $variables declared first, e.g. $adults = 2 and $children = 0. max caps total guests (the stay's maxGuests).",
  props: z.object({
    label: z.string().describe('Field label, e.g. "Who\'s coming?"'),
    adults: reactive(z.number().describe("Adults (13+); bind to $adults")),
    children: reactive(z.number().describe("Children (2-12); bind to $children")),
    max: z.number().optional().describe("Maximum total guests, default 6"),
  }),
  component: ({ props }) => {
    const isStreaming = useIsStreaming();
    const adultsField = useStateField("adults", props.adults);
    const kidsField = useStateField("children", props.children);
    const adults = Math.max(1, toCount(adultsField.value, 2));
    const kids = toCount(kidsField.value, 0);
    const max = Math.max(1, Math.floor(props.max ?? 6));

    // Persist sensible defaults so the agent always receives guest counts.
    useEffect(() => {
      if (isStreaming) return;
      const empty = (v: unknown) => v == null || v === "";
      if (empty(adultsField.value)) adultsField.setValue(2);
      if (empty(kidsField.value)) kidsField.setValue(0);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isStreaming]);

    const total = adults + kids;
    return (
      <FieldCard
        icon={<IconUsers size={15} />}
        label={props.label ?? "Guests"}
        aside={
          <span className="text-[12.5px] text-ink-3">
            {total} of {max} guests
          </span>
        }
      >
        <div className="divide-y-[1.5px] divide-dashed divide-ink/15 overflow-hidden rounded-[6px] border-[1.5px] border-ink/20 bg-[#fffdf8]">
          <Stepper
            title="Adults"
            caption="Ages 13 or above"
            value={adults}
            min={1}
            canInc={total < max}
            disabled={isStreaming}
            onChange={(v) => adultsField.setValue(v)}
          />
          <Stepper
            title="Children"
            caption="Ages 2–12"
            value={kids}
            min={0}
            canInc={total < max}
            disabled={isStreaming}
            onChange={(v) => kidsField.setValue(v)}
          />
        </div>
      </FieldCard>
    );
  },
});
