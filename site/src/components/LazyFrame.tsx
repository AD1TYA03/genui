import { lazy, Suspense } from "react";
import type { GenUIFrameProps } from "./GenUIFrame";

const GenUIFrame = lazy(() => import("./GenUIFrame"));

export function FrameSkeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      <div className="h-6 w-2/3 animate-pulse rounded-md bg-white/[0.06]" />
      <div className="h-24 animate-pulse rounded-xl bg-white/[0.04]" />
      <div className="h-24 animate-pulse rounded-xl bg-white/[0.04]" />
    </div>
  );
}

export function LazyFrame(props: GenUIFrameProps) {
  return (
    <Suspense fallback={<FrameSkeleton />}>
      <GenUIFrame {...props} />
    </Suspense>
  );
}
