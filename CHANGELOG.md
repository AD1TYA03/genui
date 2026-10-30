# Changelog

## 0.1.0 — 2026-10-31

First release.

- `Library.from_spec()` reads the LibrarySpec your React app exports (`openui generate --spec`).
- `system_prompt()` generates the OpenUI 1.0 system prompt locally, byte-identical to the official TypeScript generator (24 golden cases plus OpenUI's own 82-component `react-ui` library).
- `genui.lang`: OpenUI Lang 1.0 parser, streaming parser, evaluator, validator and edit merge. Passes all 59 official conformance fixtures.
- Streaming to React: `stream_response()` / `encode()` turn str, OpenAI, Anthropic, OpenAI Responses or LangChain streams into AG-UI or OpenAI SSE.
- `read_run()` / `to_model_messages()`: clean chat history and button clicks for the model.
- `genui.messages`: the OpenUI stored-message protocol.
- FastAPI + React example.
