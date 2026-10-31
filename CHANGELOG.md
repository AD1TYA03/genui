# Changelog

## Unreleased

**New:**

- `autofix(generate, library)`: validates the program when the reply ends and asks the model to fix its errors (spec section 6.2). The fix replaces the broken program in the same message through the regenerated-response marker (section 7.1). Options: `max_retries`, `buffer`, `check`, `feedback`. Also `errors_to_fix()`.
- `genui.threads`: server-side history. `ThreadStore` protocol, `MemoryThreadStore`, `history()` (stored turns plus the new user turn) and `record()` (stores the turn when the stream finishes, optionally with tool calls and results). Redis and Postgres stores and a FastAPI app are in `examples/threads`.
- genui-react `core` entry (`genui-react/core`): renderer, transport, storage and headless chat state without `@openuidev/react-ui`. About 210 KB gzipped with React, against ~970 KB for the full chat. `sideEffects` now lists only CSS and `devtools.js`, so bundlers can drop unused exports.

- `docs/saving-tokens.md`: measured token costs (prompt per component and option, program sizes, a real Wander flow), an estimate formula, and ways to cut cost, including the planned `compact_history()` design.

**Faster:** `StreamParser` cleans only new lines and reuses the statements it has already finished, instead of rebuilding everything on every chunk. A 300-statement program streamed in 20-byte chunks: 1013 ms → 285 ms. Snapshots are identical to a full rebuild: a differential test compares every snapshot over the conformance fixtures and 300 random programs with random chunking. One huge single statement is still re-read while it is incomplete.

### Security

**Behaviour changes** (safer defaults):

- `to_model_messages()` / `read_run()` keep only `user` and `assistant` turns and drop client-sent `toolCalls`. Before, a browser could send its own `system` prompt or fake `tool` results. Opt back in with `roles=` and `tool_calls=True`.
- Agent exceptions reach the browser as a generic `RUN_ERROR` and are logged to the `genui` logger. Pass `expose_errors=True` for the old behaviour.

**Fixes:**

- `genui.lang.parse()` caps reference expansion at 200,000 values. A program under 1 KB that doubles a reference on every line used to take minutes.
- `read_run()` rejects bodies over 2 MB (413) and malformed JSON (400). `parse_run_input()` keeps the newest 200 messages / 500,000 characters (`max_messages`, `max_chars`) and raises `RunInputError` on a malformed body.
- Sync sources (generators, sync OpenAI/Anthropic streams) are stepped in a worker thread, so they no longer block the event loop.
- OpenAI-compatible servers that repeat a tool-call id on every chunk no longer start the call twice.
- The FastAPI import error now names the right package (`genui-py[fastapi]`).
- genui-react: `GenUIChat` only opens safe `@OpenUrl` links, with `noopener` (`safeLinks`). New: `safeUrl()`, `safeOpenUrl()`, `clearChatHistory()`. The README documents the `katex` override (the examples and site use it). The `zod` 3.x advisory through `@ag-ui/core` stays open until OpenUI updates: overriding it to zod 4 breaks `@ag-ui/core`'s types.
- CI actions are pinned to commit SHAs. Removed `publish-placeholder.sh`.

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
