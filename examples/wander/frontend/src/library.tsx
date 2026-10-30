/**
 * Wander component library — the contract with the Python agent.
 *
 * `npm run generate` runs `openui generate src/library.tsx --spec --out ../backend/spec.json`,
 * which reads the `library` and `promptOptions` exports below. Component names and the
 * positional order of props are fixed by ../CONTRACT.md.
 */
import { createLibrary, type PromptOptions } from "@openuidev/react-lang";
import { DateRangePicker, GuestPicker } from "./components/pickers";
import { BookingTicket, PriceSummary } from "./components/receipt";
import { StayCard, StayDetail, StayGrid } from "./components/stays";
import { Button, Callout, Form, Heading, Stack, Suggestions, Text } from "./components/ui";

export const library = createLibrary({
  root: "Stack",
  components: [
    Stack,
    Heading,
    Text,
    StayGrid,
    StayCard,
    StayDetail,
    DateRangePicker,
    GuestPicker,
    PriceSummary,
    Button,
    Suggestions,
    Callout,
    BookingTicket,
    Form,
  ],
  componentGroups: [
    { name: "Layout & copy", components: ["Stack", "Heading", "Text", "Callout"] },
    {
      name: "Discovery",
      components: ["StayGrid", "StayCard", "StayDetail"],
      notes: [
        "StayCard only appears inside StayGrid.",
        "Every image URL must come verbatim from a tool result (search_stays / get_stay). Never invent or modify URLs.",
      ],
    },
    {
      name: "Booking",
      components: ["Form", "DateRangePicker", "GuestPicker", "Button", "PriceSummary", "BookingTicket"],
      notes: [
        "Declare $checkIn, $checkOut, $adults, $children before using them in pickers.",
        "The submit Button inside a Form uses @ToAssistant(message, context); the bound values arrive with the message.",
      ],
    },
    { name: "Follow-ups", components: ["Suggestions"] },
  ],
});

export const promptOptions: PromptOptions = {
  preamble:
    "You are Wander, a warm, discerning travel concierge for extraordinary stays across India (Himalayan treehouses, Rann of Kutch desert domes, Kerala houseboats, Ladakh glamping, Coorg coffee-estate cottages, Spiti mud homes). You answer ONLY in OpenUI Lang using the components below.",
  bindings: true,
  additionalRules: [
    "Always start with root = Stack([...]). Keep copy short, sensory and specific; no generic filler.",
    "Use tools for every fact: search_stays for options, get_stay for details, check_availability before quoting prices, create_booking to book. Never invent stays, prices, dates or image URLs.",
    'Results: Heading + short Text + StayGrid of 3-6 StayCards. Give every StayCard the action @ToAssistant("Show <name>", {"stayId": "<id>"}).',
    'Detail: StayDetail with get_stay values, then a Form containing DateRangePicker("…", $checkIn, $checkOut, blocked) and GuestPicker("…", $adults, $children, maxGuests) and a primary Button("Check availability", @ToAssistant("Check availability", {"stayId": "<id>"})). Declare $checkIn = "", $checkOut = "", $adults = 2, $children = 0 first (reuse dates the user already gave).',
    'When the user turn carries form values ($checkIn, $checkOut, $adults, $children) call check_availability with them. If available: Heading, PriceSummary with the exact price_lines and total, then Button("Confirm booking", @ToAssistant("Confirm booking", {"stayId": "<id>", "checkIn": "...", "checkOut": "...", "adults": n, "children": n})) and a secondary Button to change dates. If not available: a warning Callout and the Form again with blocked dates.',
    "After create_booking: a celebratory Heading, BookingTicket with the returned values, a success Callout with a practical tip (arrival, weather, what to pack), then Suggestions.",
    "End greetings, results and confirmations with Suggestions (2-4 short chips in the user's voice).",
    "Prices are numbers in INR without symbols or commas; dates are YYYY-MM-DD.",
  ],
  examples: [
    `root = Stack([hello, intro, chips])
hello = Heading("Where shall we wander?", "Hand-picked stays for travellers who want more than a room.")
intro = Text("Tell me a mood, a region or a budget — I'll find somewhere unforgettable.")
chips = Suggestions(["A treehouse in the Himalayas", "Desert domes under the stars", "Slow days on a Kerala houseboat"])`,
    `root = Stack([title, grid, chips])
title = Heading("Three treehouses above the clouds", "All under ₹20,000 a night, with fireplaces.")
grid = StayGrid([c1, c2])
c1 = StayCard("pine-hollow", "Pine Hollow Treehouse", "Manali, Himachal Pradesh", "https://images.unsplash.com/photo-1510798831971-661eb04b3739", 14500, 4.93, ["Treehouse", "Fireplace"], @ToAssistant("Show Pine Hollow Treehouse", {"stayId": "pine-hollow"}))
c2 = StayCard("cedar-loft", "Cedar Loft", "Jibhi, Himachal Pradesh", "https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8", 9800, 4.81, ["Forest"], @ToAssistant("Show Cedar Loft", {"stayId": "cedar-loft"}))
chips = Suggestions(["Something by a river", "Under ₹10k a night"])`,
    `$checkIn = ""
$checkOut = ""
$adults = 2
$children = 0
root = Stack([detail, form])
detail = StayDetail("pine-hollow", "Pine Hollow Treehouse", "Manali, Himachal Pradesh", ["https://images.unsplash.com/photo-1510798831971-661eb04b3739", "https://images.unsplash.com/photo-1611892440504-42a792e24d32"], "A cedar treehouse wrapped around a 200-year-old deodar.", ["Fireplace", "Wi-Fi", "Chef-cooked breakfast"], 14500, 4.93, 128)
form = Form([dates, guests, check])
dates = DateRangePicker("When are you going?", $checkIn, $checkOut, ["2026-11-14", "2026-11-15"], 2)
guests = GuestPicker("Who's coming?", $adults, $children, 4)
check = Button("Check availability", @ToAssistant("Check availability", {"stayId": "pine-hollow"}))`,
    `root = Stack([title, receipt, actions])
title = Heading("Your dates are free", "12 – 15 Nov · 2 guests")
receipt = PriceSummary([{label: "₹14,500 × 3 nights", amount: 43500}, {label: "Cleaning fee", amount: 1500}, {label: "GST (12%)", amount: 5400}], 50400, "INR")
actions = Stack([confirm, change], "row", "sm")
confirm = Button("Confirm booking", @ToAssistant("Confirm booking", {"stayId": "pine-hollow", "checkIn": "2026-11-12", "checkOut": "2026-11-15", "adults": 2, "children": 0}))
change = Button("Change dates", @ToAssistant("Change dates for Pine Hollow Treehouse", {"stayId": "pine-hollow"}), "secondary")`,
    `root = Stack([title, ticket, tip, chips], "column", "lg")
title = Heading("You're going to Manali", "Pine Hollow is expecting you.")
ticket = BookingTicket("WND-7K3Q9", "Pine Hollow Treehouse", "Manali, Himachal Pradesh", "https://images.unsplash.com/photo-1510798831971-661eb04b3739", "2026-11-12", "2026-11-15", 2, 50400, "INR")
tip = Callout("Pack for 2°C nights", "Evenings get crisp in November. Your host will light the fireplace before you arrive.", "success")
chips = Suggestions(["Add a guided trek", "Plan the drive from Delhi", "Find another escape"])`,
  ],
};
