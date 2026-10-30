# Wander — contract between frontend and backend

Wander is a showcase app for genui: an AI concierge that books extraordinary stays in India
(Himalayan treehouses, Rann of Kutch desert domes, Kerala houseboats, Ladakh glamping, Coorg
coffee-estate cottages, Spiti mud homes). The Python agent (Gemini) answers ONLY in OpenUI Lang
using the component library below; the React app renders it.

## Layout
- `frontend/` — Vite + React 19 + TypeScript + Tailwind v4. Custom OpenUI component library
  (`src/library.tsx`, `defineComponent` + Zod 4 from `@openuidev/react-lang`). Custom chat shell
  (no default OpenUI chat chrome). Streams from `POST /api/chat` with `agUIAdapter()` via
  `@openuidev/react-headless`. `npm run generate` writes `../backend/spec.json` with the
  OpenUI CLI (`openui generate src/library.tsx --spec --out ../backend/spec.json`).
- `backend/` — FastAPI + `genui-py` (local editable path `../../..`) + Gemini via its
  OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`),
  key from env `GEMINI_API_KEY` (fallback: macOS Keychain service `gemini-api-key`).

## Component library (frontend owns; names and positional prop order are the contract)
Root component: `Stack`.
1. `Stack(children: any[], direction?: "column"|"row", gap?: "sm"|"md"|"lg")`
2. `Heading(text: string, subtitle?: string)`
3. `Text(content: string, tone?: "default"|"muted")`
4. `StayGrid(stays: StayCard[])`
5. `StayCard(id: string, name: string, location: string, image: string, pricePerNight: number, rating: number, tags?: string[], action?: Action)` — image MUST be a URL returned by a tool.
6. `StayDetail(id: string, name: string, location: string, images: string[], description: string, amenities: string[], pricePerNight: number, rating: number, reviews: number)`
7. `DateRangePicker(label: string, checkIn: $binding<string>, checkOut: $binding<string>, blocked?: string[], minNights?: number)` — ISO dates `YYYY-MM-DD`, beautiful two-month calendar, blocked dates disabled.
8. `GuestPicker(label: string, adults: $binding<number>, children: $binding<number>, max?: number)`
9. `PriceSummary(lines: {label: string, amount: number}[], total: number, currency?: string)`
10. `Button(label: string, action?: Action, variant?: "primary"|"secondary"|"ghost")`
11. `Suggestions(items: string[])` — tappable follow-up chips; tapping sends the text as the next user message.
12. `Callout(title: string, body: string, tone?: "info"|"success"|"warning")`
13. `BookingTicket(code: string, stayName: string, location: string, image: string, checkIn: string, checkOut: string, guests: number, total: number, currency?: string)` — boarding-pass style confirmation.
14. `Form(children: any[])`, used to group pickers with a submit Button whose action is `@ToAssistant(...)` so selections (form state) reach the agent.

## Backend tools (Python, mock data, deterministic)
- `search_stays(query?: str, region?: str, max_price?: int, guests?: int)` → list of stays `{id, name, location, region, image, images[], pricePerNight, rating, reviews, tags[], description, amenities[], maxGuests}`
- `get_stay(id: str)` → one stay
- `check_availability(id: str, check_in: str, check_out: str)` → `{available: bool, blocked: [dates], nights, price_lines: [{label, amount}], total, currency: "INR"}` (taxes 12% GST, cleaning fee)
- `create_booking(id, check_in, check_out, adults, children, name?)` → `{code, ...ticket fields}`
Image URLs: real, verified (HTTP 200) Unsplash `images.unsplash.com/photo-...` URLs, fixed in the mock data.

## Conversation flow the agent should drive
greet + Suggestions → search → StayGrid of StayCards (Button/StayCard action `@ToAssistant("Show <name>", {"stayId": id})`) → StayDetail + Form(DateRangePicker, GuestPicker, Button "Check availability" → @ToAssistant) → PriceSummary + Button "Confirm booking" → BookingTicket + Callout + Suggestions.
