# genui

**Generative UI for Python agents.** Your Python backend streams [OpenUI Lang](https://www.openui.com/docs/openui-lang/overview); your React app renders it as live cards, tables, forms and charts with OpenUI's open-source renderer.

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

```jsx
// React
import { AgentInterface, agUIAdapter, fetchLLM } from "@openuidev/react-ui";
import { openuiLibrary } from "@openuidev/react-ui/genui-lib";

const llm = fetchLLM({ url: "/api/chat", streamAdapter: agUIAdapter() });
<AgentInterface llm={llm} componentLibrary={openuiLibrary} />;
```

A full working app is in [`examples/fastapi-react`](examples/fastapi-react).

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

## License

MIT. The OpenUI spec and fixtures in `spec/` are © Thesys, MIT — see `spec/NOTICE.md`.
