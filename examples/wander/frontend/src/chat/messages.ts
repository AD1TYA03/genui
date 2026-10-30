import type { Message } from "@openuidev/react-headless";
import { BuiltinActionType, buildMessage, parseMessage, type ActionEvent } from "@openuidev/react-lang";
import { formatShortDate } from "../components/bridge";

export function textOf(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content))
    return content
      .map((p) => (p && typeof p === "object" && "text" in p ? String((p as { text: unknown }).text ?? "") : ""))
      .join("");
  return "";
}

/** Split a stored message into its OpenUI content and context (marker lines removed). */
export function readMessage(raw: string, streaming = false): { content: string; context: unknown } {
  const parsed = parseMessage(raw, { streaming });
  return { content: parsed.content, context: parsed.context ?? null };
}

/**
 * The user turn for a `continue_conversation` action, in the OpenUI reference format
 * (spec/prompt.md §6.3), which genui's `to_model_messages` understands:
 *
 *   ]]>openui:content
 *   <message>
 *   ]]>openui:context
 *   ["User clicked: <message>", <formState>, <@ToAssistant context?>]
 */
export function buildActionUserMessage(event: ActionEvent): string {
  const ctx: unknown[] = [`User clicked: ${event.humanFriendlyMessage}`];
  const actionContext = event.params?.["context"];
  if (event.formState || actionContext !== undefined) ctx.push(event.formState ?? {});
  if (actionContext !== undefined) ctx.push(actionContext);
  const built = buildMessage({ content: event.humanFriendlyMessage, context: ctx });
  return event.humanFriendlyMessage ? built : built.slice(built.indexOf("\n") + 1);
}

export function isContinueConversation(event: ActionEvent) {
  return event.type === BuiltinActionType.ContinueConversation;
}

/** Plain values out of a formState map ($vars are plain; fields are {value, componentType}). */
function flattenState(state: unknown): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (!state || typeof state !== "object") return out;
  for (const [k, v] of Object.entries(state as Record<string, unknown>)) {
    if (v && typeof v === "object" && !Array.isArray(v) && "value" in v) out[k.replace(/^\$/, "")] = (v as { value: unknown }).value;
    else if (v && typeof v === "object" && !Array.isArray(v)) Object.assign(out, flattenState(v));
    else out[k.replace(/^\$/, "")] = v;
  }
  return out;
}

/** Human chips for the form values a user turn carried (dates, guests). */
export function summarizeContext(context: unknown): string[] {
  if (!Array.isArray(context)) return [];
  const state = flattenState(context[1]);
  const chips: string[] = [];
  const ci = state["checkIn"];
  const co = state["checkOut"];
  if (typeof ci === "string" && ci && typeof co === "string" && co)
    chips.push(`${formatShortDate(ci)} → ${formatShortDate(co)}`);
  const a = Number(state["adults"]);
  const c = Number(state["children"]);
  if (Number.isFinite(a) && a > 0) {
    let g = `${a} adult${a === 1 ? "" : "s"}`;
    if (Number.isFinite(c) && c > 0) g += ` · ${c} child${c === 1 ? "" : "ren"}`;
    chips.push(g);
  }
  return chips;
}

export interface Turn {
  user?: Message;
  agent: Message[];
}

/** Group a flat AG-UI message list into user → agent turns. */
export function groupTurns(messages: Message[]): Turn[] {
  const turns: Turn[] = [];
  for (const m of messages) {
    if (m.role === "user") turns.push({ user: m, agent: [] });
    else if (m.role === "assistant" || m.role === "tool") {
      if (!turns.length) turns.push({ agent: [] });
      turns[turns.length - 1].agent.push(m);
    }
  }
  return turns;
}

const TOOL_LABELS: Record<string, [string, string]> = {
  search_stays: ["Wandering through stays", "Wandered through stays"],
  get_stay: ["Leafing through the guestbook", "Read the guestbook"],
  check_availability: ["Checking the calendar", "Checked the calendar"],
  create_booking: ["Stamping your booking", "Booking stamped"],
};

export function toolLabel(name: string, done: boolean): string {
  const hit = TOOL_LABELS[name];
  if (hit) return done ? hit[1] : hit[0];
  const pretty = name.replace(/_/g, " ");
  return done ? `Ran ${pretty}` : `Running ${pretty}`;
}
