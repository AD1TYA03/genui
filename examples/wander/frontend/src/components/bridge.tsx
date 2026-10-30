import { createContext, useContext } from "react";

/**
 * The chat shell provides this so library components (e.g. Suggestions) can send a plain
 * user message without going through the OpenUI action/form-state machinery.
 */
export interface ChatBridge {
  send: (text: string) => void;
  busy: boolean;
}

export const ChatBridgeContext = createContext<ChatBridge | null>(null);

export function useChatBridge(): ChatBridge | null {
  return useContext(ChatBridgeContext);
}

export function formatMoney(amount: number | undefined, currency = "INR"): string {
  if (typeof amount !== "number" || Number.isNaN(amount)) return "—";
  try {
    return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${Math.round(amount).toLocaleString()}`;
  }
}

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

/** Parse "YYYY-MM-DD" as a local date (no timezone drift). */
export function parseISODate(s: unknown): Date | null {
  if (typeof s !== "string") return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s.trim());
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function formatShortDate(s: unknown, withWeekday = false): string {
  const d = parseISODate(s);
  if (!d) return typeof s === "string" ? s : "—";
  return d.toLocaleDateString("en-GB", {
    ...(withWeekday ? { weekday: "short" } : {}),
    day: "numeric",
    month: "short",
  });
}

export function nightsBetween(a: unknown, b: unknown): number {
  const da = parseISODate(a);
  const db = parseISODate(b);
  if (!da || !db) return 0;
  return Math.max(0, Math.round((db.getTime() - da.getTime()) / 86_400_000));
}
