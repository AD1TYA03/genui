import { lazy, Suspense } from "react";
import type { GenUIFrameProps } from "./GenUIFrame";

const GenUIFrame = lazy(() => import("./GenUIFrame"));

/** Shimmering placeholder in the rough shape of a generated answer. */
export function FrameSkeleton({ label }: { label?: string }) {
  return (
    <div className="relative" role="status" aria-label={label ?? "Loading"}>
      <div className="space-y-3" aria-hidden>
        <div className="shimmer h-5 w-1/2 rounded-md" />
        <div className="shimmer h-3.5 w-3/4 rounded-md" />
        <div className="grid grid-cols-3 gap-3 pt-2">
          <div className="shimmer h-20 rounded-xl" />
          <div className="shimmer h-20 rounded-xl" />
          <div className="shimmer h-20 rounded-xl" />
        </div>
        <div className="shimmer h-28 rounded-xl" />
      </div>
      {label && <p className="mt-5 text-center text-sm text-dim">{label}</p>}
    </div>
  );
}

export function LazyFrame(props: GenUIFrameProps) {
  return (
    <Suspense fallback={<FrameSkeleton label="Loading renderer…" />}>
      <GenUIFrame {...props} />
    </Suspense>
  );
}
