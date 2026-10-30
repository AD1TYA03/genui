# Wander backend

The Python half of Wander, an AI concierge for extraordinary stays in India. It runs a Gemini
tool-calling agent whose answers are OpenUI Lang, and streams them to the React frontend with
[genui](../../../README.md). The UI contract is in [`../CONTRACT.md`](../CONTRACT.md).

## Run

```bash
# 1. Gemini key: put it in the env, or store it once in the macOS Keychain
export GEMINI_API_KEY=...
# or
security add-generic-password -U -a genui -s gemini-api-key -w    # prompts for the key

# 2. Start the API on :8000 (the Vite dev server on :5173 proxies or calls it; CORS is open for it)
uv run uvicorn app:app --reload --port 8000

# 3. Check it
curl localhost:8000/api/health
```

Model: `gemini-3.8-flash` by default (bare id, as Gemini's OpenAI-compatible endpoint expects).
Override it with `MODEL=gemini-3.5-flash-lite uv run uvicorn app:app ...` for a faster, cheaper run.

Tests use a fake model, so no key is needed:

```bash
uv run pytest -q
```

## Files

| file | what it does |
| --- | --- |
| `app.py` | FastAPI: `POST /api/chat` (AG-UI SSE), `GET /api/health`, CORS for `localhost:5173`. |
| `agent.py` | System prompt from the LibrarySpec, the Gemini client, the tool loop, history cleanup, validation. |
| `tools.py` | `search_stays`, `get_stay`, `check_availability`, `create_booking`: pure functions, their OpenAI tool schemas and a dispatcher. |
| `data.py` | Ten stays across India, with verified Unsplash images and blocked dates relative to today. |
| `spec.json` | The component library, written by the frontend (`npm run generate` in `../frontend`). Git-ignored. |
| `spec.dev.json` | A hand-written stand-in with the same signatures, used when `spec.json` is missing (fresh clone). |

## Architecture

```
React (frontend/)                         Python (this folder)
─────────────────                         ────────────────────
src/library.tsx ──npm run generate──▶ spec.json ─▶ Library.from_spec() ─▶ library.system_prompt()
agUIAdapter() ──POST /api/chat──────▶ read_run(): AG-UI body -> clean chat history
                                          run_agent():
                                            loop: Gemini (stream, tools) ─▶ tool calls ─▶ tools.py
                                                   ToolCallStart/Args/End + ToolResult events
                                            final round: OpenUI Lang text, streamed as it arrives
                ◀──AG-UI SSE─────────── stream_response(run_agent(...), run=run)
StayCard / Button click @ToAssistant ──▶ next turn, with form state and {"stayId": ...} context
```

The agent loop (`agent.run_agent`) is an async generator that yields two kinds of items, and
genui turns both into AG-UI events:

- **Tool activity.** Each tool call becomes `ToolCallStart`, `ToolCallArgs`, `ToolCallEnd` and
  `ToolResult`, which genui encodes as `TOOL_CALL_START/ARGS/END/RESULT`. The frontend uses them
  to show "Searching stays..." while the model works.
- **The answer.** OpenUI Lang text, streamed delta by delta as `TEXT_MESSAGE_CONTENT`, so the UI
  builds itself while the model is still writing. Text is held back only until its first newline:
  if the model writes a remark and then decides to call a tool, that remark never reaches the UI.

Gemini 3 attaches a thought signature (`extra_content.google.thought_signature`) to tool calls.
The loop keeps it and sends it back with the assistant turn, as Gemini requires.

History: `read_run()` gives clean user/assistant turns (markers stripped, button clicks turned
into `message + context and form values = {...}`). The agent also drops tool calls and tool
results of earlier turns: the UI program of each turn is enough context, and replayed tool calls
without their thought signatures would be rejected by Gemini.

### Validation, and why there is no in-turn repair round

The final program is checked with `genui.lang.parse(text, spec)`. A repair round in the same turn
would mean either buffering the whole answer (losing the live-building UI, the point of the demo)
or streaming a second program after the first. So instead the errors are fed back on the **next**
request, as spec/prompt.md section 6.2 recommends: `prepare_history` re-parses the previous
assistant program from the history and, if it had errors, adds them as a system note. Errors are
also logged on the server when they happen.

## How it shows off genui

- **One source of truth.** The prompt is generated from the same `spec.json` the React renderer
  is built from, so the model only knows components that exist, with their real signatures.
- **Any agent shape.** The agent is plain Python yielding strings and genui events; no framework.
- **Tool calls in the UI.** genui's provider-neutral tool events become AG-UI tool events.
- **Round-trips.** `@ToAssistant` clicks and form state (dates, guests) arrive as clean model
  input through `read_run()`.
- **Validation in Python.** `genui.lang.parse` checks programs against the spec with the same
  rules as the TypeScript renderer.
