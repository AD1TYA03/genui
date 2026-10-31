# Saving tokens with genui

Where the tokens go in a genui app, how to estimate them, and how to spend fewer. All numbers
were measured in this repo (October 2026). Token counts use OpenAI's `o200k` tokenizer; Gemini
and Claude count roughly ±10% differently, but the proportions hold.

## Where the tokens go

Every model call sends:

```
input  = system prompt  +  tool schemas  +  chat history  +  the new user turn
output = the UI program (OpenUI Lang)  +  thinking tokens (if the model thinks)
```

Output usually costs 4–8× more per token than input (e.g. `gemini-3-flash-preview`: $0.50 input,
$0.05 cached input, $3.00 output per million tokens).

## Estimating your prompt

| Part | Tokens | Notes |
| --- | --- | --- |
| OpenUI Lang syntax rules (fixed) | **~500–1,100** | 526 for a 3-component library; 1,114 for the 12-component fixture library |
| ↳ with `tools=[...]` | **+~2,500** | Teaches `Query()` / `Mutation()`. Only pass it if the *UI itself* calls tools. Your LLM's function calling doesn't need it. |
| ↳ with `bindings=True` | +~800 | Two-way `$state` bindings for forms |
| ↳ with `edit_mode=True` | +~250 | Patch-style edits of the previous program |
| ↳ with `inline_mode=True` | +~200 | Prose with embedded programs |
| ↳ with examples | +~1,000–1,500 | OpenUI's default library ships examples: 2,380 tokens of rules + examples in total |
| **Each component** | **~50–60** | Signature + description. Median 51, average 58, largest 280 (OpenUI's 82 default components) |
| Your own rules / persona | varies | Wander: 1,315 |
| Each LLM tool schema | ~100–200 | Wander: 612 for 4 tools |

**Rule of thumb:** `prompt ≈ 1,000 + 55 × components + your rules`.

| Library size | Prompt (approx.) |
| --- | --- |
| 15 components (Wander has 14) | ~1,800 + your rules |
| 25 components (one focused agent) | ~2,400 + your rules |
| 82 components (OpenUI's default library) | 7,100 (measured) |
| 90 components in one prompt | ~6,000–8,000 |

## Estimating output

| What the model writes | Tokens |
| --- | --- |
| A small reply (heading, text, suggestions) | ~150–250 |
| A list of 3 rich cards | ~430 |
| A detail view with gallery, calendar and price | ~700 |
| The same 3-card list as compact JSON | ~510 (+18%) |
| …as pretty-printed JSON (how models usually write JSON) | ~775 (+79%) |
| …as plain markdown (no interactive UI) | ~165 |

OpenUI Lang is the most compact way here to get interactive UI out of a model.

## OpenUI Lang vs JSON-based UI

The same UIs, measured three ways: as OpenUI Lang, as the equivalent nested JSON component tree
(`{"type": ..., "props": {...}}`, the leanest common JSON shape), and as pretty-printed JSON, which
is how models usually write JSON unless told otherwise.

### Output: what the model writes

| Program | OpenUI Lang | Compact JSON | Pretty JSON |
| --- | --- | --- | --- |
| Wander greeting | 113 | 132 | 193 |
| Wander stay grid | 432 | 510 | 775 |
| Wander price summary | 235 | 273 | 485 |
| Wander booking ticket | 195 | 230 | 344 |
| Analytics dashboard | 842 | 928 | 1,739 |
| Appointment form | 690 | 868 | 1,608 |
| Product comparison | 391 | 413 | 639 |
| Recipe card | 896 | 868 | 1,407 |
| Support triage | 535 | 595 | 993 |
| Travel booking | 655 | 823 | 1,523 |
| **Total (10 programs)** | **4,984** | **5,640 (+13%)** | **9,706 (+95%)** |

Compact JSON ranges from −3% (recipe card, mostly long text) to +26% (a form with many fields).
Pretty JSON ranges from +57% to +133%. The gap grows with structure: forms, tables and dashboards
repeat `"type"` / `"props"` / key names in JSON, while OpenUI Lang passes arguments by position.
Flat JSON formats (every component with an `id` and a list of child ids) are larger still.

### Input: what the prompt must describe

| Library | OpenUI signatures | JSON Schema of the same components |
| --- | --- | --- |
| Wander (14 components) | 755 | 1,723 (2.3×) |
| OpenUI default (82 components) | 4,721 | 11,512 (2.4×) |

A JSON approach usually sends the JSON Schema, in the prompt or as a structured-output schema;
both are billed as input. OpenUI Lang also needs its syntax rules (~900 tokens) where JSON needs
fewer format instructions (~300). Net, per call: Wander's JSON prompt is still ~350–400 tokens
larger, and for 82 components ~6,000 tokens larger.

### Cost: the Wander booking flow

| Format | Extra tokens vs OpenUI Lang | Extra cost | vs $0.025 flow |
| --- | --- | --- | --- |
| Compact JSON | +221 output, +~3,000 input | +~$0.002 | **~+10%** |
| Pretty JSON | +1,588 output, +~3,000 input | +~$0.006 | **~+25%** |

The savings grow with the library (JSON Schema is ~2.4× per component) and with structure-heavy UIs
(forms and tables: up to +26% compact, +133% pretty). Prompt caching narrows the input side for
both formats; the output gap stays, and output is the expensive side.

### Beyond tokens

| | OpenUI Lang | JSON |
| --- | --- | --- |
| **Streaming** | Each line is a complete statement and renders as soon as it arrives. `root` comes first, so the layout appears immediately and fills in. | A nested tree is valid only when its brackets close. Progressive rendering needs a partial-JSON parser, and the root object finishes last. |
| **Errors** | A bad statement is dropped with a structured error and hint; the rest renders. `autofix()` feeds the errors back. | One missing bracket or quote breaks the whole document unless repaired. |
| **Reuse** | Define a value once and reference it (`c1` in a grid and in a detail view). | Repeated values are written out again. |
| **Logic** | State (`$checkIn`), bindings, expressions and actions are part of the language. | Needs a custom convention on top of JSON. |
| **Where JSON wins** | | Every model and tool knows it; constrained decoding can guarantee valid syntax; standard JSON Schema validators. |

**Bottom line:** OpenUI Lang writes ~13% fewer tokens than the leanest JSON and ~half of what models
write as pretty JSON, needs a ~2.4× smaller component description, and streams and degrades better.
JSON's advantage is ubiquity and guaranteed-valid syntax, not cost.

## A measured flow: Wander

A real booking (search → open stay → dates → book) on `gemini-3-flash-preview`:

| Step | Model calls | Input | Output + thinking | Cost |
| --- | --- | --- | --- | --- |
| Search | 2 | 8,139 | 297 + 269 | $0.0058 |
| Open stay | 2 | 8,901 | 704 + 337 | $0.0076 |
| Dates | 2 | 9,791 (2,020 cached) | 327 + 0 | $0.0050 |
| Book | 2 | 10,696 (4,041 cached) | 348 + 594 | $0.0064 |
| **Total** | **8** | **37,527** | **1,676 + 1,200** | **$0.025 (≈ ₹2)** |

Roughly: ~45% from making two calls per step, ~20% history, ~15% OpenUI syntax rules, ~13% writing
UI instead of text, the rest thinking.

## How to spend fewer tokens (by impact)

### 1. Cache the system prompt — ~40% on short flows

The system prompt and tool schemas are the same on every call. Put them first and unchanged
(no timestamps or per-user text at the top), then use your provider's prompt caching: Gemini
context caching, Anthropic `cache_control`, OpenAI's automatic prefix caching. Cached input is
~90% cheaper, which makes the OpenUI rules almost free (~15% → ~2% of the flow).

Put per-request values (today's date, the user's name) in the last message, not the system prompt.

### 2. Compact old UI programs in history — ~3–5% on short flows, ~30–50% on long chats

> **Status: planned.** A `compact_history()` helper is not in genui yet. This is the design.

The browser stores every UI program, and each one is resent to the model on every later call,
twice per step when the agent calls a tool. Replace **older** programs with a one-line summary in
the copy sent to the model. **The frontend does not change:** it keeps rendering and storing the full
programs. Only the server-side history the model reads gets shorter.

```
before:  user · <430-token stay grid> · user · <700-token detail> · user · <program 3> · user
after:   user · "Showed 3 stays: Canopy House (manali-canopy-treehouse, ₹16,500), …" ·
         user · "Showed Canopy House detail with a date picker" · user · <program 3> · user
```

Do:

- **Keep the most recent program in full.** The model needs it for "change the dates", "the second
  one", and edit-mode patches.
- **Keep IDs and key values** in summaries (stay IDs, prices, dates, booking codes), so the model
  doesn't have to call tools again.
- **Build summaries with code**, not an LLM: parse the program with `genui.lang.parse` and list the
  components with their key props. That costs nothing and is deterministic.
- **Keep summaries deterministic.** The same program must always give the same text, or the history
  prefix changes and prompt caching breaks.
- Validate the last program (to feed errors back) **before** compacting.

Avoid: summarizing the last program; vague summaries ("showed some stays"); LLM-written summaries.

Clicks keep working, because a click carries its own data (`{"stayId": ...}`).

Estimated savings for Wander-sized programs (~165–700 tokens each, kept in full for one turn):

| Conversation | Tokens saved | Share of input |
| --- | --- | --- |
| 4-step booking | ~1,400–1,600 | ~3–5% |
| 20 turns | ~70,000–90,000 | ~30–35% |
| 50 turns | ~600,000 | ~50% |

Model: ~3,600-token prompt, ~300-token programs compacted to ~40-token summaries, 2 calls per
turn, last program kept in full. Savings grow roughly with the square of the conversation length.

### 3. Fewer components per agent — ~55 tokens each, plus accuracy

Split a large library by area (e.g. CRM, Desk, Books agents with ~20–30 components each) and give
each agent only its components. A 90-component prompt costs ~6–8k tokens per call. A
25-component one costs ~2.4k, and the model picks the right component more often.

Keep descriptions short and concrete. The largest default component costs 280 tokens because of
its long description.

### 4. Don't pass `tools=` to `system_prompt()` unless the UI calls tools — saves ~2,500

`tools=` teaches the model `Query()`/`Mutation()`, for UIs that fetch data themselves. Normal LLM
function calling (your agent runs tools on the server) doesn't need it.

### 5. One model call per step where possible — up to ~45% on those steps

A tool-using step makes two calls: one to call the tool, one to write the UI. Both resend the full
prompt and history. When a tool result maps directly to a fixed UI (e.g. "booking confirmed" →
ticket), build that program from the result in code and skip the second call.

### 6. Control thinking — up to ~15% of output cost

Thinking tokens are billed as output. Use a low reasoning or thinking budget for simple steps
(date checks, confirmations) and a higher one only where it pays off.

### 7. Use a cheaper model for simple steps — 30–50%

Route simple turns (search, availability) to a smaller model and keep the strongest model for rich
UI. Check quality with `autofix()` statistics before switching.

### 8. Budget for `autofix()` retries

A correction round costs one more call (≈ prompt + history + one program), but only when the
program has errors. Track how often it retries (the `genui` logger logs every round). A high rate
usually means the component descriptions need work, which is cheaper to fix than paying for retries.

## Quick estimate for your app

```
per call input   ≈ 1,000 + 55 × components + your rules + 150 × LLM tools + history
per step output  ≈ 200–700 (program) + thinking
calls per step   = 1 (no tools) or 2 (tool call + answer)
history per turn ≈ +(user text + program) for every earlier turn, unless compacted
```

Example: 25 components, 600 tokens of rules, 5 tools, 2 calls per step, no caching:
~4,000 input tokens per call at the first step, growing ~500–700 per turn, plus ~400–900 output
per step. With caching and history compaction, a long conversation costs about half that.
