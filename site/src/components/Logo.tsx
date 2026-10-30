export function LogoMark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 512 512" className={className} aria-hidden>
      <defs>
        <linearGradient id="lm-g" x1="80" y1="60" x2="440" y2="460" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#22D3EE" />
          <stop offset=".55" stopColor="#8B5CF6" />
          <stop offset="1" stopColor="#F472B6" />
        </linearGradient>
        <linearGradient id="lm-bg" x1="0" y1="0" x2="0" y2="512" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#14141F" />
          <stop offset="1" stopColor="#0A0A12" />
        </linearGradient>
        <radialGradient id="lm-glow" cx="300" cy="230" r="260" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#8B5CF6" stopOpacity=".35" />
          <stop offset="1" stopColor="#8B5CF6" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="512" height="512" rx="116" fill="url(#lm-bg)" />
      <rect width="512" height="512" rx="116" fill="url(#lm-glow)" />
      <path
        d="M132 112h232a52 52 0 0 1 52 52v164a52 52 0 0 1-52 52H214l-64 52v-52h-18a52 52 0 0 1-52-52V164a52 52 0 0 1 52-52z"
        fill="none"
        stroke="url(#lm-g)"
        strokeWidth="22"
        strokeLinejoin="round"
      />
      <rect x="128" y="158" width="168" height="26" rx="13" fill="url(#lm-g)" />
      <rect x="128" y="204" width="112" height="92" rx="18" fill="url(#lm-g)" opacity=".9" />
      <rect x="256" y="204" width="112" height="92" rx="18" fill="url(#lm-g)" opacity=".55" />
      <rect x="128" y="314" width="96" height="24" rx="12" fill="#F4F4F8" />
      <path d="M398 52c6 30 18 42 48 48-30 6-42 18-48 48-6-30-18-42-48-48 30-6 42-18 48-48z" fill="#F4F4F8" />
    </svg>
  );
}

export function Wordmark({ size = "md" }: { size?: "md" | "xl" }) {
  if (size === "xl") {
    return (
      <span className="inline-flex items-center gap-4">
        <LogoMark className="size-14 sm:size-16 drop-shadow-[0_8px_30px_rgba(139,92,246,0.35)]" />
        <span className="text-5xl font-extrabold tracking-[-0.045em] sm:text-6xl">
          gen<span className="text-gradient">ui</span>
        </span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark className="size-7" />
      <span className="text-[1.35rem] font-extrabold tracking-[-0.04em]">
        gen<span className="text-gradient">ui</span>
      </span>
    </span>
  );
}
