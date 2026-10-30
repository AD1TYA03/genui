# Backend examples

Copy-paste backends for genui. Each one is a single file under 60 lines that:

1. loads the component library from `../fastapi-react/backend/spec.json`,
2. sends `library.system_prompt()` to the model,
3. reads the chat history the UI posts with `read_run()` / `parse_run_input()`,
4. streams the answer back as AG-UI events for OpenUI's React renderer.

| File | Stack | Model | Tool calls in the UI |
| --- | --- | --- | --- |
| [`anthropic_app.py`](anthropic_app.py) | FastAPI + Anthropic Messages API | Claude | n/a |
| [`ollama_app.py`](ollama_app.py) | FastAPI + Ollama (OpenAI-compatible endpoint) | any local model. No cloud, no key | n/a |
| [`langgraph_app.py`](langgraph_app.py) | FastAPI + LangGraph agent (`langchain.agents.create_agent`) | any LangChain chat model | yes |
| [`openai_agents_app.py`](openai_agents_app.py) | FastAPI + OpenAI Agents SDK (`Runner.run_streamed`) | OpenAI | yes |
| [`pydantic_ai_app.py`](pydantic_ai_app.py) | FastAPI + Pydantic AI (`agent.run_stream`) | any Pydantic AI model | n/a |
| [`flask_app.py`](flask_app.py) | Flask (WSGI) + `genui.stream.encode()` | OpenAI or any compatible server | n/a |

## Install

Run from this folder. Each command installs what one example needs:

```bash
pip install "genui-py[fastapi]" anthropic uvicorn                          # anthropic_app.py
pip install "genui-py[fastapi,openai]" uvicorn                             # ollama_app.py
pip install "genui-py[fastapi]" langchain langgraph langchain-openai uvicorn  # langgraph_app.py
pip install "genui-py[fastapi]" openai-agents uvicorn                      # openai_agents_app.py
pip install "genui-py[fastapi]" "pydantic-ai-slim[openai]" uvicorn         # pydantic_ai_app.py
pip install genui-py flask openai                                          # flask_app.py
```

## Run with the React frontend

The frontend in [`../fastapi-react/frontend`](../fastapi-react/frontend) already proxies `/api` to
`http://localhost:8000` (see its `vite.config.js`), so start any backend on port 8000:

```bash
# terminal 1: the frontend. `npm run dev` also writes ../fastapi-react/backend/spec.json
cd examples/fastapi-react/frontend
npm install
npm run dev                     # http://localhost:5173

# terminal 2: pick one backend
cd examples/backends
ANTHROPIC_API_KEY=... uvicorn anthropic_app:app --reload --port 8000
uvicorn ollama_app:app --reload --port 8000              # needs `ollama serve` and `ollama pull qwen3`
OPENAI_API_KEY=...    uvicorn langgraph_app:app --reload --port 8000
OPENAI_API_KEY=...    uvicorn openai_agents_app:app --reload --port 8000
OPENAI_API_KEY=...    uvicorn pydantic_ai_app:app --reload --port 8000
OPENAI_API_KEY=...    flask --app flask_app run --port 8000
```

Start the frontend once before running a backend, because the backends read `spec.json` and
`npm run dev` generates it from `src/library.ts`. Every example reads a `MODEL` environment
variable, for example `MODEL=llama3.3`, `MODEL=anthropic:claude-opus-5-5` (LangGraph and Pydantic AI),
or `MODEL=claude-sonnet-5-5`.

## Notes

- **Tool calls.** `langgraph_app.py` and `openai_agents_app.py` each include a small `to_genui()`
  generator. It turns the framework's tool-call and tool-result events into genui's `ToolCallStart`
  / `ToolCallArgs` / `ToolCallEnd` / `ToolResult` events, which the UI receives as `TOOL_CALL_*`.
  Text passes straight through. Without this step, LangGraph's `(chunk, metadata)` tuples and the
  Agents SDK's wrapper events would fail to stream, and LangGraph tool output would be mixed into
  the UI text.
- **Other frameworks.** `genui.stream.encode()` is an async generator. `flask_app.py` shows how
  to run it from a sync (WSGI) server on a private event loop. The same `iter_sync()` helper
  works with Django's `StreamingHttpResponse`.
- **Local models.** `ollama_app.py` works unchanged with vLLM, LM Studio and the llama.cpp server.
  Point `OLLAMA_URL` at their `/v1` endpoint.
