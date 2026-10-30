import { useCallback, useEffect, useRef, useState } from "react";

/** A deterministic PRNG so replays look the same every time. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Chunk {
  /** End offset into the source text. */
  end: number;
  /** Delay before this chunk lands, in ms at 1x speed. */
  delay: number;
}

/**
 * Split text the way an LLM stream arrives: token-sized pieces (2 to 14 chars),
 * a steady ~25ms cadence with jitter, and the occasional longer pause at line
 * breaks, as when a model starts a new statement.
 */
export function chunkText(text: string, seed = 7): Chunk[] {
  const rand = mulberry32(seed);
  const chunks: Chunk[] = [];
  let i = 0;
  // Time to first token.
  let first = true;
  while (i < text.length) {
    let size = 2 + Math.floor(rand() * 10);
    if (rand() < 0.12) size += Math.floor(rand() * 10);
    let end = Math.min(text.length, i + size);
    // Prefer to break after a newline if one is close.
    const nl = text.indexOf("\n", i);
    if (nl !== -1 && nl < end && nl > i) end = nl + 1;
    const piece = text.slice(i, end);
    let delay = 18 + rand() * 26;
    if (piece.endsWith("\n")) delay += rand() < 0.25 ? 60 + rand() * 90 : 10;
    if (first) {
      delay = 380;
      first = false;
    }
    chunks.push({ end, delay });
    i = end;
  }
  return chunks;
}

export interface ReplayState {
  text: string;
  /** Number of characters revealed. */
  shown: number;
  playing: boolean;
  done: boolean;
  progress: number;
  play: () => void;
  pause: () => void;
  replay: () => void;
  /** Jump straight to the finished response. */
  finish: () => void;
}

export function useReplay(
  source: string,
  { speed = 1, autoplay = true, seed = 7, loopDelay }: { speed?: number; autoplay?: boolean; seed?: number; loopDelay?: number } = {},
): ReplayState {
  const [index, setIndex] = useState(0); // chunks consumed
  const [playing, setPlaying] = useState(autoplay);
  const chunksRef = useRef<Chunk[]>(chunkText(source, seed));
  const speedRef = useRef(speed);
  speedRef.current = speed;

  // New source: reset.
  useEffect(() => {
    chunksRef.current = chunkText(source, seed);
    setIndex(0);
    setPlaying(autoplay);
  }, [source, seed, autoplay]);

  const total = chunksRef.current.length;
  const done = index >= total;

  useEffect(() => {
    if (!playing) return;
    if (done) {
      if (loopDelay == null) {
        setPlaying(false);
        return;
      }
      const t = window.setTimeout(() => setIndex(0), loopDelay);
      return () => window.clearTimeout(t);
    }
    const chunk = chunksRef.current[index];
    const t = window.setTimeout(() => setIndex((n) => n + 1), chunk.delay / speedRef.current);
    return () => window.clearTimeout(t);
  }, [playing, index, done, loopDelay]);

  const shown = index === 0 ? 0 : chunksRef.current[Math.min(index, total) - 1].end;

  const play = useCallback(() => {
    setIndex((n) => (n >= chunksRef.current.length ? 0 : n));
    setPlaying(true);
  }, []);
  const pause = useCallback(() => setPlaying(false), []);
  const replay = useCallback(() => {
    setIndex(0);
    setPlaying(true);
  }, []);
  const finish = useCallback(() => {
    setIndex(chunksRef.current.length);
    setPlaying(false);
  }, []);

  return {
    text: source.slice(0, shown),
    shown,
    playing: playing && !done,
    done,
    progress: total ? Math.min(1, index / total) : 1,
    play,
    pause,
    replay,
    finish,
  };
}
