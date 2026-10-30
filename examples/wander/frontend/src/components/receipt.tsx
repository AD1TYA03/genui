import { defineComponent } from "@openuidev/react-lang";
import { motion } from "motion/react";
import { useMemo } from "react";
import { z } from "zod/v4";
import { cx, formatMoney, formatShortDate, nightsBetween, parseISODate } from "./bridge";
import { IconPin } from "./icons";
import { InkStamp, MountainTreehouse, PostageStamp } from "./sketches";
import { SmartImage, sized } from "./stays";
import { fadeUp } from "./ui";

/* ------------------------------ PriceSummary ----------------------------- */
export const PriceSummary = defineComponent({
  name: "PriceSummary",
  description:
    "Receipt-style price breakdown. Use the exact price_lines and total from check_availability (nightly rate × nights, cleaning fee, 12% GST).",
  props: z.object({
    lines: z
      .array(
        z.object({
          label: z.string().describe('Line label, e.g. "₹18,500 × 3 nights"'),
          amount: z.number().describe("Line amount"),
        }),
      )
      .describe("Price lines in order"),
    total: z.number().describe("Grand total"),
    currency: z.string().optional().describe('ISO currency code, default "INR"'),
  }),
  component: ({ props }) => {
    const currency = props.currency ?? "INR";
    const lines = (props.lines ?? []).filter((l) => l && typeof l === "object");
    return (
      <motion.div {...fadeUp} className="receipt-wrap w-full max-w-[440px] -rotate-[0.4deg]">
        <div className="receipt-paper relative bg-[#fffdf8] px-6 pb-9 pt-9 sm:px-8">
          <div className="text-center">
            <p className="font-display text-[22px] italic leading-none text-ink">Wander</p>
            <p className="mt-1.5 font-mono text-[10.5px] uppercase tracking-[0.24em] text-ink-3">Travel receipt · {currency}</p>
          </div>
          <div className="mt-5 border-t-[1.5px] border-dashed border-ink/25" />
          <ul className="mt-5 space-y-3.5 font-mono text-[13.5px]">
            {lines.map((l, i) => (
              <motion.li
                key={`${l.label}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.06 * i, duration: 0.4 }}
                className="flex items-baseline gap-3"
              >
                <span className="text-ink-2">{l.label}</span>
                <span className="mb-1 flex-1 border-b border-dotted border-ink/30" />
                <span className="tabular-nums text-ink">{formatMoney(l.amount, currency)}</span>
              </motion.li>
            ))}
          </ul>
          <div className="mt-6 border-t-[1.5px] border-dashed border-ink/25 pt-5">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-3">Total</p>
                <p className="mt-1 font-hand text-[19px] leading-none text-teal">taxes &amp; fees included ✓</p>
              </div>
              <p className="font-display text-[38px] leading-none tracking-tight text-ink tabular-nums">
                {formatMoney(props.total, currency)}
              </p>
            </div>
          </div>
          <div aria-hidden className="mt-6 flex h-8 items-stretch justify-center gap-[2px] opacity-70">
            {Array.from({ length: 46 }, (_, i) => (
              <span key={i} className="bg-ink" style={{ width: [1, 2, 1, 3, 1, 1, 2][(i * 7) % 7] }} />
            ))}
          </div>
        </div>
      </motion.div>
    );
  },
});

/* ------------------------------ BookingTicket ---------------------------- */
function hash(str: string) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h ^= h << 13;
    h ^= h >>> 17;
    h ^= h << 5;
    return ((h >>> 0) % 1000) / 1000;
  };
}

function QrPattern({ seed, className }: { seed: string; className?: string }) {
  const N = 25;
  const cells = useMemo(() => {
    const rnd = hash(seed || "WANDER");
    const out: [number, number][] = [];
    const inFinder = (x: number, y: number) =>
      (x < 8 && y < 8) || (x >= N - 8 && y < 8) || (x < 8 && y >= N - 8);
    for (let y = 0; y < N; y++)
      for (let x = 0; x < N; x++) if (!inFinder(x, y) && rnd() > 0.52) out.push([x, y]);
    return out;
  }, [seed]);
  const finder = (x: number, y: number) => (
    <g key={`${x}-${y}`}>
      <rect x={x + 0.5} y={y + 0.5} width={6} height={6} rx={1.4} fill="none" stroke="currentColor" strokeWidth={1} />
      <rect x={x + 2} y={y + 2} width={3} height={3} rx={0.7} fill="currentColor" />
    </g>
  );
  return (
    <svg viewBox={`0 0 ${N} ${N}`} className={className} aria-hidden>
      {cells.map(([x, y]) => (
        <rect key={`${x}.${y}`} x={x + 0.08} y={y + 0.08} width={0.84} height={0.84} rx={0.22} fill="currentColor" />
      ))}
      {finder(0, 0)}
      {finder(N - 7, 0)}
      {finder(0, N - 7)}
    </svg>
  );
}

function Field({ k, v, sub, className }: { k: string; v: string; sub?: string; className?: string }) {
  return (
    <div className={cx("min-w-0", className)}>
      <p className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3">{k}</p>
      <p className="mt-1 truncate font-display text-[19px] text-ink">{v}</p>
      {sub ? <p className="text-[12px] text-ink-3">{sub}</p> : null}
    </div>
  );
}

export const BookingTicket = defineComponent({
  name: "BookingTicket",
  description:
    "Boarding-pass style booking confirmation with confirmation code and scannable-looking pass. Use after create_booking with its exact values.",
  props: z.object({
    code: z.string().describe('Confirmation code from create_booking, e.g. "WND-7K3Q9"'),
    stayName: z.string().describe("Stay name"),
    location: z.string().describe("Place"),
    image: z.string().describe("Cover image URL returned by a tool"),
    checkIn: z.string().describe("YYYY-MM-DD"),
    checkOut: z.string().describe("YYYY-MM-DD"),
    guests: z.number().describe("Total guests"),
    total: z.number().describe("Amount paid"),
    currency: z.string().optional().describe('Default "INR"'),
  }),
  component: ({ props }) => {
    const nights = nightsBetween(props.checkIn, props.checkOut);
    const ci = parseISODate(props.checkIn);
    const co = parseISODate(props.checkOut);
    const yearOf = (d: Date | null) => (d ? String(d.getFullYear()) : "");
    return (
      <motion.div
        initial={{ opacity: 0, y: 28, rotate: -1.2, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, rotate: 0, scale: 1 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className="ticket-wrap w-full"
      >
        <div className="ticket relative flex flex-col overflow-hidden rounded-[10px] bg-[#fffdf8] md:flex-row">
          {/* photo panel, mounted like a print */}
          <div className="relative shrink-0 p-3 pb-0 md:w-[30%] md:p-3.5 md:pr-0">
            <div className="relative h-44 overflow-hidden rounded-[3px] md:h-full md:min-h-[230px]">
              <SmartImage src={sized(props.image, 900)} alt={props.stayName ?? ""} className="absolute inset-0" imgClassName="sepia-[0.1]" />
              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(20,24,40,0.05),rgba(20,24,40,0.75))]" />
              <PostageStamp value="₹25" tint="var(--sage)" className="absolute right-2.5 top-2.5 w-[56px] rotate-6">
                <MountainTreehouse className="aspect-square w-full" />
              </PostageStamp>
              <div className="absolute inset-x-0 bottom-0 p-4">
                <p className="font-display text-[26px] leading-[1.02] text-white text-balance">{props.stayName}</p>
                <p className="mt-1 flex items-center gap-1.5 font-hand text-[19px] leading-none text-white/90">
                  <IconPin size={13} /> {props.location}
                </p>
              </div>
            </div>
          </div>
          {/* main */}
          <div className="relative min-w-0 flex-1 px-6 py-6 sm:px-7">
            <p className="flex items-baseline gap-2.5">
              <span className="font-display text-[22px] italic text-ink">Wander</span>
              <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-ink-3">Stay pass</span>
            </p>
            <div className="mt-6 flex items-center gap-3 sm:gap-4">
              <div className="min-w-0">
                <p className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3">Check-in</p>
                <p className="whitespace-nowrap font-display text-[30px] leading-none text-ink sm:text-[36px]">{formatShortDate(props.checkIn)}</p>
                <p className="mt-1 whitespace-nowrap text-[11.5px] text-ink-3 sm:text-[12px]">
                  {ci ? ci.toLocaleDateString("en-GB", { weekday: "short" }) : ""} · from 2 PM
                </p>
              </div>
              <div className="flex min-w-0 flex-1 items-center gap-1.5 text-ink-3 sm:gap-2 sm:px-1">
                <span className="size-1.5 rounded-full bg-terracotta" />
                <span className="h-0 flex-1 border-t-[1.5px] border-dotted border-ink/40" />
                <span className="whitespace-nowrap font-hand text-[19px] leading-none text-ink-2">
                  {nights || "—"} {nights === 1 ? "night" : "nights"}
                </span>
                <span className="h-0 flex-1 border-t-[1.5px] border-dotted border-ink/40" />
                <span className="size-1.5 rounded-full border border-terracotta" />
              </div>
              <div className="min-w-0 text-right">
                <p className="whitespace-nowrap font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3">Check-out</p>
                <p className="whitespace-nowrap font-display text-[30px] leading-none text-ink sm:text-[36px]">{formatShortDate(props.checkOut)}</p>
                <p className="mt-1 whitespace-nowrap text-[11.5px] text-ink-3 sm:text-[12px]">
                  {co ? co.toLocaleDateString("en-GB", { weekday: "short" }) : ""} · by 11 AM
                </p>
              </div>
            </div>
            <div className="mt-6 grid grid-cols-3 gap-4 border-t-[1.5px] border-dashed border-ink/15 pt-5">
              <Field k="Guests" v={String(props.guests ?? "—")} />
              <Field k="Year" v={yearOf(ci) || "—"} />
              <Field k="Paid" v={formatMoney(props.total, props.currency ?? "INR")} className="text-right" />
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 1.8, rotate: -24 }}
              animate={{ opacity: 0.9, scale: 1, rotate: -11 }}
              transition={{ delay: 0.55, duration: 0.35, ease: [0.5, 0, 0.75, 0] }}
              className="pointer-events-none absolute right-4 top-5 w-[110px] mix-blend-multiply sm:right-5 sm:top-2 sm:w-[150px]"
            >
              <InkStamp text="CONFIRMED" sub={ci ? ci.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }).toUpperCase() : undefined} className="w-full" />
            </motion.div>
          </div>
          {/* perforation + stub */}
          <div className="ticket-perf relative" aria-hidden />
          <div className="relative flex shrink-0 flex-row items-center justify-between gap-5 bg-surface-2/70 px-6 py-5 md:w-[210px] md:flex-col md:justify-center md:px-5 md:py-6">
            <div className="md:text-center">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-3">Confirmation</p>
              <p className="mt-1 font-mono text-[20px] font-medium tracking-[0.08em] text-ink">{props.code}</p>
            </div>
            <div className="rounded-[4px] border border-ink/15 bg-[#fffdf8] p-2.5 text-ink">
              <QrPattern seed={props.code ?? ""} className="size-[84px] md:size-[104px]" />
            </div>
          </div>
        </div>
      </motion.div>
    );
  },
});
