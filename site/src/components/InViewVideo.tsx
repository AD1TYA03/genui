import { useEffect, useRef, useState } from "react";
import { PauseIcon, PlayIcon } from "./icons";

const reduceMotion = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Muted, looping video that plays only while it is on screen.
 * Nothing downloads until it first scrolls into view; a small button lets people pause it.
 */
export function InViewVideo({
  webm,
  mp4,
  poster,
  label,
  width,
  height,
  className = "",
  eager = false,
}: {
  webm: string;
  mp4: string;
  poster: string;
  label: string;
  width: number;
  height: number;
  className?: string;
  /** Above the fold: start buffering right away. */
  eager?: boolean;
}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [paused, setPaused] = useState(true);
  const userPaused = useRef(reduceMotion());

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && !userPaused.current) {
          if (v.preload === "none") v.preload = "auto";
          v.play().catch(() => {});
        } else if (!e.isIntersecting) {
          v.pause();
        }
      },
      { threshold: 0.35 },
    );
    io.observe(v);
    return () => io.disconnect();
  }, []);

  const toggle = () => {
    const v = ref.current;
    if (!v) return;
    if (v.paused) {
      userPaused.current = false;
      v.play().catch(() => {});
    } else {
      userPaused.current = true;
      v.pause();
    }
  };

  return (
    <div className={`group relative ${className}`}>
      <video
        ref={ref}
        muted
        loop
        playsInline
        preload={eager ? "auto" : "none"}
        poster={poster}
        width={width}
        height={height}
        aria-label={label}
        onPlay={() => setPaused(false)}
        onPause={() => setPaused(true)}
        className="block h-auto w-full"
      >
        <source src={webm} type="video/webm" />
        <source src={mp4} type="video/mp4" />
      </video>
      <button
        type="button"
        onClick={toggle}
        aria-label={paused ? "Play video" : "Pause video"}
        className="absolute bottom-3 right-3 grid size-9 place-items-center rounded-full bg-black/55 text-white opacity-80 backdrop-blur transition hover:bg-black/70 hover:opacity-100 focus-visible:opacity-100"
      >
        {paused ? <PlayIcon className="size-3.5" /> : <PauseIcon className="size-3.5" />}
      </button>
    </div>
  );
}
