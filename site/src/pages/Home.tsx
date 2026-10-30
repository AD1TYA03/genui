import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { CodeTabs, type CodeFile } from "../components/CodeTabs";
import { CopyPill } from "../components/CopyPill";
import { HeroReplay } from "../components/HeroReplay";
import { ArrowRight } from "../components/icons";
import { recordings } from "../lib/recordings";
import { useTitle } from "../lib/useTitle";

const PYTHON = `from fastapi import FastAPI, Request
from openai import AsyncOpenAI
from genui import Library
from genui.integrations.fastapi import read_run, stream_response

library = Library.from_spec("spec.json")  # exported from your React components
SYSTEM_PROMPT = library.system_prompt()
client = AsyncOpenAI()  # or Ollama / vLLM / LM Studio via OPENAI_BASE_URL
app = FastAPI()

@app.post("/api/chat")
async def chat(request: Request):
    run = await read_run(request)  # clean history, button clicks as turns
    stream = await client.chat.completions.create(
        model="gpt-5.5-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *run.messages],
        stream=True,
    )
    return stream_response(stream, run=run)  # AG-UI events over SSE`;

const REACT = `import "genui-react/styles.css";
import { GenUIChat } from "genui-react";

export default function App() {
  return (
    <div style={{ height: "100vh" }}>
      <GenUIChat url="/api/chat" agentName="My assistant" />
    </div>
  );
}`;

const RENDERER = `import "genui-react/styles.css";
import { GenUIRenderer } from "genui-react";

// Render one saved or streaming response anywhere in your app.
export function Answer({ text, streaming }: { text: string; streaming: boolean }) {
  return (
    <GenUIRenderer
      response={text}
      isStreaming={streaming}
      onAction={(e) => console.log(e.humanFriendlyMessage)}
    />
  );
}`;

const VALIDATE = `from genui import Library
from genui.lang import parse

library = Library.from_spec("spec.json")
result = parse(model_output, library.to_spec())

result.errors  # structured errors with hints to feed back to the model`;

const BACKEND_FILES: CodeFile[] = [
  { name: "app.py", lang: "python", code: PYTHON },
  { name: "validate.py", lang: "python", code: VALIDATE },
];
const FRONTEND_FILES: CodeFile[] = [
  { name: "App.tsx", lang: "tsx", code: REACT },
  { name: "Answer.tsx", lang: "tsx", code: RENDERER },
];

const reveal = {
  initial: { opacity: 0, y: 12 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.1 },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
};

function Section({ id, children, className = "" }: { id?: string; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28 ${className}`}>
      {children}
    </section>
  );
}

function Heading({ eyebrow, title, children }: { eyebrow: string; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-12 max-w-2xl">
      <p className="mb-3 text-sm font-medium text-dim">{eyebrow}</p>
      <h2 className="text-balance text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">{title}</h2>
      {children && <p className="mt-4 text-pretty text-[17px] leading-relaxed text-muted">{children}</p>}
    </div>
  );
}

function Hero() {
  return (
    <section className="relative">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[560px] bg-[radial-gradient(60%_50%_at_70%_0%,rgba(139,92,246,0.10),transparent_70%)]"
      />
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-12 sm:px-8 sm:pt-20 lg:grid-cols-[1fr_1fr] lg:gap-16 lg:pb-28 lg:pt-24">
        <div className="min-w-0">
          <h1 className="text-balance text-[2.6rem] font-semibold leading-[1.05] tracking-[-0.035em] sm:text-6xl">
            Generative UI for <span className="text-gradient">Python agents</span>
          </h1>
          <p className="mt-6 max-w-md text-pretty text-lg leading-relaxed text-muted">
            Stream OpenUI Lang from any Python agent. Render it as live React components.
          </p>

          <div className="mt-10 grid max-w-sm gap-3">
            <CopyPill command="pip install genui-py" />
            <CopyPill command="npm install genui-react" />
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/gallery"
              className="group inline-flex h-11 items-center gap-2 rounded-xl bg-fg px-5 text-sm font-semibold text-ink transition hover:bg-white"
            >
              See the gallery
              <ArrowRight className="transition group-hover:translate-x-0.5" />
            </Link>
            <Link
              to="/playground"
              className="inline-flex h-11 items-center rounded-xl border border-line-strong px-5 text-sm font-semibold text-fg transition hover:border-white/25 hover:bg-white/[0.04]"
            >
              Open playground
            </Link>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="min-w-0"
        >
          <HeroReplay />
        </motion.div>
      </div>
    </section>
  );
}

const STEPS = [
  {
    n: "1",
    title: "Export your components",
    body: "Your React app owns the components. One CLI command writes them to spec.json.",
    code: "openui generate --spec",
  },
  {
    n: "2",
    title: "Prompt any model",
    body: "genui builds the system prompt from spec.json. Your agent answers in OpenUI Lang.",
    code: "library.system_prompt()",
  },
  {
    n: "3",
    title: "Render while it streams",
    body: "genui streams AG-UI events over SSE. Each component appears as soon as its line lands.",
    code: "stream_response(stream)",
  },
];

function HowItWorks() {
  return (
    <Section id="how-it-works">
      <Heading eyebrow="How it works" title="One spec, shared by both sides">
        The prompt and the renderer read the same file, so they never drift apart.
      </Heading>
      <ol className="grid gap-4 md:grid-cols-3">
        {STEPS.map((s) => (
          <motion.li key={s.n} {...reveal} className="rounded-2xl border border-line p-6">
            <span className="grid size-8 place-items-center rounded-full border border-cyan-300/40 font-mono text-sm text-cyan-300">
              {s.n}
            </span>
            <h3 className="mt-6 text-lg font-semibold tracking-tight">{s.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-muted">{s.body}</p>
            <code className="mt-6 inline-block font-mono text-[12.5px] text-dim">{s.code}</code>
          </motion.li>
        ))}
      </ol>
    </Section>
  );
}

function CodeSection() {
  return (
    <Section>
      <Heading eyebrow="Quick start" title="A backend and a page">
        Swap OpenAI for Anthropic, Gemini, LangGraph or a local model. genui streams them all.
      </Heading>
      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <div className="min-w-0">
          <p className="mb-3 font-mono text-[12.5px] text-dim">pip install &quot;genui-py[fastapi,openai]&quot;</p>
          <CodeTabs files={BACKEND_FILES} />
        </div>
        <div className="min-w-0">
          <p className="mb-3 font-mono text-[12.5px] text-dim">npm install genui-react</p>
          <CodeTabs files={FRONTEND_FILES} />
        </div>
      </div>
    </Section>
  );
}

const FEATURES: { title: string; body: string; stat: string }[] = [
  { stat: "MIT", title: "Free forever", body: "No account, no API key, no paid tier." },
  { stat: "0", title: "Zero telemetry", body: "Prompting, validation and streaming run in your process." },
  { stat: "Any", title: "Any model", body: "OpenAI, Anthropic, Gemini, or local via Ollama, vLLM, LM Studio." },
  { stat: "6", title: "Stream types", body: "Text, OpenAI Chat and Responses, Anthropic, LangChain/LangGraph, genui events." },
  { stat: "59/59", title: "Conformance fixtures", body: "A spec-exact OpenUI Lang 1.0 parser in pure Python." },
  { stat: "1:1", title: "Byte-identical prompts", body: "Matches the official TypeScript prompt generator byte for byte." },
];

function Features() {
  return (
    <Section>
      <Heading eyebrow="Why genui" title="Small, local, spec-exact" />
      <dl className="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="border-t border-line pt-6">
            <dt>
              <span className="block font-mono text-2xl font-medium tracking-tight text-fg">{f.stat}</span>
              <span className="mt-3 block font-semibold">{f.title}</span>
            </dt>
            <dd className="mt-1.5 text-[15px] leading-relaxed text-muted">{f.body}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function GalleryTeaser() {
  return (
    <Section className="pt-0 sm:pt-0">
      <div className="grid items-center gap-10 rounded-2xl border border-line p-8 sm:p-12 lg:grid-cols-[1.2fr_1fr]">
        <div>
          <h2 className="text-balance text-3xl font-semibold tracking-[-0.025em]">Watch real model output become UI</h2>
          <p className="mt-4 max-w-lg text-pretty leading-relaxed text-muted">
            Six recorded agent answers, replayed through the renderer you ship. Open any of them in the playground.
          </p>
          <Link
            to="/gallery"
            className="group mt-8 inline-flex h-11 items-center gap-2 rounded-xl bg-fg px-5 text-sm font-semibold text-ink transition hover:bg-white"
          >
            Open the gallery <ArrowRight className="transition group-hover:translate-x-0.5" />
          </Link>
        </div>
        <ul className="grid grid-cols-2 gap-2">
          {recordings.map((r) => (
            <li key={r.id}>
              <Link
                to={`/gallery?example=${r.id}`}
                className="block rounded-lg px-3 py-2.5 text-sm text-muted transition hover:bg-white/[0.04] hover:text-fg"
              >
                {r.title}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}

export default function Home() {
  useTitle();
  return (
    <>
      <Hero />
      <HowItWorks />
      <CodeSection />
      <Features />
      <GalleryTeaser />
    </>
  );
}
