"""Wander's backend tools: pure, deterministic functions over the mock data, plus their
OpenAI-format JSON schemas and a dispatcher the agent loop calls.

All money is INR (integers, rupees). Dates are ISO ``YYYY-MM-DD``; a stay from check_in to
check_out occupies the nights check_in .. check_out - 1.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any, Callable

from data import GST_RATE, all_stays, find_stay

CURRENCY = "INR"
_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I


class ToolError(ValueError):
    """A bad tool call. The message is returned to the model so it can correct itself."""


def _card(stay: dict[str, Any]) -> dict[str, Any]:
    """Search results drop the booking-only fields to keep the model context small."""
    return {k: v for k, v in stay.items() if k not in ("blocked", "cleaningFee")}


def search_stays(
    query: str | None = None,
    region: str | None = None,
    max_price: int | None = None,
    guests: int | None = None,
    *,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Stays matching every given filter, best rated first. ``query`` matches any word against
    name, location, region, tags and description; with no match it falls back to all stays
    (filtered by the other criteria) so the user always sees something."""
    stays = all_stays(today)
    if region:
        r = region.lower()
        stays = [s for s in stays if r in s["region"].lower() or r in s["location"].lower()]
    if max_price is not None:
        stays = [s for s in stays if s["pricePerNight"] <= int(max_price)]
    if guests is not None:
        stays = [s for s in stays if s["maxGuests"] >= int(guests)]
    if query:
        words = [w for w in query.lower().replace(",", " ").split() if len(w) > 2]

        def score(s: dict[str, Any]) -> int:
            hay = " ".join([s["name"], s["location"], s["region"], " ".join(s["tags"]), s["description"]]).lower()
            return sum(1 for w in words if w in hay or w.rstrip("s") in hay)

        scored = [(score(s), s) for s in stays]
        if any(sc for sc, _ in scored):
            stays = [s for sc, s in sorted(scored, key=lambda x: (-x[0], -x[1]["rating"])) if sc]
            return [_card(s) for s in stays]
    return [_card(s) for s in sorted(stays, key=lambda s: -s["rating"])]


def get_stay(id: str, *, today: date | None = None) -> dict[str, Any]:
    stay = find_stay(id, today)
    if stay is None:
        raise ToolError(f"No stay with id {id!r}. Call search_stays to get valid ids.")
    return stay


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as e:
        raise ToolError(f"{field} must be an ISO date YYYY-MM-DD, got {value!r}.") from e


def _nights(check_in: date, check_out: date) -> list[str]:
    return [(check_in + timedelta(days=i)).isoformat() for i in range((check_out - check_in).days)]


def check_availability(id: str, check_in: str, check_out: str, *, today: date | None = None) -> dict[str, Any]:
    stay = get_stay(id, today=today)
    ci, co = _parse_date(check_in, "check_in"), _parse_date(check_out, "check_out")
    if co <= ci:
        raise ToolError("check_out must be after check_in.")
    if ci < (today or date.today()):
        raise ToolError("check_in is in the past.")
    nights = _nights(ci, co)
    clashes = [d for d in nights if d in set(stay["blocked"])]
    rate = stay["pricePerNight"]
    subtotal = rate * len(nights)
    cleaning = stay["cleaningFee"]
    gst = round((subtotal + cleaning) * GST_RATE)
    lines = [
        {"label": f"₹{rate:,} × {len(nights)} night{'s' if len(nights) != 1 else ''}", "amount": subtotal},
        {"label": "Cleaning fee", "amount": cleaning},
        {"label": "GST (12%)", "amount": gst},
    ]
    return {
        "id": stay["id"],
        "name": stay["name"],
        "check_in": ci.isoformat(),
        "check_out": co.isoformat(),
        "available": not clashes,
        "conflicts": clashes,
        "blocked": stay["blocked"],
        "nights": len(nights),
        "price_lines": lines,
        "total": subtotal + cleaning + gst,
        "currency": CURRENCY,
        "maxGuests": stay["maxGuests"],
    }


def booking_code(*parts: Any) -> str:
    """Deterministic code like ``WND-7K2Q9`` from the booking details."""
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return "WND-" + "".join(_CODE_ALPHABET[b % len(_CODE_ALPHABET)] for b in digest[:5])


def create_booking(
    id: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int = 0,
    name: str | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    quote = check_availability(id, check_in, check_out, today=today)
    if not quote["available"]:
        raise ToolError(f"Not available: {', '.join(quote['conflicts'])} already booked. Offer other dates.")
    adults, children = int(adults), int(children or 0)
    if adults < 1:
        raise ToolError("At least one adult is required.")
    guests = adults + children
    if guests > quote["maxGuests"]:
        raise ToolError(f"This stay sleeps at most {quote['maxGuests']} guests; got {guests}.")
    stay = get_stay(id, today=today)
    return {
        "code": booking_code(id, quote["check_in"], quote["check_out"], adults, children, name or ""),
        "status": "confirmed",
        "stayName": stay["name"],
        "location": stay["location"],
        "image": stay["image"],
        "checkIn": quote["check_in"],
        "checkOut": quote["check_out"],
        "nights": quote["nights"],
        "guests": guests,
        "adults": adults,
        "children": children,
        "guestName": name,
        "total": quote["total"],
        "currency": CURRENCY,
    }


# ─── OpenAI-format tool schemas ──────────────────────────────────────────────

def _fn(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}}


_ID = {"type": "string", "description": "Stay id from search_stays, e.g. 'manali-canopy-treehouse'."}
_DATE = {"type": "string", "description": "ISO date YYYY-MM-DD."}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn("search_stays", "Search Wander's stays across India. All filters optional; call with no arguments to list everything.", {
        "query": {"type": "string", "description": "Free text, e.g. 'treehouse', 'houseboat kerala', 'desert dome'."},
        "region": {"type": "string", "description": "Himalayas, Desert, Kerala, Kashmir, Western Ghats, Coast, or a state/town name."},
        "max_price": {"type": "integer", "description": "Maximum price per night in INR."},
        "guests": {"type": "integer", "description": "Total guests the stay must sleep."},
    }, []),
    _fn("get_stay", "Full details of one stay: images, description, amenities, blocked dates, cleaning fee.",
        {"id": _ID}, ["id"]),
    _fn("check_availability", "Check dates for a stay and price them (nightly total, cleaning fee, 12% GST, total in INR).",
        {"id": _ID, "check_in": _DATE, "check_out": _DATE}, ["id", "check_in", "check_out"]),
    _fn("create_booking", "Book a stay. Only call after the user explicitly confirms the quoted price.", {
        "id": _ID, "check_in": _DATE, "check_out": _DATE,
        "adults": {"type": "integer", "minimum": 1},
        "children": {"type": "integer", "minimum": 0},
        "name": {"type": "string", "description": "Lead guest name, if given."},
    }, ["id", "check_in", "check_out", "adults"]),
]

TOOLS: dict[str, Callable[..., Any]] = {
    "search_stays": search_stays,
    "get_stay": get_stay,
    "check_availability": check_availability,
    "create_booking": create_booking,
}


def run_tool(name: str, arguments: str | dict[str, Any] | None, *, today: date | None = None) -> str:
    """Execute a tool call and return its JSON result. Errors come back as ``{"error": ...}``
    so the model can recover instead of the run failing."""
    fn = TOOLS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool {name!r}. Available: {', '.join(TOOLS)}."})
    try:
        args = json.loads(arguments or "{}") if isinstance(arguments, str) else dict(arguments or {})
        if not isinstance(args, dict):
            raise ToolError("Tool arguments must be a JSON object.")
        args = {k: v for k, v in args.items() if v is not None}
        return json.dumps(fn(**args, today=today), ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Arguments are not valid JSON: {e}"})
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
    except ToolError as e:
        return json.dumps({"error": str(e)})
