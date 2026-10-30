import { CodeTabs, type CodeFile } from "../components/CodeTabs";
import { ArrowRight, GithubIcon } from "../components/icons";
import { InViewVideo } from "../components/InViewVideo";
import { LINKS } from "../lib/links";
import { useTitle } from "../lib/useTitle";

const FLOW = [
  { title: "Ask", body: "Pick a suggestion or describe a mood. Wander takes it from there.", img: "/wander/flow-1.webp" },
  { title: "Stays", body: "The agent calls search_stays and answers with custom stay cards.", img: "/wander/flow-2.webp" },
  { title: "Dates & guests", body: "A two-month calendar with blocked dates and a guest picker.", img: "/wander/flow-3.webp" },
  { title: "Price", body: "check_availability returns real lines: nights, cleaning, GST.", img: "/wander/flow-4.webp" },
  { title: "Ticket", body: "create_booking confirms, and the UI prints a boarding-pass ticket.", img: "/wander/flow-5.webp" },
];

const STACK = [
  { name: "FastAPI", role: "POST /api/chat, AG-UI over SSE" },
  { name: "genui-py", role: "Prompt from spec.json, streaming, validation" },
  { name: "Gemini", role: "Tool-calling model via the OpenAI-compatible API" },
  { name: "React", role: "14 custom components, defined with Zod" },
  { name: "genui-react", role: "Renders the stream as it arrives" },
];

const RUN: CodeFile[] = [
  {
    name: "terminal",
    lang: "bash",
    code: `git clone https://github.com/AD1TYA03/genui
cd genui/examples/wander

# 1. Frontend: install and export the component spec
cd frontend
OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 npm install
npm run generate          # writes ../backend/spec.json

# 2. Backend (new terminal): Gemini key, then the API on :8000
cd ../backend
export GEMINI_API_KEY=...
uv run uvicorn app:app --reload --port 8000

# 3. Frontend dev server on :5173
cd ../frontend && npm run dev`,
  },
];

const WANDER_CODE = `${LINKS.github}/tree/main/examples/wander`;

export default function Wander() {
  useTitle("Wander");

  return (
    <div className="mx-auto max-w-6xl px-5 pb-10 pt-12 sm:px-8 sm:pt-20">
      {/* Intro */}
      <header className="max-w-2xl">
        <p className="text-sm font-medium text-dim">Showcase</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.03em] sm:text-5xl">Wander</h1>
        <p className="mt-4 text-pretty text-[17px] leading-relaxed text-muted">
          A booking concierge built with genui: a Python agent on Gemini, real tools, and custom React components.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a
            href={WANDER_CODE}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-11 items-center gap-2 rounded-xl bg-fg px-5 text-sm font-semibold text-ink transition hover:bg-white"
          >
            <GithubIcon /> View the code
          </a>
          <a
            href="#run"
            className="inline-flex h-11 items-center rounded-xl border border-line-strong px-5 text-sm font-semibold text-fg transition hover:border-white/25 hover:bg-white/[0.04]"
          >
            Run it locally
          </a>
        </div>
      </header>

      {/* Recording */}
      <section className="mt-14" aria-label="Screen recording">
        <figure>
          <div className="overflow-hidden rounded-2xl border border-line bg-ink-2 shadow-[0_40px_100px_-50px_rgba(0,0,0,0.9)]">
            <div className="flex items-center gap-3 border-b border-line px-4 py-2.5">
              <div className="flex gap-1.5" aria-hidden>
                <span className="size-2.5 rounded-full bg-white/10" />
                <span className="size-2.5 rounded-full bg-white/10" />
                <span className="size-2.5 rounded-full bg-white/10" />
              </div>
              <span className="mx-auto rounded-md bg-white/[0.04] px-3 py-0.5 font-mono text-[11px] text-dim">localhost:5173</span>
              <span className="w-12" aria-hidden />
            </div>
            <InViewVideo
              webm="/wander/wander.webm"
              mp4="/wander/wander.mp4"
              poster="/wander/wander-poster.jpg"
              width={1440}
              height={780}
              label="Screen recording of Wander: asking for a romantic getaway, browsing treehouse stays, picking dates and guests, checking the price and confirming a booking"
              className="bg-[#f3ece0]"
            />
          </div>
          <figcaption className="mt-3 text-sm text-dim">A real run: Gemini agent → genui-py → React</figcaption>
        </figure>
      </section>

      {/* Flow */}
      <section className="mt-24" aria-labelledby="flow-title">
        <h2 id="flow-title" className="text-3xl font-semibold tracking-[-0.025em]">
          One conversation, five screens
        </h2>
        <p className="mt-3 max-w-xl text-pretty text-muted">Stills from the recording above. Each screen is OpenUI Lang from the agent, rendered by Wander&rsquo;s own components.</p>
        <ol className="scrollbar-thin -mx-5 mt-8 flex snap-x snap-mandatory gap-4 overflow-x-auto px-5 pb-4 sm:-mx-8 sm:px-8">
          {FLOW.map((f, i) => (
            <li key={f.title} className="w-[280px] shrink-0 snap-start sm:w-[320px]">
              <div className="overflow-hidden rounded-xl border border-line bg-[#f3ece0] transition hover:border-line-strong">
                <img src={f.img} alt={`Step ${i + 1}: ${f.title}`} loading="lazy" decoding="async" width={800} className="aspect-[4/3] w-full object-cover object-top" />
              </div>
              <div className="mt-4 flex items-baseline gap-2.5">
                <span className="font-mono text-xs text-cyan-300">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="font-semibold">{f.title}</h3>
                {i < FLOW.length - 1 && <ArrowRight className="ml-auto size-3.5 text-dim" aria-hidden />}
              </div>
              <p className="mt-1.5 text-[14.5px] leading-relaxed text-muted">{f.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Stack */}
      <section className="mt-24" aria-labelledby="stack-title">
        <h2 id="stack-title" className="text-3xl font-semibold tracking-[-0.025em]">
          The stack
        </h2>
        <ul className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-5">
          {STACK.map((s) => (
            <li key={s.name} className="bg-ink-2 p-5">
              <p className="font-mono text-[15px] text-fg">{s.name}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.role}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Run */}
      <section id="run" className="mt-24 scroll-mt-24" aria-labelledby="run-title">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.4fr]">
          <div>
            <h2 id="run-title" className="text-3xl font-semibold tracking-[-0.025em]">
              Run it locally
            </h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted">
              You need Node 18+, <a className="text-fg underline decoration-white/20 underline-offset-4 hover:decoration-white/60" href="https://docs.astral.sh/uv/" target="_blank" rel="noreferrer">uv</a> and a
              Gemini API key. The tools use deterministic mock data, so bookings are safe to try.
            </p>
            <ul className="mt-6 space-y-2 text-sm text-muted">
              <li>
                <a className="text-fg hover:underline" href={WANDER_CODE} target="_blank" rel="noreferrer">examples/wander</a> · source
              </li>
              <li>
                <a className="text-fg hover:underline" href={`${LINKS.github}/blob/main/examples/wander/CONTRACT.md`} target="_blank" rel="noreferrer">CONTRACT.md</a> · components and tools
              </li>
              <li>
                <a className="text-fg hover:underline" href={`${WANDER_CODE}/backend`} target="_blank" rel="noreferrer">backend/</a> · agent loop and tests
              </li>
            </ul>
          </div>
          <CodeTabs files={RUN} />
        </div>
      </section>
    </div>
  );
}
