import { Link } from "react-router";
import { LINKS } from "../lib/links";
import { useTitle } from "../lib/useTitle";

export default function Wander() {
  useTitle("Wander");
  return (
    <div className="mx-auto max-w-4xl px-5 pb-10 pt-12 sm:px-8 sm:pt-20">
      <p className="text-sm font-medium text-dim">Coming soon</p>
      <h1 className="mt-3 text-balance text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">Wander: AI booking concierge demo</h1>
      <p className="mt-4 max-w-xl text-pretty text-[17px] leading-relaxed text-muted">
        A full app on genui. A Python agent searches, compares and books trips, and answers with itineraries, date pickers and checkout forms.
      </p>

      <div className="mt-10 overflow-hidden rounded-2xl border border-line bg-ink-2" data-slot="wander-screenshot">
        <div className="relative grid aspect-[16/10] place-items-center sm:aspect-[16/9]">
          <div aria-hidden className="absolute inset-0 grid grid-cols-[1fr_2fr] gap-4 p-6 opacity-50 sm:p-10">
            <div className="space-y-3">
              <div className="h-3 w-3/4 rounded bg-white/[0.07]" />
              <div className="h-3 w-1/2 rounded bg-white/[0.07]" />
              <div className="mt-6 h-14 rounded-xl bg-white/[0.04]" />
              <div className="h-14 rounded-xl bg-white/[0.04]" />
            </div>
            <div className="space-y-3">
              <div className="h-20 rounded-xl bg-white/[0.05]" />
              <div className="grid grid-cols-3 gap-3">
                <div className="h-16 rounded-xl bg-white/[0.04]" />
                <div className="h-16 rounded-xl bg-white/[0.04]" />
                <div className="h-16 rounded-xl bg-white/[0.04]" />
              </div>
              <div className="h-9 w-1/3 rounded-lg bg-white/[0.07]" />
            </div>
          </div>
          <p className="relative rounded-full border border-line-strong bg-ink px-4 py-2 text-sm text-muted">Screenshot coming soon</p>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to="/gallery?example=travel-booking"
          className="inline-flex h-11 items-center rounded-xl bg-fg px-5 text-sm font-semibold text-ink transition hover:bg-white"
        >
          See the travel booking replay
        </Link>
        <a
          href={LINKS.github}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-11 items-center rounded-xl border border-line-strong px-5 text-sm font-semibold text-fg transition hover:bg-white/[0.04]"
        >
          Follow on GitHub
        </a>
      </div>
    </div>
  );
}
