/**
 * Hand-drawn ink illustrations for Wander's travel-journal look.
 * All original inline SVG: slightly irregular strokes in ink navy + soft watercolour washes.
 */
import { motion } from "motion/react";
import { useId, type ReactNode, type SVGProps } from "react";
import { cx } from "./bridge";

type SvgProps = SVGProps<SVGSVGElement> & { title?: string };

const ink = "var(--ink)";

/** Base for line art: round caps, currentColor ink. */
function Sketch({ children, viewBox = "0 0 240 160", title, className, ...rest }: SvgProps & { children: ReactNode }) {
  return (
    <svg
      viewBox={viewBox}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      className={cx("text-ink", className)}
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Watercolour wash: a soft blob of colour under the ink. */
function Wash({ d, color, opacity = 0.32 }: { d: string; color: string; opacity?: number }) {
  return <path d={d} fill={color} stroke="none" opacity={opacity} />;
}

/** Shared "rough ink" filter — mount once near the root. */
export function SketchDefs() {
  return (
    <svg width="0" height="0" className="absolute" aria-hidden>
      <defs>
        <filter id="wander-rough" x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="3" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" />
        </filter>
      </defs>
    </svg>
  );
}

/* ------------------------------------------------------------- vignettes */
export function MountainTreehouse(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M190 38m-15 0a15 14 0 1 0 30 0a15 14 0 1 0 -30 0" color="var(--mustard)" opacity={0.4} />
      <Wash d="M6 114 L48 60 L66 78 L98 34 L126 70 L142 56 L190 108 Z" color="var(--sky)" opacity={0.35} />
      <path d="M5 113 L47.5 59 L66 77.5 L98.5 33 L126 70.5 L142.5 55.5 L188 106" />
      <path d="M88 47 l10.5 -13.5 l9 12.2 l-5.4 -2.4 l-3.8 4.2 l-4.2 -3.6 z" fill="var(--surface)" />
      <path d="M41 68 l6.5 -8.5 l5.6 5.8 l-3.6 -1 l-2.6 3 z" fill="var(--surface)" />
      <path d="M58 30 q4 -4.5 8 0 q4 -4.5 8 0 M78 22 q3 -3.5 6 0 q3 -3.5 6 0" strokeWidth={1.3} />
      {/* deodar */}
      <Wash
        d="M150 34 C146 48 140 56 131 64 L144 63 C138 75 130 83 121 91 L140 89 C134 101 126 109 117 115 L183 115 C174 109 166 101 160 89 L179 91 C170 83 162 75 156 63 L169 64 C160 56 154 48 150 34 Z"
        color="var(--sage)"
        opacity={0.38}
      />
      <path d="M150 34 C146.5 48 140 56.5 131 64.2 L144 63 C138.5 75 130.5 83 121 91.2 L140 89 C134 101 126 109.5 117 115 M183 115 C174 109 166 101 160 89 L179 91.2 C170 83 162 75 156 63 L169 64 C160.5 56 154 48 150 34" />
      <path d="M150.5 112 L150 150" strokeWidth={2.2} />
      {/* treehouse */}
      <path d="M124 104.5 L178 103.5" strokeWidth={2} />
      <path d="M134 104 L134.5 85 L166 84.5 L166.5 104" fill="var(--surface)" />
      <path d="M128.5 87 L150.5 70 L172 86.5" />
      <path d="M144.5 90 h10 v8.5 h-10 z" fill="var(--mustard)" fillOpacity={0.7} />
      <path d="M159 76 c-3 -6 4 -8 0.5 -14 c-3 -5 3 -8 1 -12" strokeWidth={1.2} opacity={0.7} />
      <path d="M140 104 L136.5 150 M146.5 104 L143 150 M138.6 117 h6.4 M137.8 127 h6.4 M137 137 h6.4" strokeWidth={1.3} />
      {/* small pines + ground */}
      <path d="M28 150 L28.5 134 M28 116 L19.5 134.5 L37.5 134 Z M210 150 V138 M210 122 L203 138.5 L217 138 Z" />
      <path d="M4 150.5 C40 146.5 80 152 120 149.2 S200 146 236 150" />
      <path d="M58 156 h18 M168 156 h26" strokeWidth={1.1} opacity={0.6} />
    </Sketch>
  );
}

export function Houseboat(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 118 C60 112 180 112 240 118 L240 160 L0 160 Z" color="var(--teal)" opacity={0.22} />
      <Wash d="M62 112 C64 84 92 75 121 75 C150 75 178 84 182 110 Z" color="var(--mustard)" opacity={0.42} />
      {/* palms */}
      <path d="M208 116 C203 90 203 64 212 40" strokeWidth={2} />
      <path d="M212 40 c-12 -6 -25 -2 -31 6 M212 40 c8 -10 22 -12 30 -6 M212 40 c-4 -12 -14 -18 -25 -18 M212 40 c10 2 19 12 19 23 M212 40 c-10 4 -17 14 -17 25" />
      <path d="M34 116 C36 94 32 74 24 58" strokeWidth={2} />
      <path d="M24 58 c10 -7 22 -5 28 2 M24 58 c-6 -9 -18 -11 -24 -6 M24 58 c3 -11 12 -16 22 -15 M24 58 c-8 3 -12 12 -11 21" />
      {/* kettuvallam */}
      <path d="M62 112 C64 84 92 75.5 121 75 C150 75 178 84 182.5 110" />
      <path d="M78 104 C79 92 84 86 92 82 M100 102 V79 M121 102 V76 M142 102 V79 M162 104 C161 92 157 86 150 82" strokeWidth={1.1} opacity={0.7} />
      <path d="M86 112 V100 h14 v12 M134 112 V100 h16 v12" fill="var(--surface)" />
      <path d="M40 112.5 C70 128 170 128.5 204.5 108" strokeWidth={2} fill="var(--surface)" />
      <path d="M40 112.5 C34 104 30 100 24 98.5 M204.5 108 C212 102 216 96 222 94" strokeWidth={2} />
      <path d="M46 116 C80 124 160 125 198 112" strokeWidth={1.1} />
      {/* water */}
      <path d="M14 136 q10 -4 20 0 t20 0 M86 142 q8 -3.5 16 0 t16 0 t16 0 M168 134 q9 -4 18 0 t18 0 M40 150 q8 -3 16 0 t16 0 M150 152 q8 -3 16 0" strokeWidth={1.2} opacity={0.75} />
      <path d="M150 26 q4 -4.5 8 0 q4 -4.5 8 0" strokeWidth={1.3} />
    </Sketch>
  );
}

export function DesertCamp(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 126 C40 102 80 102 120 120 S200 104 240 118 L240 160 L0 160 Z" color="var(--mustard)" opacity={0.38} />
      <Wash d="M0 144 C50 130 110 132 150 146 S220 136 240 140 L240 160 L0 160 Z" color="var(--terracotta)" opacity={0.2} />
      <path d="M0 126.5 C40 102 80 102.5 120 120 S200 104 240 118" />
      <path d="M0 144 C50 130 110 132 150 146.5 S220 136 240 140" strokeWidth={1.2} />
      {/* moon + stars */}
      <path d="M44 24 a13 13 0 1 0 14 18 a10 10 0 1 1 -14 -18 z" fill="var(--mustard)" fillOpacity={0.5} />
      <path d="M96 20 v6 M93 23 h6 M150 34 v5 M147.5 36.5 h5 M120 14 v4 M118 16 h4 M196 22 v6 M193 25 h6 M76 46 v3 M74.5 47.5 h3" strokeWidth={1.2} />
      {/* dome tent */}
      <path d="M92 121 A36 32 0 0 1 164 119" fill="var(--surface)" strokeWidth={1.8} />
      <path d="M100 103 C116 96 140 96 156 102 M112 91 L128 120 L144 91 M128 87 V120 M104 110 L118 92 M152 110 L138 92" strokeWidth={1.1} />
      <path d="M121 120 v-10 a7 7 0 0 1 14 0 v10" fill="var(--terracotta)" fillOpacity={0.35} />
      {/* camel */}
      <path d="M176 109 C179 93 195 92 199 104 C203 97 211 99 213.5 108" />
      <path d="M213.5 108 C219 101 221 93 225 88.5 L232 90.5 L230 94" />
      <path d="M176 109 C189 116.5 205 116 213.5 108" />
      <path d="M182 112 L180 129 M190 114 L190.5 129.5 M203 114 L205 129 M211 111 L213.5 128.5" />
      <path d="M176 109 c-3 3 -4 8 -3 12" strokeWidth={1.2} />
    </Sketch>
  );
}

export function LadakhCamp(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 106 L44 52 L70 78 L112 26 L150 72 L174 50 L240 112 L240 116 L0 116 Z" color="var(--sky)" opacity={0.35} />
      <Wash d="M0 120 C60 114 180 116 240 122 L240 134 C170 130 60 130 0 134 Z" color="var(--teal)" opacity={0.35} />
      <path d="M0 106 L44 52 L70 78.5 L112 26 L150 72.5 L174 50 L240 112" />
      <path d="M100 41 l12 -15 l11 14 l-6 -2.5 l-4.5 4 l-5 -3.5 z M37 61 l7 -9 l6.5 6.5 l-4 -1.2 l-3 3 z M167 57 l7 -7 l7 6.5 l-4 -0.8 l-3 2.4 z" fill="var(--surface)" />
      <path d="M0 120.5 C60 114 180 116.5 240 122 M30 128 q8 -3 16 0 t16 0 M150 128 q8 -3 16 0 t16 0" strokeWidth={1.2} />
      {/* prayer flags */}
      <path d="M14 70 Q96 100 196 64" strokeWidth={1.1} />
      {[
        [34, 77, "var(--sky)"],
        [54, 83, "var(--surface)"],
        [74, 87, "var(--terracotta)"],
        [94, 89, "var(--sage)"],
        [114, 88, "var(--mustard)"],
        [134, 85, "var(--sky)"],
        [154, 80, "var(--surface)"],
        [174, 73, "var(--terracotta)"],
      ].map(([x, y, c], i) => (
        <path key={i} d={`M${x} ${y} l9 0.6 l-0.6 10 l-9 -0.6 z`} fill={c as string} fillOpacity={0.7} strokeWidth={1.1} />
      ))}
      {/* tents */}
      <path d="M58 150 L88 110 L120 150 Z" fill="var(--surface)" />
      <path d="M88 110 L84 150 M78 150 C80 140 84 134 86 128" strokeWidth={1.2} />
      <path d="M88 110 l2 -8 M88 102 l6 2 l-6 2" strokeWidth={1.2} />
      <path d="M140 150 L160 124 L182 150 Z" fill="var(--surface)" />
      <path d="M160 124 L157 150" strokeWidth={1.2} />
      <path d="M4 151 C70 148 160 152 236 150" />
      <path d="M196 150 c0 -6 4 -10 8 -12 M200 146 c2 -4 6 -6 9 -6" strokeWidth={1.1} opacity={0.6} />
    </Sketch>
  );
}

export function CoffeeEstate(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 110 C50 88 110 90 160 104 S220 98 240 92 L240 160 L0 160 Z" color="var(--sage)" opacity={0.35} />
      <Wash d="M0 136 C60 122 120 124 240 134 L240 160 L0 160 Z" color="var(--sage)" opacity={0.3} />
      <path d="M0 110 C50 88 110 90.5 160 104 S220 98 240 92" />
      <path d="M0 136 C60 122 120 124.5 240 134" />
      {/* bush rows */}
      <path d="M8 120 q5 -6 10 0 q5 -6 10 0 q5 -6 10 0 M58 116 q5 -6 10 0 q5 -6 10 0 q5 -6 10 0 M120 118 q5 -6 10 0 q5 -6 10 0 q5 -6 10 0 q5 -6 10 0 M190 112 q5 -6 10 0 q5 -6 10 0 q5 -6 10 0" strokeWidth={1.2} />
      <path d="M20 148 q6 -7 12 0 q6 -7 12 0 q6 -7 12 0 M96 146 q6 -7 12 0 q6 -7 12 0 q6 -7 12 0 q6 -7 12 0 M180 150 q6 -7 12 0 q6 -7 12 0 q6 -7 12 0" strokeWidth={1.2} />
      {/* cottage */}
      <path d="M150 99 V76 H190 V96" fill="var(--surface)" />
      <path d="M144 78 L162 60 H184 L196 78" fill="var(--terracotta)" fillOpacity={0.35} />
      <path d="M176 60 V50 h6 v10" />
      <path d="M179 46 c-3 -5 3 -7 0 -12 c-2 -4 2 -6 1 -9" strokeWidth={1.1} opacity={0.6} />
      <path d="M158 99 V86 h8 v13 M174 84 h9 v7 h-9 z" />
      {/* mist + silver oak */}
      <path d="M20 60 h46 M36 68 h40 M120 40 h34" strokeWidth={1.2} opacity={0.5} />
      <path d="M62 104 V64 M62 74 l-10 -8 M62 84 l12 -9 M62 66 c-6 -8 -2 -18 0 -22 c3 6 6 14 0 22" />
      <path d="M100 30 q4 -4 8 0 q4 -4 8 0" strokeWidth={1.3} />
    </Sketch>
  );
}

export function SpitiVillage(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 98 L52 40 L86 70 L130 22 L176 66 L200 50 L240 92 L240 160 L0 160 Z" color="var(--terracotta)" opacity={0.18} />
      <Wash d="M30 160 C60 120 100 96 150 92 C190 90 220 116 236 160 Z" color="var(--mustard)" opacity={0.3} />
      <path d="M0 98 L52 40.5 L86 70 L130 22 L176 66.5 L200 50 L240 92" />
      <path d="M120 34 l10 -12 l10 11 l-5 -2 l-4 3 l-4 -2.5 z" fill="var(--surface)" />
      <path d="M58 70 l8 10 M150 46 l10 14 M182 62 l6 8" strokeWidth={1.1} opacity={0.6} />
      <path d="M30 160 C60 120 100 96.5 150 92 C190 90 220 116 236 160" />
      {/* monastery + mud homes */}
      <path d="M128 92 V70 H170 V92" fill="var(--surface)" />
      <path d="M124 70 H174 M128 76 H170" strokeWidth={1.2} />
      <path d="M126 70 V66 H172 V70" fill="var(--terracotta)" fillOpacity={0.5} />
      <path d="M140 92 V82 h6 v10 M154 80 h8 v6 h-8 z" />
      <path d="M149 66 v-8 M146 58 h6 M149 58 l0 -4" strokeWidth={1.3} />
      <path d="M86 118 V102 H114 V114 M80 102 H120" fill="var(--surface)" />
      <path d="M92 108 h5 v5 h-5 z M104 108 h5 v5 h-5 z" fill="var(--ink)" fillOpacity={0.7} />
      <path d="M176 124 V106 H206 V128 M172 106 H210" fill="var(--surface)" />
      <path d="M184 112 h5 v6 h-5 z M196 112 h5 v6 h-5 z" fill="var(--ink)" fillOpacity={0.7} />
      <path d="M58 140 V124 H80 V134 M54 124 H84" fill="var(--surface)" />
      <path d="M64 130 h4 v5 h-4 z" fill="var(--ink)" fillOpacity={0.7} />
      <path d="M96 132 c10 4 30 6 50 2 M112 146 c16 3 36 3 52 -2" strokeWidth={1.1} opacity={0.6} />
    </Sketch>
  );
}

export function Shikara(p: SvgProps) {
  return (
    <Sketch {...p}>
      <Wash d="M0 70 L40 34 L70 54 L104 22 L140 56 L170 36 L240 78 Z" color="var(--sky)" opacity={0.3} />
      <Wash d="M0 96 C60 92 180 92 240 96 L240 160 L0 160 Z" color="var(--teal)" opacity={0.2} />
      <path d="M0 70 L40 34.5 L70 54 L104 22 L140 56.5 L170 36 L240 78" />
      <path d="M0 96.5 C60 92 180 92.5 240 96" strokeWidth={1.2} />
      <path d="M40 104 L70 120 M104 102 L104 124 M170 104 L150 122" strokeWidth={1} opacity={0.35} />
      {/* canopy */}
      <path d="M72 92 C100 84 140 84 168 92 L166 98 C140 92 100 92 74 98 Z" fill="var(--terracotta)" fillOpacity={0.45} />
      <path d="M80 97 V118 M160 97 V118 M120 90 V118" strokeWidth={1.3} />
      <path d="M86 100 h68" strokeWidth={1} strokeDasharray="2 3" />
      {/* hull */}
      <path d="M26 112 C70 128.5 170 129 216 110" strokeWidth={2} fill="var(--surface)" />
      <path d="M26 112 C20 106 16 104 10 103 M216 110 C222 104 226 101 232 100" strokeWidth={2} />
      {/* boatman + oar */}
      <path d="M196 112 V96 M196 92 m-3 0 a3 3 0 1 0 6 0 a3 3 0 1 0 -6 0 M196 100 L188 108 M178 96 L210 140" />
      <path d="M206 134 l8 10 l4 -3 l-8 -10" fill="var(--kraft)" />
      {/* lotus + ripples */}
      <path d="M44 140 c3 -6 7 -6 10 0 c3 -6 7 -6 10 0 M50 140 c2 -8 6 -10 9 -12 c3 2 6 4 7 12" strokeWidth={1.2} />
      <path d="M90 146 q8 -3 16 0 t16 0 M150 150 q8 -3 16 0 t16 0 M10 128 q8 -3 16 0" strokeWidth={1.1} opacity={0.75} />
    </Sketch>
  );
}

/* ---------------------------------------------------------------- objects */
export function CompassRose({ className, spin = false, ...p }: SvgProps & { spin?: boolean }) {
  return (
    <Sketch viewBox="0 0 100 100" className={className} {...p}>
      <circle cx="50" cy="50" r="42" />
      <circle cx="50" cy="50" r="36.5" strokeWidth={1} strokeDasharray="1.5 3.5" />
      <path d="M50 4 v6 M50 90 v6 M4 50 h6 M90 50 h6" strokeWidth={1.2} />
      <path d="M50 28 L56 50 L50 72 L44 50 Z M28 50 L50 44 L72 50 L50 56 Z" strokeWidth={1.1} opacity={0.55} transform="rotate(45 50 50)" />
      <motion.g
        animate={spin ? { rotate: [0, 28, -18, 10, 0] } : undefined}
        transition={spin ? { duration: 3.4, repeat: Infinity, ease: "easeInOut" } : undefined}
        style={{ originX: "50px", originY: "50px", transformBox: "view-box" }}
      >
        <path d="M50 14 L57 50 L50 86 L43 50 Z" fill="var(--surface)" />
        <path d="M50 14 L57 50 H43 Z" fill="var(--terracotta)" fillOpacity={0.85} />
        <path d="M14 50 L50 45 L86 50 L50 55 Z" fill="var(--surface)" />
      </motion.g>
      <circle cx="50" cy="50" r="3.4" fill="var(--surface)" />
    </Sketch>
  );
}

export function PaperPlane(p: SvgProps) {
  return (
    <Sketch viewBox="0 0 40 32" {...p}>
      <path d="M2 15 L37 3 L26 29 L18.5 19.5 Z" fill="var(--surface)" />
      <path d="M18.5 19.5 L37 3 M18.5 19.5 L17 27 L22 23" />
    </Sketch>
  );
}

/** Tiny looping plane + compass used as a "working on it" mark. */
export function CompassSpinner({ className }: { className?: string }) {
  return <CompassRose spin className={cx("size-7", className)} />;
}

/* --------------------------------------------------------------- dividers */
export function SketchDivider({ className, label }: { className?: string; label?: string }) {
  return (
    <div className={cx("flex items-center gap-3 text-ink-3", className)} aria-hidden>
      <svg viewBox="0 0 300 12" preserveAspectRatio="none" className="h-3 flex-1" fill="none" stroke="currentColor" strokeLinecap="round">
        <path d="M2 7 C40 4 70 9 110 6 S190 4 230 7 S280 6 298 5" strokeWidth={1.2} opacity={0.6} vectorEffect="non-scaling-stroke" />
      </svg>
      {label ? (
        <span className="font-hand text-[20px] leading-none text-ink-2">{label}</span>
      ) : (
        <span className="flex items-center gap-1.5">
          <svg viewBox="0 0 60 16" className="h-4 w-14" fill="none" stroke="currentColor" strokeLinecap="round">
            <path d="M2 12 C14 4 26 4 40 9" strokeWidth={1.3} strokeDasharray="1 4" />
          </svg>
          <PaperPlane className="h-5 w-6 -rotate-6 text-ink-2" />
        </span>
      )}
      <svg viewBox="0 0 300 12" preserveAspectRatio="none" className="h-3 flex-1" fill="none" stroke="currentColor" strokeLinecap="round">
        <path d="M2 6 C50 8 90 4 140 6 S220 8 260 5 S290 7 298 6" strokeWidth={1.2} opacity={0.6} vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}

/** Small hand-drawn underline swash used under headings. */
export function Swash({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 12" preserveAspectRatio="none" className={cx("h-2.5 w-24", className)} fill="none" stroke="currentColor" strokeLinecap="round" aria-hidden>
      <path d="M3 8 C30 3 62 3 92 6 C102 7 110 7 117 5" strokeWidth={2.4} />
      <path d="M14 10 C40 7 70 7.5 98 9" strokeWidth={1.2} opacity={0.55} />
    </svg>
  );
}

/* ----------------------------------------------------------------- stamps */
/** Postage stamp with perforated edge around any small sketch. */
export function PostageStamp({
  children,
  value = "₹25",
  country = "INDIA",
  className,
  tint = "var(--sky)",
}: {
  children: ReactNode;
  value?: string;
  country?: string;
  className?: string;
  tint?: string;
}) {
  return (
    <div className={cx("stamp-perf bg-[#fffdf8] p-[7px] shadow-[0_1px_2px_rgba(60,40,10,0.18)]", className)} aria-hidden>
      <div className="relative flex h-full flex-col border border-ink/25 p-1.5" style={{ background: `color-mix(in oklab, ${tint} 16%, #fffdf8)` }}>
        <div className="min-h-0 flex-1">{children}</div>
        <div className="mt-1 flex items-end justify-between px-0.5 font-mono text-[9px] font-medium leading-none tracking-[0.12em] text-ink">
          <span>{country}</span>
          <span className="font-display text-[12px] tracking-normal">{value}</span>
        </div>
      </div>
    </div>
  );
}

/** Passport-style ink stamp, slightly uneven, with grainy ink coverage. */
export function InkStamp({
  text = "CONFIRMED",
  sub,
  className,
  color = "var(--terracotta)",
}: {
  text?: string;
  sub?: string;
  className?: string;
  color?: string;
}) {
  const id = useId().replace(/:/g, "");
  return (
    <svg viewBox="0 0 220 96" className={className} role="img" aria-label={text} style={{ color }}>
      <defs>
        <filter id={`ink-${id}`} x="-5%" y="-10%" width="110%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="noise" />
          <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.3 1.5" result="holes" />
          <feComposite in="SourceGraphic" in2="holes" operator="in" result="inked" />
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="2" result="warp" />
          <feDisplacementMap in="inked" in2="warp" scale="3" />
        </filter>
      </defs>
      <g filter={`url(#ink-${id})`} fill="none" stroke="currentColor">
        <rect x="5" y="5" width="210" height="86" rx="12" strokeWidth="4" />
        <rect x="13" y="13" width="194" height="70" rx="7" strokeWidth="1.6" />
        <text
          x="110"
          y={sub ? 52 : 59}
          textAnchor="middle"
          fill="currentColor"
          stroke="none"
          fontFamily="var(--font-mono)"
          fontWeight="500"
          fontSize="27"
          letterSpacing="3.5"
        >
          {text}
        </text>
        {sub ? (
          <text x="110" y="72" textAnchor="middle" fill="currentColor" stroke="none" fontFamily="var(--font-mono)" fontSize="10.5" letterSpacing="2.5">
            {sub}
          </text>
        ) : null}
        <path d="M24 24 h20 M176 24 h20 M24 72 h14 M182 72 h14" strokeWidth="1.4" />
      </g>
    </svg>
  );
}

/* ------------------------------------------------------------- India map */
// Simplified India outline (lon, lat), drawn as a smooth hand-traced line.
const OUTLINE: [number, number][] = [
  [74.4, 34.8], [76.2, 35.6], [77.8, 35.5], [79.3, 34.2], [78.8, 32.6], [79.1, 31.2], [80.3, 30.4], [81.1, 30.0],
  [82.6, 27.6], [84.2, 27.4], [86.1, 26.5], [88.0, 26.4], [88.2, 27.8], [88.9, 27.3], [89.8, 26.8], [92.0, 26.9],
  [92.1, 27.8], [94.0, 29.0], [95.5, 29.2], [96.7, 28.5], [97.3, 28.0], [96.2, 27.2], [95.2, 26.6], [94.6, 25.3],
  [94.2, 23.8], [93.4, 22.6], [92.6, 22.1], [92.2, 23.9], [91.6, 24.6], [90.0, 25.2], [89.0, 25.4], [88.6, 24.3],
  [89.0, 22.2], [87.2, 21.5], [86.5, 20.1], [84.8, 19.2], [83.3, 17.7], [82.3, 16.6], [81.2, 15.9], [80.2, 15.2],
  [80.3, 13.4], [79.9, 11.7], [79.8, 10.3], [78.9, 9.3], [78.1, 8.5], [77.5, 8.1], [76.6, 8.9], [76.2, 10.2],
  [75.7, 11.6], [74.8, 12.9], [74.4, 14.5], [73.7, 15.8], [73.2, 17.5], [72.8, 19.0], [72.9, 20.8], [72.5, 21.6],
  [71.2, 20.8], [69.8, 21.5], [69.0, 22.4], [70.2, 22.9], [68.7, 23.3], [68.3, 23.8], [69.6, 24.3], [71.0, 24.5],
  [70.1, 25.6], [70.6, 27.1], [72.0, 28.4], [73.4, 29.9], [74.6, 31.0], [74.7, 32.4], [73.9, 33.3],
];

const proj = ([lon, lat]: [number, number]): [number, number] => [(lon - 67) * 12.6 + 10, (37.2 - lat) * 14.2 + 8];

function smoothPath(pts: [number, number][], closed: boolean, jitter = 0): string {
  const P = pts.map(([x, y], i) => [x + (jitter ? Math.sin(i * 12.9898) * jitter : 0), y + (jitter ? Math.cos(i * 78.233) * jitter : 0)]);
  const n = P.length;
  const get = (i: number) => (closed ? P[(i + n) % n] : P[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${P[0][0].toFixed(1)} ${P[0][1].toFixed(1)}`;
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const p0 = get(i - 1);
    const p1 = get(i);
    const p2 = get(i + 1);
    const p3 = get(i + 2);
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return closed ? d + " Z" : d;
}

const OUTLINE_PTS = OUTLINE.map(proj);
const OUTLINE_D = smoothPath(OUTLINE_PTS, true);
const OUTLINE_D2 = smoothPath(OUTLINE_PTS, true, 1.6);

export const MAP_STOPS: { name: string; at: [number, number]; dx: number; dy: number }[] = [
  { name: "Srinagar", at: [74.8, 34.1], dx: -8, dy: -8 },
  { name: "Leh", at: [77.6, 34.2], dx: 8, dy: -4 },
  { name: "Manali", at: [77.2, 32.2], dx: 9, dy: 6 },
  { name: "Jaisalmer", at: [70.9, 26.9], dx: 8, dy: -6 },
  { name: "Kutch", at: [69.7, 23.3], dx: -6, dy: 18 },
  { name: "Coorg", at: [75.8, 12.4], dx: 9, dy: 4 },
  { name: "Alleppey", at: [76.3, 9.5], dx: 9, dy: 8 },
];
const ROUTE_PTS = MAP_STOPS.map((s) => proj(s.at));
const ROUTE_D = (() => {
  // Gentle arcs between stops so the route reads as a hand-drawn journey.
  const [first, ...rest] = ROUTE_PTS;
  let d = `M${first[0].toFixed(1)} ${first[1].toFixed(1)}`;
  let prev = first;
  rest.forEach((p, i) => {
    const mx = (prev[0] + p[0]) / 2;
    const my = (prev[1] + p[1]) / 2;
    const dx = p[0] - prev[0];
    const dy = p[1] - prev[1];
    const bend = (i % 2 ? 0.22 : -0.22);
    d += ` Q${(mx - dy * bend).toFixed(1)} ${(my + dx * bend).toFixed(1)} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
    prev = p;
  });
  return d;
})();

export function IndiaMap({ className, animate = true }: { className?: string; animate?: boolean }) {
  const id = useId().replace(/:/g, "");
  const end = ROUTE_PTS[ROUTE_PTS.length - 1];
  return (
    <svg viewBox="0 0 410 440" className={className} fill="none" strokeLinecap="round" strokeLinejoin="round" role="img" aria-label="Hand-drawn map of India with a dotted route from Srinagar to Alleppey">
      <defs>
        <mask id={`route-${id}`}>
          <motion.path
            d={ROUTE_D}
            stroke="#fff"
            strokeWidth={10}
            initial={{ pathLength: animate ? 0 : 1 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 3.2, delay: 0.6, ease: [0.45, 0, 0.2, 1] }}
          />
        </mask>
      </defs>
      <g filter="url(#wander-rough)">
        <path d={OUTLINE_D} fill="var(--mustard)" fillOpacity={0.13} stroke="none" />
        <path d={OUTLINE_D} stroke={ink} strokeWidth={1.7} />
        <path d={OUTLINE_D2} stroke={ink} strokeWidth={0.8} opacity={0.4} />
      </g>
      {/* sea hatching */}
      <g stroke="var(--teal)" strokeWidth={1} opacity={0.45}>
        <path d="M70 300 q8 -3 16 0 t16 0 M60 320 q8 -3 16 0 t16 0 M312 300 q8 -3 16 0 t16 0 M300 320 q8 -3 16 0 M150 420 q8 -3 16 0 t16 0 M250 420 q8 -3 16 0" />
      </g>
      <text x="64" y="350" fontFamily="var(--font-hand)" fontSize="17" fill="var(--teal)" opacity={0.8}>Arabian Sea</text>
      <text x="246" y="372" fontFamily="var(--font-hand)" fontSize="17" fill="var(--teal)" opacity={0.8}>Bay of Bengal</text>
      {/* route */}
      <path d={ROUTE_D} stroke="var(--terracotta)" strokeWidth={2.4} strokeDasharray="0.1 7.5" mask={`url(#route-${id})`} />
      {MAP_STOPS.map((s, i) => {
        const [x, y] = proj(s.at);
        return (
          <motion.g
            key={s.name}
            initial={animate ? { opacity: 0, scale: 0.4 } : false}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7 + i * 0.42, duration: 0.4 }}
            style={{ originX: `${x}px`, originY: `${y}px`, transformBox: "view-box" }}
          >
            <circle cx={x} cy={y} r={4.6} fill="var(--surface)" stroke={ink} strokeWidth={1.5} />
            <circle cx={x} cy={y} r={1.7} fill="var(--terracotta)" />
            <text
              x={x + s.dx}
              y={y + s.dy}
              textAnchor={s.dx < 0 ? "end" : "start"}
              fontFamily="var(--font-hand)"
              fontSize="19"
              fontWeight="600"
              fill={ink}
            >
              {s.name}
            </text>
          </motion.g>
        );
      })}
      <motion.g
        initial={animate ? { opacity: 0, x: -14, y: -10 } : false}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ delay: 3.5, duration: 0.7, ease: "easeOut" }}
      >
        <g transform={`translate(${end[0] + 14} ${end[1] + 6}) rotate(38)`}>
          <path d="M0 9 L26 0 L18 20 L12.5 13 Z" fill="var(--surface)" stroke={ink} strokeWidth={1.4} />
          <path d="M12.5 13 L26 0 M12.5 13 L11.5 18.5 L15 16" stroke={ink} strokeWidth={1.4} />
        </g>
      </motion.g>
    </svg>
  );
}

/* --------------------------------------------------------------- loaders */
/** A little landscape that keeps drawing itself — used while the concierge works. */
export function SketchLoader({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 240 110"
      className={cx("draw-loop text-ink", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path pathLength={1} d="M6 92 L48 44 L66 62 L100 22 L132 60 L150 46 L196 94" />
      <path pathLength={1} d="M90 36 l10 -14 l9 12" style={{ animationDelay: "0.3s" }} />
      <path pathLength={1} d="M4 96 C50 92 100 99 150 95 S220 92 236 96" style={{ animationDelay: "0.5s" }} />
      <path pathLength={1} d="M176 30 m-11 0 a11 11 0 1 0 22 0 a11 11 0 1 0 -22 0" stroke="var(--mustard)" style={{ animationDelay: "0.2s" }} />
      <path pathLength={1} d="M30 30 C70 10 120 14 160 34" stroke="var(--terracotta)" style={{ animationDelay: "0.7s" }} />
      <path pathLength={1} d="M200 96 V80 M200 66 L193 81 L207 81 Z" style={{ animationDelay: "0.9s" }} />
    </svg>
  );
}

/** Which vignette belongs to which destination tile. */
export const DESTINATION_SKETCHES = [MountainTreehouse, Houseboat, DesertCamp, LadakhCamp, CoffeeEstate, SpitiVillage];
export const DESTINATION_TINTS = ["var(--sage)", "var(--teal)", "var(--mustard)", "var(--sky)", "var(--sage)", "var(--terracotta)"];
