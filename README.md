<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/logo-wordmark-dark.svg">
    <img alt="genui" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/logo-wordmark-light.svg" width="460">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/genui-py/"><img alt="PyPI" src="https://img.shields.io/pypi/v/genui-py?color=8B5CF6"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-22D3EE">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-F472B6">
  <img alt="Telemetry" src="https://img.shields.io/badge/telemetry-none-0A0A12">
</p>

**Generative UI for Python agents.** Your Python backend streams [OpenUI Lang](https://www.openui.com/docs/openui-lang/overview); your React app renders it as live cards, tables, forms and charts with OpenUI's open-source renderer.

<p align="center">
  <a href="https://genui-py.vercel.app"><b>Live demo</b></a> ·
  <a href="https://pypi.org/project/genui-py/">PyPI</a> ·
  <a href="https://www.npmjs.com/package/genui-react">npm</a>
</p>

## See it in action: Wander

[`examples/wander`](examples/wander) is a full booking concierge built with genui: a Python agent on Gemini with real tools (search, availability, booking) and a React app with custom components (polaroid stay cards, a range calendar, a receipt, a boarding-pass ticket). The agent answers only in OpenUI Lang; genui handles the prompt, the tool events, the streaming and the button clicks.

<p align="center">
  <a href="https://genui-py.vercel.app/wander"><img alt="Wander: booking a treehouse end to end with a Gemini agent" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/wander.gif" width="820"></a>
  <br><sub>A real run: Gemini agent → genui → React. <a href="https://genui-py.vercel.app/wander">Watch the full-quality video</a>.</sub>
</p>

- **Free, MIT.** `pip install genui-py`. No account, no API key, no paid tier.
- **Your data stays with you.** Prompt generation, validation and streaming run in your process. Zero telemetry, zero network calls.
- **Any model.** OpenAI, Anthropic, Gemini, or local models through any OpenAI-compatible server (Ollama, vLLM, LM Studio).
- **Any agent.** Plain Python, LangGraph, OpenAI Agents SDK, Pydantic AI, CrewAI — if it yields text, genui can stream it.
- **Spec-exact.** Implements the OpenUI 1.0 spec and runs the official conformance fixtures in CI.

> genui is a community project. It is not affiliated with or endorsed by Thesys, the authors of OpenUI.

## How it fits

```
React (OpenUI renderer)                Python (your agent + genui)
───────────────────────                ───────────────────────────
components (Zod + React)  ──spec.json──▶  Library.from_spec()
                                           library.system_prompt()  → your LLM
<AgentInterface agUIAdapter()> ◀──SSE──  stream_response(llm_stream)
button click @ToAssistant  ──POST────▶  read_run(): clean history for the model
```

The frontend owns the components. `npx @openuidev/cli generate src/library.ts --spec --out spec.json` exports them, and genui reads that file, so the prompt and the renderer can never drift apart.

## Quick start (FastAPI)

```bash
pip install "genui-py[fastapi,openai]"
```

```python
from fastapi import FastAPI, Request
from openai import AsyncOpenAI
from genui import Library
from genui.integrations.fastapi import read_run, stream_response

library = Library.from_spec("spec.json")
SYSTEM_PROMPT = library.system_prompt()
client = AsyncOpenAI()
app = FastAPI()

@app.post("/api/chat")
async def chat(request: Request):
    run = await read_run(request)
    stream = await client.chat.completions.create(
        model="gpt-5.5-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *run.messages],
        stream=True,
    )
    return stream_response(stream, run=run)
```

```bash
npm install genui-react
```

```jsx
// React
import { GenUIChat } from "genui-react";
import "genui-react/styles.css";

<GenUIChat url="/api/chat" />;
```

Prefer composing OpenUI's components yourself? `genuiLLM({ url })` returns the client for `AgentInterface`, and `GenUIRenderer` renders a single stored response.

**Rendering your own components?** Import from `genui-react/core`. It has the renderer, transport and storage without OpenUI's default component library: about **210 KB gzipped with React**, against ~970 KB for the full chat.

A full working app is in [`examples/fastapi-react`](examples/fastapi-react). Backend examples for Anthropic, Ollama (fully local), LangGraph, OpenAI Agents SDK, Pydantic AI and Flask are in [`examples/backends`](examples/backends).

## What you can stream

`stream_response()` (and `genui.stream.encode()` for other frameworks) accepts sync or async iterables of:

| item | example |
| --- | --- |
| `str` | `yield 'root = Card([title])'` from any agent |
| OpenAI Chat Completions chunks | `await client.chat.completions.create(..., stream=True)` |
| OpenAI Responses events | `client.responses.create(..., stream=True)` |
| Anthropic Messages events | `client.messages.create(..., stream=True)` |
| LangChain / LangGraph message chunks | `graph.astream(..., stream_mode="messages")` |
| genui events | `ToolCallStart`, `ToolCallArgs`, `ToolResult`, `StreamError`, … |

Output formats: `"ag-ui"` (default, for `agUIAdapter()`) or `"openai"` (for `openAIAdapter()`). Exceptions inside your agent become a `RUN_ERROR` the UI can show.

## Validate and auto-fix model output

`autofix()` checks the program when the reply ends. If it has errors (an unknown component, a missing prop, no root), it asks the model again with the structured error list. The corrected program replaces the broken one in the same message, so the UI updates in place.

```python
from genui import autofix

async def call_model(fix):  # [] first, then the correction turns
    return await client.chat.completions.create(
        model=MODEL, messages=[system, *run.messages, *fix], stream=True)

return stream_response(autofix(call_model, library), run=run)
```

`max_retries=1` by default. `buffer=True` holds the program back until it validates, so users never see a broken UI (they see nothing until it's ready). To check a program yourself:

```python
from genui.lang import parse

result = parse(text, library.to_spec())
result.errors      # structured errors with hints you can feed back to the model
```

`StreamParser` gives you snapshots while the reply streams. It re-reads only new text and reuses the statements it has already finished.

## Server-side history

For agents that take actions, don't trust the history the browser sends. `genui.threads` keeps each conversation on your server: only the new user turn is read from the request, and the reply is stored when the stream finishes.

```python
from genui.threads import MemoryThreadStore, history, record

store = MemoryThreadStore()          # or Redis / Postgres: examples/threads

@app.post("/api/chat")
async def chat(request: Request, user=Depends(current_user)):
    run = await read_run(request)
    key = f"{user.id}:{run.thread_id}"         # scope threads to the signed-in user
    messages = await history(store, key, run)
    stream = await client.chat.completions.create(model=MODEL, messages=[system, *messages], stream=True)
    return stream_response(record(store, key, run, stream, include_tools=True), run=run)
```

`include_tools=True` also stores the tool calls your server ran and their results, so later turns know what was done. A turn that fails is not stored. Ready-made Redis and Postgres stores and a full app are in [`examples/threads`](examples/threads).

## Token costs

Each component adds ~55 tokens to the system prompt, and the OpenUI Lang rules cost ~500–1,100. A UI program is ~150–700 tokens, about 20–45% fewer than the same UI as JSON. A full Wander booking costs ~$0.025 on Gemini 3 Flash. [`docs/saving-tokens.md`](docs/saving-tokens.md) explains how to estimate your app and how to cut cost: prompt caching, compacting old UI programs in history, smaller per-agent libraries.

## Message protocol

`genui.messages` reads and writes OpenUI's stored-message format (`]]>openui:content` marker lines), turns button clicks into model-ready turns, and strips markers before anything reaches the model.

## Security

The chat history in each request comes from the browser, so genui treats it as untrusted:

- **Only `user` and `assistant` turns reach your model.** `read_run()` drops `system`, `developer` and `tool` turns and client-sent `toolCalls`, so a user can't inject a system prompt or fake a tool result. Opt in with `read_run(request, roles=(...), tool_calls=True)` only if you verify those turns against server-side history.
- **Request limits.** `read_run()` rejects bodies over 2 MB (HTTP 413) and keeps the newest 200 messages / 500,000 characters. Change these with `max_bytes`, `max_messages` and `max_chars`.
- **Never pass `run.tools` or unchecked `run.extra` fields** (such as a model name) to your LLM. Check them against an allowlist.
- **Errors stay on the server.** An exception in your agent is logged (logger `genui`) and the browser sees a generic `RUN_ERROR`. Use `stream_response(..., expose_errors=True)` in development, or yield `StreamError("...")` for a message you want users to see.
- **Bounded parsing.** `genui.lang.parse()` stops with a `parse-exception` once a program expands past 200,000 values, so a short program that keeps doubling its references can't hang your server.
- **Frontend.** `GenUIChat` opens `@OpenUrl` links only for `http(s)`, `mailto`, `tel` and relative URLs, always with `noopener`. History in `localStorage` is plain text: call `clearChatHistory()` on logout, or use `storageKey={false}` or server storage for sensitive data. **Dependency advisories.** OpenUI's dependencies pull in an old `katex` (GHSA-238p-pmpm-9mq7). Fix it with an npm override in your app's `package.json` (overrides only apply in apps, not libraries):

  ```json
  "overrides": { "katex": "^0.19.1" }
  ```

  They also pull in `zod` 3.x through `@ag-ui/core` (GHSA-mrhx-c7xc-m3w5, memory exhaustion on oversized input). Here zod only validates the SSE events your own backend sends, so exploiting it needs control of your server's stream. Don't override it to zod 4: the app still runs, but `@ag-ui/core`'s types turn into `unknown`. The fix has to come from an OpenUI release on `@ag-ui/core` 1.x.

## Status

Alpha. API may change before 1.0. Roadmap: Markdown → UI "beautify" mode.

## Brand

Logo files are in [`assets/`](assets): `logo.svg` (icon), `logo-wordmark-{light,dark}.svg`, PNG sizes, and `social-preview.png` (1280×640) for the GitHub repo card.

## License

MIT. The OpenUI spec and fixtures in `spec/` are © Thesys, MIT — see `spec/NOTICE.md`.
