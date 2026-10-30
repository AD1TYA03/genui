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
  <a href="https://genui-py.vercel.app"><b>Live demo &amp; playground</b></a> ·
  <a href="https://genui-py.vercel.app/gallery">Gallery</a> ·
  <a href="https://pypi.org/project/genui-py/">PyPI</a> ·
  <a href="https://www.npmjs.com/package/genui-react">npm</a>
</p>

<p align="center"><img alt="A UI streaming in token by token" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/demo.gif" width="760"></p>

## See it in action: Wander

[`examples/wander`](examples/wander) is a full booking concierge built with genui: a Python agent on Gemini with real tools (search, availability, booking) and a React app with custom components (polaroid stay cards, a range calendar, a receipt, a boarding-pass ticket). The agent answers only in OpenUI Lang; genui handles the prompt, the tool events, the streaming and the button clicks.

<p align="center">
  <img alt="Wander home" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/screenshots/wander-home.jpg" width="49%">
  <img alt="Wander booking flow" src="https://raw.githubusercontent.com/AD1TYA03/genui/main/assets/screenshots/wander-booking.jpg" width="49%">
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

## Validate model output

```python
from genui.lang import parse

result = parse(text, library.to_spec())
result.errors      # structured errors with hints you can feed back to the model
```

## Message protocol

`genui.messages` reads and writes OpenUI's stored-message format (`]]>openui:content` marker lines), turns button clicks into model-ready turns, and strips markers before anything reaches the model.

## Status

Alpha. API may change before 1.0. Roadmap: framework adapters (LangGraph, OpenAI Agents SDK, Pydantic AI), local auto-fix loop, Markdown → UI "beautify" mode.

## Brand

Logo files are in [`assets/`](assets): `logo.svg` (icon), `logo-wordmark-{light,dark}.svg`, PNG sizes, and `social-preview.png` (1280×640) for the GitHub repo card.

## License

MIT. The OpenUI spec and fixtures in `spec/` are © Thesys, MIT — see `spec/NOTICE.md`.
