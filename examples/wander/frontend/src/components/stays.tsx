import { action, defineComponent, useIsStreaming, useTriggerAction } from "@openuidev/react-lang";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { z } from "zod/v4";
import { cx, formatMoney } from "./bridge";
import { AmenityIcon, IconArrowRight, IconChevronLeft, IconChevronRight, IconPin, IconStar } from "./icons";
import { RichText, fadeUp } from "./ui";

/** Image with a shimmer placeholder and a graceful gradient fallback. */
export function SmartImage({
  src,
  alt,
  className,
  imgClassName,
  sizes,
  eager,
}: {
  src?: string;
  alt: string;
  className?: string;
  imgClassName?: string;
  sizes?: string;
  eager?: boolean;
}) {
  // Track which src finished, so a cached image that loads before effects run still shows.
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const [errorSrc, setErrorSrc] = useState<string | null>(null);
  const state: "loading" | "loaded" | "error" =
    src && errorSrc === src ? "error" : src && loadedSrc === src ? "loaded" : "loading";
  const valid = typeof src === "string" && /^https?:\/\//.test(src);
  return (
    <div className={cx("overflow-hidden bg-surface-2", !/\babsolute\b/.test(className ?? "") && "relative", className)}>
      {(!valid || state !== "loaded") && (
        <div className={cx("absolute inset-0", state === "error" || !valid ? "img-fallback" : "shimmer")} />
      )}
      {valid && state !== "error" ? (
        <img
          src={src}
          alt={alt}
          sizes={sizes}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          draggable={false}
          ref={(el) => {
            if (el && el.complete && el.naturalWidth > 0 && loadedSrc !== src) setLoadedSrc(src ?? null);
          }}
          onLoad={() => setLoadedSrc(src ?? null)}
          onError={() => setErrorSrc(src ?? null)}
          className={cx(
            "absolute inset-0 size-full object-cover transition-[opacity,transform] duration-700",
            state === "loaded" ? "opacity-100" : "opacity-0",
            imgClassName,
          )}
        />
      ) : null}
    </div>
  );
}

/** Unsplash URLs get a sensible width; anything else is returned as-is. */
export function sized(url: string | undefined, w: number): string | undefined {
  if (!url) return url;
  if (!url.includes("images.unsplash.com")) return url;
  try {
    const u = new URL(url);
    u.searchParams.set("w", String(w));
    if (!u.searchParams.has("q")) u.searchParams.set("q", "80");
    if (!u.searchParams.has("auto")) u.searchParams.set("auto", "format");
    if (!u.searchParams.has("fit")) u.searchParams.set("fit", "crop");
    return u.toString();
  } catch {
    return url;
  }
}

function RatingPill({ rating, className }: { rating?: number; className?: string }) {
  if (typeof rating !== "number") return null;
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full bg-[#fffdf8]/92 px-2.5 py-1 text-[12.5px] font-semibold text-ink shadow-[0_1px_2px_rgba(0,0,0,0.2)]",
        className,
      )}
    >
      <IconStar size={12} className="text-mustard" />
      {rating.toFixed(2).replace(/0$/, "")}
    </span>
  );
}

/* -------------------------------- StayCard ------------------------------- */
const TAPES = ["var(--mustard)", "var(--sky)", "var(--sage)", "var(--terracotta)"];
function hashStr(str: string) {
  let h = 7;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}

export const StayCard = defineComponent({
  name: "StayCard",
  description:
    'A bookable stay as a photo card. Only inside StayGrid. Use values exactly as returned by search_stays. Clicking sends action (default: @ToAssistant("Show <name>", {"stayId": id})).',
  props: z.object({
    id: z.string().describe("Stay id from search_stays"),
    name: z.string().describe("Stay name"),
    location: z.string().describe('Place, e.g. "Manali, Himachal Pradesh"'),
    image: z.string().describe("Cover image URL — MUST be the exact `image` URL returned by a tool, never invented"),
    pricePerNight: z.number().describe("Nightly price in INR (number, no symbols)"),
    rating: z.number().describe("Guest rating 0-5, e.g. 4.92"),
    tags: z.array(z.string()).optional().describe('1-3 short tags, e.g. ["Treehouse", "Mountain view"]'),
    action: action()
      .optional()
      .describe('Click action, e.g. @ToAssistant("Show Pine Hollow Treehouse", {"stayId": "pine-hollow"})'),
  }),
  component: ({ props }) => {
    const triggerAction = useTriggerAction();
    const isStreaming = useIsStreaming();
    const name = props.name ?? "";
    const open = () => {
      if (isStreaming || !name) return;
      if (props.action) void triggerAction(`Show ${name}`, undefined, props.action as never);
      else
        void triggerAction(`Show ${name}`, undefined, {
          type: "continue_conversation",
          params: { context: { stayId: props.id } },
        });
    };
    const tags = (props.tags ?? []).filter(Boolean).slice(0, 3);
    const seed = hashStr(props.id ?? name);
    const tilt = ((seed % 5) - 2) * 0.55;
    const tape = TAPES[seed % TAPES.length];
    return (
      <motion.article
        variants={{ hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0 } }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="group/card relative min-w-0 pt-3"
      >
        <button
          type="button"
          onClick={open}
          aria-label={name ? `View ${name}` : "View stay"}
          style={{ ["--tilt" as string]: `${tilt}deg` }}
          className="relative block w-full rotate-[var(--tilt)] cursor-pointer rounded-[3px] bg-[#fffdf8] p-2.5 pb-4 text-left shadow-card outline-none transition-all duration-500 ease-[cubic-bezier(.22,1,.36,1)] hover:-translate-y-1.5 hover:rotate-[calc(var(--tilt)*-1.6)] hover:shadow-card-hover focus-visible:ring-2 focus-visible:ring-teal/70 focus-visible:ring-offset-4 focus-visible:ring-offset-bg"
        >
          <span className="tape -top-3 left-1/2 w-20 -translate-x-1/2 -rotate-3" style={{ ["--tape" as string]: tape }} />
          <div className="relative overflow-hidden rounded-[1px]">
            <SmartImage
              src={sized(props.image, 900)}
              alt={name}
              className="aspect-[4/3.6]"
              imgClassName="group-hover/card:scale-[1.05] duration-[1200ms] saturate-[0.92] sepia-[0.08]"
            />
            <div className="pointer-events-none absolute inset-0 shadow-[inset_0_0_0_1px_rgba(31,42,68,0.08)]" />
            <RatingPill rating={props.rating} className="absolute right-2.5 top-2.5" />
          </div>
          <div className="px-1.5 pt-3.5">
            <h3 className="font-display text-[22px] font-normal leading-[1.08] tracking-[-0.01em] text-ink text-balance">{name || " "}</h3>
            <p className="mt-1 flex items-center gap-1 font-hand text-[19px] leading-tight text-terracotta">
              <IconPin size={14} className="shrink-0" />
              <span className="truncate">{props.location}</span>
            </p>
            {tags.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-[3px] border border-ink/20 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.1em] text-ink-2"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-3.5 flex items-end justify-between gap-3 border-t border-dashed border-ink/20 pt-3">
              <p className="text-ink">
                <span className="text-[18px] font-semibold tracking-tight">{formatMoney(props.pricePerNight)}</span>
                <span className="ml-1 text-[12.5px] text-ink-3">/ night</span>
              </p>
              <span className="inline-flex items-center gap-1 text-[13px] font-medium text-ink-2 transition-all duration-300 group-hover/card:translate-x-0.5 group-hover/card:text-terracotta">
                View stay <IconArrowRight size={14} />
              </span>
            </div>
          </div>
        </button>
      </motion.article>
    );
  },
});

/* -------------------------------- StayGrid ------------------------------- */
export const StayGrid = defineComponent({
  name: "StayGrid",
  description: "Responsive gallery of StayCard results (ideally 3-6). Use after search_stays.",
  props: z.object({
    stays: z.array(StayCard.ref).describe("StayCard components"),
  }),
  component: ({ props, renderNode }) => {
    const stays = Array.isArray(props.stays) ? props.stays : [];
    return (
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.09 } } }}
        className="-mx-5 flex snap-x snap-mandatory gap-5 overflow-x-auto px-5 pb-6 pt-1 scrollbar-none sm:mx-0 sm:grid sm:grid-cols-2 sm:gap-7 sm:overflow-visible sm:px-0 sm:pb-2 lg:grid-cols-3 [&>*]:w-[78%] [&>*]:shrink-0 [&>*]:snap-center sm:[&>*]:w-auto"
      >
        {renderNode(stays)}
      </motion.div>
    );
  },
});

/* ------------------------------- StayDetail ------------------------------ */
function Gallery({ images, name }: { images: string[]; name: string }) {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState(1);
  const count = images.length;
  const go = useCallback(
    (delta: number) => {
      if (!count) return;
      setDir(delta);
      setIndex((i) => (i + delta + count) % count);
    },
    [count],
  );
  useEffect(() => {
    if (index >= count && count > 0) setIndex(0);
  }, [count, index]);

  if (!count) return <div className="shimmer aspect-[16/10] rounded-[3px]" />;
  const current = images[Math.min(index, count - 1)];
  return (
    <div className="flex flex-col gap-5">
      <div className="relative -rotate-[0.6deg] bg-[#fffdf8] p-2.5 pb-3 shadow-card sm:p-3.5 sm:pb-4">
      <span className="tape -left-4 top-3 w-24 -rotate-[38deg]" style={{ ["--tape" as string]: "var(--mustard)" }} />
      <span className="tape -right-4 bottom-4 w-24 -rotate-[36deg]" style={{ ["--tape" as string]: "var(--sky)" }} />
      <div
        className="group/gal relative aspect-[4/3] overflow-hidden rounded-[1px] bg-surface-2 sm:aspect-[16/9]"
        tabIndex={0}
        role="region"
        aria-roledescription="carousel"
        aria-label={`${name} photos`}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") go(1);
          if (e.key === "ArrowLeft") go(-1);
        }}
      >
        <AnimatePresence initial={false} custom={dir} mode="popLayout">
          <motion.div
            key={current + index}
            custom={dir}
            initial={{ opacity: 0, x: dir * 60, scale: 1.04 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: dir * -60, scale: 0.98 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            drag={count > 1 ? "x" : false}
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.18}
            onDragEnd={(_, info) => {
              if (info.offset.x < -50 || info.velocity.x < -400) go(1);
              else if (info.offset.x > 50 || info.velocity.x > 400) go(-1);
            }}
            className="absolute inset-0 cursor-grab active:cursor-grabbing"
          >
            <SmartImage src={sized(current, 1600)} alt={`${name} — photo ${index + 1}`} className="size-full" />
          </motion.div>
        </AnimatePresence>
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,transparent_60%,rgba(0,0,0,0.45))]" />
        {count > 1 && (
          <>
            <button
              type="button"
              aria-label="Previous photo"
              onClick={() => go(-1)}
              className="absolute left-4 top-1/2 hidden size-11 -translate-y-1/2 place-items-center rounded-full bg-black/35 text-white opacity-0 backdrop-blur-md ring-1 ring-white/20 transition-all duration-300 hover:bg-black/55 group-hover/gal:opacity-100 focus-visible:opacity-100 sm:grid"
            >
              <IconChevronLeft size={20} />
            </button>
            <button
              type="button"
              aria-label="Next photo"
              onClick={() => go(1)}
              className="absolute right-4 top-1/2 hidden size-11 -translate-y-1/2 place-items-center rounded-full bg-black/35 text-white opacity-0 backdrop-blur-md ring-1 ring-white/20 transition-all duration-300 hover:bg-black/55 group-hover/gal:opacity-100 focus-visible:opacity-100 sm:grid"
            >
              <IconChevronRight size={20} />
            </button>
            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-1.5">
              {images.map((_, i) => (
                <span
                  key={i}
                  className={cx(
                    "h-1.5 rounded-full bg-white transition-all duration-500",
                    i === index ? "w-6 opacity-100" : "w-1.5 opacity-50",
                  )}
                />
              ))}
            </div>
            <span className="absolute bottom-4 right-4 rounded-full bg-black/40 px-2.5 py-1 font-mono text-[11px] text-white/90 backdrop-blur-md">
              {index + 1} / {count}
            </span>
          </>
        )}
      </div>
      </div>
      {count > 1 && (
        <div className="-m-2 flex gap-3 overflow-x-auto p-2 pb-3 scrollbar-none">
          {images.map((img, i) => (
            <button
              key={img + i}
              type="button"
              aria-label={`Show photo ${i + 1}`}
              aria-current={i === index}
              onClick={() => {
                setDir(i > index ? 1 : -1);
                setIndex(i);
              }}
              style={{ rotate: `${[-2, 1.5, -1, 2, -1.5, 1][i % 6]}deg` }}
              className={cx(
                "relative shrink-0 bg-[#fffdf8] p-1 pb-2.5 shadow-[0_1px_2px_rgba(60,40,10,0.18),0_6px_10px_-6px_rgba(60,40,10,0.3)] outline-none transition-all duration-300 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal/70",
                i === index ? "-translate-y-1 ring-[1.5px] ring-terracotta" : "opacity-75 hover:opacity-100",
              )}
            >
              <SmartImage src={sized(img, 300)} alt="" className="h-14 w-20 sm:h-[66px] sm:w-[96px]" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export const StayDetail = defineComponent({
  name: "StayDetail",
  description:
    "Full detail view of one stay: swipeable photo gallery, story, amenities, rating and nightly price. Use after get_stay, with the tool's values verbatim.",
  props: z.object({
    id: z.string().describe("Stay id"),
    name: z.string().describe("Stay name"),
    location: z.string().describe("Place"),
    images: z.array(z.string()).describe("Gallery image URLs exactly as returned by get_stay (`images`)"),
    description: z.string().describe("2-4 sentence story of the place"),
    amenities: z.array(z.string()).describe('Amenities, e.g. ["Wood-fired hot tub", "Wi-Fi", "Chef-cooked breakfast"]'),
    pricePerNight: z.number().describe("Nightly price in INR"),
    rating: z.number().describe("Guest rating 0-5"),
    reviews: z.number().describe("Number of reviews"),
  }),
  component: ({ props }) => {
    const images = (props.images ?? []).filter((s): s is string => typeof s === "string" && s.length > 8);
    const amenities = (props.amenities ?? []).filter(Boolean);
    return (
      <motion.section {...fadeUp} className="flex min-w-0 flex-col gap-7">
        <Gallery images={images} name={props.name ?? ""} />
        <div className="grid gap-8 lg:grid-cols-[1fr_260px] lg:gap-12">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 font-hand text-[23px] leading-none text-terracotta">
              <IconPin size={16} /> {props.location}
            </p>
            <h2 className="mt-2 font-display text-[38px] font-normal leading-[1.02] tracking-[-0.025em] text-ink text-balance sm:text-[54px]">
              {props.name}
            </h2>
            {props.description ? (
              <p className="mt-4 max-w-[62ch] text-[16px] leading-[1.75] text-ink-2 text-pretty">
                <RichText text={props.description} />
              </p>
            ) : null}
          </div>
          <div className="flex flex-row items-stretch gap-3 lg:flex-col">
            <div className="flex-1 rotate-[0.8deg] rounded-[3px] border-[1.5px] border-dashed border-ink/25 bg-surface p-4">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-3">From</p>
              <p className="mt-1 font-display text-[24px] tracking-tight text-ink sm:text-[28px]">
                {formatMoney(props.pricePerNight)}
                <span className="ml-1 whitespace-nowrap font-sans text-[13px] font-normal text-ink-3">/ night</span>
              </p>
            </div>
            <div className="flex-1 -rotate-[0.6deg] rounded-[3px] border-[1.5px] border-dashed border-ink/25 bg-surface p-4">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-3">Guests love it</p>
              <p className="mt-1 flex flex-wrap items-center gap-x-1.5 font-display text-[24px] sm:text-[28px] tracking-tight text-ink">
                <IconStar size={20} className="text-mustard" />
                {typeof props.rating === "number" ? props.rating.toFixed(2) : "—"}
                <span className="font-sans text-[13px] font-normal text-ink-3">
                  {typeof props.reviews === "number" ? `${props.reviews} reviews` : ""}
                </span>
              </p>
            </div>
          </div>
        </div>
        {amenities.length > 0 && (
          <div>
            <p className="mb-3 font-hand text-[24px] leading-none text-ink">What this place offers</p>
            <ul className="grid grid-cols-2 gap-x-4 sm:gap-x-6 lg:grid-cols-3">
              {amenities.map((a, i) => (
                <motion.li
                  key={a + i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.03 * i, duration: 0.4 }}
                  className="flex min-w-0 items-center gap-2.5 border-b border-dashed border-ink/15 py-2.5 text-[13.5px] text-ink-2 sm:gap-3 sm:text-[14.5px]"
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-full border-[1.5px] border-ink/50 text-ink">
                    <AmenityIcon name={a} size={17} />
                  </span>
                  <span className="min-w-0 truncate">{a}</span>
                </motion.li>
              ))}
            </ul>
          </div>
        )}
      </motion.section>
    );
  },
});
