/**
 * Dev-only demo (`?demo=1` prefilled, `?demo=live` streamed): a canned conversation rendered
 * through the real Renderer, plus a fake ChatLLM that streams AG-UI events — no backend needed.
 */
import type { ChatLLM, Message } from "@openuidev/react-headless";
import { agUIAdapter } from "@openuidev/react-headless";
import { buildActionUserMessage } from "./messages";

const img = (id: string) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=1200&q=80`;

const MANALI = {
  id: "manali-canopy-treehouse",
  name: "Canopy House",
  location: "Old Manali, Himachal Pradesh",
  image: img("1510798831971-661eb04b3739"),
  images: [
    img("1510798831971-661eb04b3739"),
    img("1611892440504-42a792e24d32"),
    img("1449158743715-0a90ebb6d2d8"),
    img("1506905925346-21bda4d32df4"),
    img("1590490360182-c33d57733427"),
  ],
};

const STEP_GREETING = `root = Stack([hello, intro, chips])
hello = Heading("Where shall we wander?", "Hand-picked stays for travellers who want more than a room.")
intro = Text("Tell me a mood, a region or a budget — a **cedar treehouse** above the clouds, a *dome under desert stars*, a houseboat drifting through palms. I'll find it and book it, right here.")
chips = Suggestions(["A treehouse in the Himalayas", "Desert domes under the stars", "Slow days on a Kerala houseboat"])`;

const STEP_GRID = `root = Stack([title, intro, grid, chips])
title = Heading("Three escapes for mid-November", "Each one hand-checked for that long-weekend feeling.")
intro = Text("Crisp mountain air, a sky without light pollution, or a slow drift through the backwaters — tap a stay to see it up close.")
grid = StayGrid([c1, c2, c3])
c1 = StayCard("${MANALI.id}", "${MANALI.name}", "${MANALI.location}", "${MANALI.image}", 16500, 4.96, ["Treehouse", "Fireplace"], @ToAssistant("Show ${MANALI.name}", {"stayId": "${MANALI.id}"}))
c2 = StayCard("jaisalmer-stargazer-dome", "Stargazer Dome", "Sam Dunes, Jaisalmer", "${img("1473580044384-7ba9967e16a0")}", 12800, 4.89, ["Desert", "Stargazing"], @ToAssistant("Show Stargazer Dome", {"stayId": "jaisalmer-stargazer-dome"}))
c3 = StayCard("alleppey-kettuvallam", "Vembanad Kettuvallam", "Alleppey, Kerala", "${img("1602216056096-3b40cc0c9944")}", 21000, 4.92, ["Houseboat", "Private chef"], @ToAssistant("Show Vembanad Kettuvallam", {"stayId": "alleppey-kettuvallam"}))
chips = Suggestions(["Under ₹15k a night", "Something pet-friendly", "Show me more mountains"])`;

const STEP_DETAIL = `$checkIn = "2026-11-13"
$checkOut = "2026-11-16"
$adults = 2
$children = 0
root = Stack([detail, form], "column", "lg")
detail = StayDetail("${MANALI.id}", "${MANALI.name}", "${MANALI.location}", ${JSON.stringify(MANALI.images)}, "A two-storey cedar treehouse wrapped around a 200-year-old deodar, ten minutes' walk above Old Manali. Mornings start with apple-wood smoke, mountain tea and the Pir Panjal turning pink outside a wall of glass.", ["Wood-fired hot tub", "Fireplace", "Chef-cooked breakfast", "Valley-view deck", "Fast Wi-Fi", "Guided forest walks"], 16500, 4.96, 214)
form = Form([dates, guests, check])
dates = DateRangePicker("When are you going?", $checkIn, $checkOut, ["2026-11-07", "2026-11-08", "2026-11-20", "2026-11-21", "2026-11-22"], 2)
guests = GuestPicker("Who's coming?", $adults, $children, 4)
check = Button("Check availability", @ToAssistant("Check availability", {"stayId": "${MANALI.id}"}))`;

const STEP_PRICE = `root = Stack([title, receipt, note, actions])
title = Heading("Your dates are free", "Fri 13 – Mon 16 Nov · 2 guests · 3 nights")
receipt = PriceSummary([{label: "₹16,500 × 3 nights", amount: 49500}, {label: "Cleaning fee", amount: 1800}, {label: "GST (12%)", amount: 6156}], 57456, "INR")
note = Text("Free cancellation until 6 November. Your host will have the fire lit when you arrive.", "muted")
actions = Stack([confirm, change], "row", "sm")
confirm = Button("Confirm booking", @ToAssistant("Confirm booking", {"stayId": "${MANALI.id}", "checkIn": "2026-11-13", "checkOut": "2026-11-16", "adults": 2, "children": 0}))
change = Button("Change dates", @ToAssistant("Change dates for ${MANALI.name}", {"stayId": "${MANALI.id}"}), "secondary")`;

const STEP_TICKET = `root = Stack([title, ticket, tip, chips], "column", "lg")
title = Heading("You're going to Manali", "Canopy House is expecting you on Friday the 13th — the lucky kind.")
ticket = BookingTicket("WND-7K3Q9", "${MANALI.name}", "${MANALI.location}", "${MANALI.image}", "2026-11-13", "2026-11-16", 2, 57456, "INR")
tip = Callout("Pack for 2°C nights", "November evenings are crisp in Old Manali. Bring a warm layer — the hot tub and fireplace handle the rest.", "success")
chips = Suggestions(["Add a guided trek", "Plan the drive from Delhi", "Find another escape"])`;

const formState = { $checkIn: "2026-11-13", $checkOut: "2026-11-16", $adults: 2, $children: 0 };

const userAction = (message: string, context: unknown, state: Record<string, unknown> = {}) =>
  buildActionUserMessage({
    type: "continue_conversation",
    humanFriendlyMessage: message,
    params: { context },
    formState: state,
  });

let n = 0;
const id = (p: string) => `${p}-${++n}`;

function toolPair(name: string, args: unknown, result: unknown): Message[] {
  const callId = id("call");
  return [
    {
      id: id("a"),
      role: "assistant",
      content: "",
      toolCalls: [{ id: callId, type: "function", function: { name, arguments: JSON.stringify(args) } }],
    },
    { id: id("t"), role: "tool", toolCallId: callId, content: JSON.stringify(result) },
  ] as Message[];
}

export function demoConversation(): Message[] {
  return [
    { id: id("a"), role: "assistant", content: STEP_GREETING },
    { id: id("u"), role: "user", content: "Somewhere unforgettable for a long weekend in mid-November" },
    ...toolPair("search_stays", { query: "long weekend november" }, { count: 3 }),
    { id: id("a"), role: "assistant", content: STEP_GRID },
    { id: id("u"), role: "user", content: userAction(`Show ${MANALI.name}`, { stayId: MANALI.id }) },
    ...toolPair("get_stay", { id: MANALI.id }, { ok: true }),
    { id: id("a"), role: "assistant", content: STEP_DETAIL },
    { id: id("u"), role: "user", content: userAction("Check availability", { stayId: MANALI.id }, formState) },
    ...toolPair("check_availability", { id: MANALI.id }, { available: true }),
    { id: id("a"), role: "assistant", content: STEP_PRICE },
    { id: id("u"), role: "user", content: userAction("Confirm booking", { stayId: MANALI.id }, formState) },
    ...toolPair("create_booking", { id: MANALI.id }, { code: "WND-7K3Q9" }),
    { id: id("a"), role: "assistant", content: STEP_TICKET },
  ] as Message[];
}

/* ------------------------------------------------------- streaming fake LLM */
function pickStep(text: string): { tool: string; program: string } {
  if (/confirm/i.test(text)) return { tool: "create_booking", program: STEP_TICKET };
  if (/check availability/i.test(text)) return { tool: "check_availability", program: STEP_PRICE };
  if (/^\s*(\]\]>openui:content\s*)?show /i.test(text) || /change dates/i.test(text))
    return { tool: "get_stay", program: STEP_DETAIL };
  return { tool: "search_stays", program: STEP_GRID };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function demoLLM(): ChatLLM {
  return {
    streamProtocol: agUIAdapter(),
    async send({ messages, signal }) {
      const last = [...messages].reverse().find((m) => m.role === "user");
      const text = typeof last?.content === "string" ? last.content : "";
      console.info("[wander demo] user turn:", JSON.stringify(text));
      const step = pickStep(text);
      const enc = new TextEncoder();
      const stream = new ReadableStream<Uint8Array>({
        async start(controller) {
          const emit = (e: Record<string, unknown>) => controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
          try {
            emit({ type: "RUN_STARTED", threadId: "demo", runId: id("run") });
            const callId = id("call");
            emit({ type: "TOOL_CALL_START", toolCallId: callId, toolCallName: step.tool });
            emit({ type: "TOOL_CALL_ARGS", toolCallId: callId, delta: "{}" });
            emit({ type: "TOOL_CALL_END", toolCallId: callId });
            await sleep(1100);
            emit({ type: "TOOL_CALL_RESULT", toolCallId: callId, messageId: id("t"), content: "{}" });
            const mid = id("m");
            emit({ type: "TEXT_MESSAGE_START", messageId: mid, role: "assistant" });
            const p = step.program;
            for (let i = 0; i < p.length; i += 24) {
              if (signal.aborted) break;
              emit({ type: "TEXT_MESSAGE_CONTENT", messageId: mid, delta: p.slice(i, i + 24) });
              await sleep(28);
            }
            emit({ type: "TEXT_MESSAGE_END", messageId: mid });
            emit({ type: "RUN_FINISHED", threadId: "demo", runId: "x" });
          } finally {
            controller.close();
          }
        },
      });
      return new Response(stream, { headers: { "Content-Type": "text/event-stream" } });
    },
  };
}
