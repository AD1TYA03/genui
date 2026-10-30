# Changelog

## 0.1.2 — 2026-10-31

- README shows a real end-to-end run of the Wander example instead of screenshots. No code changes.

## 0.1.1 — 2026-10-31

- Streams from LangGraph (`stream_mode="messages"` tuples), the OpenAI Agents SDK and OpenAI Responses tool calls now work; LangChain tool results become tool events instead of leaking into the UI text.
- Text before and after a tool call is sent as separate message parts, so an agent's preamble can't corrupt the UI program.
- `encode_sync()` for WSGI frameworks (Flask, sync Django); `SSE_HEADERS` exported from `genui.stream`.
- `RunInput.text_messages()` and `RunInput.anthropic(system)` for APIs that reject OpenAI-only history shapes.
- New examples: Wander booking concierge (Gemini + tools + custom React components), and backends for Anthropic, Ollama, LangGraph, OpenAI Agents SDK, Pydantic AI and Flask.
- Live demo, gallery and playground: https://genui-py.vercel.app

## 0.1.0 — 2026-10-31

First release.

- `Library.from_spec()` reads the LibrarySpec your React app exports (`openui generate --spec`).
- `system_prompt()` generates the OpenUI 1.0 system prompt locally, byte-identical to the official TypeScript generator (24 golden cases plus OpenUI's own 82-component `react-ui` library).
- `genui.lang`: OpenUI Lang 1.0 parser, streaming parser, evaluator, validator and edit merge. Passes all 59 official conformance fixtures.
- Streaming to React: `stream_response()` / `encode()` turn str, OpenAI, Anthropic, OpenAI Responses or LangChain streams into AG-UI or OpenAI SSE.
- `read_run()` / `to_model_messages()`: clean chat history and button clicks for the model.
- `genui.messages`: the OpenUI stored-message protocol.
- FastAPI + React example.
