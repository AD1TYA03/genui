"""Mock inventory for Wander: ten extraordinary stays across India.

Every image URL below was checked to return HTTP 200 from images.unsplash.com and to show
what it claims to (treehouse, dunes, houseboat, tent, cottage, ...). The agent may only put
these URLs in the UI, never ones it makes up.

Blocked dates are generated relative to today (offsets in days), so the calendar always has
some unavailable nights in the next 60 days.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

GST_RATE = 0.12  # applied to nightly total + cleaning fee


def img(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1200&q=80"


def _blocked(*offsets: int, today: date | None = None) -> list[str]:
    base = today or date.today()
    return sorted((base + timedelta(days=o)).isoformat() for o in offsets)


def _span(start: int, length: int) -> list[int]:
    return list(range(start, start + length))


_STAYS: list[dict[str, Any]] = [
    {
        "id": "manali-canopy-treehouse",
        "name": "Canopy Treehouse",
        "location": "Old Manali, Himachal Pradesh",
        "region": "Himalayas",
        "photos": ["1618767689160-da3fb810aad7", "1586375300773-8384e3e4916f",
                   "1609920658906-8223bd289001", "1593181629936-11c609b8db9b"],
        "pricePerNight": 8900,
        "cleaningFee": 1200,
        "rating": 4.92,
        "reviews": 318,
        "maxGuests": 3,
        "tags": ["treehouse", "mountains", "forest", "romantic"],
        "description": (
            "A cedar-and-glass cabin hung twelve metres up in a stand of old deodars above Old "
            "Manali. Wake to the Beas roaring below and the Pir Panjal turning pink at dawn, then "
            "cross a swaying rope bridge to breakfast. At night the canopy goes quiet except for "
            "owls and the wood stove."
        ),
        "amenities": ["Wood-burning stove", "Rope-bridge deck", "Himalayan breakfast",
                      "Heated blankets", "Wi-Fi", "Guided Hampta walks"],
        "blocked": _span(3, 3) + _span(18, 2) + [31, 32, 45],
    },
    {
        "id": "jaisalmer-stargazer-dome",
        "name": "Sam Dunes Stargazer Dome",
        "location": "Sam Sand Dunes, Jaisalmer, Rajasthan",
        "region": "Desert",
        "photos": ["1517824806704-9040b037703b", "1473580044384-7ba9967e16a0",
                   "1542401886-65d6c61db217", "1599661046289-e31897846e41"],
        "pricePerNight": 12500,
        "cleaningFee": 1500,
        "rating": 4.88,
        "reviews": 204,
        "maxGuests": 2,
        "tags": ["dome", "desert", "stargazing", "glamping"],
        "description": (
            "A transparent geodesic dome pitched alone on the crest of the Thar dunes, 40 km from "
            "the golden fort. Dinner is laal maas cooked over dung-fire coals, followed by Manganiyar "
            "folk songs, then you fall asleep under the Milky Way with a telescope at the foot of "
            "the bed."
        ),
        "amenities": ["Star-view ceiling", "Telescope", "Camel safari at sunset",
                      "Private folk performance", "En-suite bath", "Air cooling"],
        "blocked": _span(5, 4) + _span(22, 3) + [40, 41],
    },
    {
        "id": "alleppey-kettuvallam",
        "name": "Vembanad Kettuvallam",
        "location": "Alleppey backwaters, Kerala",
        "region": "Kerala",
        "photos": ["1602216056096-3b40cc0c9944", "1593693397690-362cb9666fc2",
                   "1506461883276-594a12b11cf3", "1590050752117-238cb0fb12b1"],
        "pricePerNight": 15800,
        "cleaningFee": 2000,
        "rating": 4.95,
        "reviews": 412,
        "maxGuests": 4,
        "tags": ["houseboat", "backwaters", "family", "food"],
        "description": (
            "A hand-stitched jackwood and coir kettuvallam with two air-conditioned bedrooms and an "
            "open upper deck. Drift past paddy fields and toddy shops on Vembanad Lake while the "
            "onboard cook grills karimeen pollichathu, then moor in a quiet canal for the night."
        ),
        "amenities": ["Private chef", "Two bedrooms", "Upper sun deck", "Air conditioning",
                      "Canoe village tour", "Fishing gear"],
        "blocked": _span(1, 2) + _span(12, 4) + _span(36, 3),
    },
    {
        "id": "pangong-luxury-camp",
        "name": "Pangong Shore Glamp",
        "location": "Spangmik, Pangong Tso, Ladakh",
        "region": "Himalayas",
        "photos": ["1532339142463-fd0a8979791a", "1581793745862-99fde7fa73d2",
                   "1455763916899-e8b50eca9967", "1506905925346-21bda4d32df4"],
        "pricePerNight": 11200,
        "cleaningFee": 1000,
        "rating": 4.81,
        "reviews": 167,
        "maxGuests": 3,
        "tags": ["glamping", "lake", "high-altitude", "adventure"],
        "description": (
            "Insulated canvas suites at 4,250 m on the shore of Pangong Tso, the lake that shifts "
            "from turquoise to cobalt by the hour. Heated beds, butter tea at sunrise and the "
            "clearest night sky in India. Rates include oxygen support and a Changthang wildlife drive."
        ),
        "amenities": ["Heated beds", "Oxygen support", "Lake-view deck", "All meals",
                      "Wildlife drive", "Solar hot water"],
        "blocked": _span(7, 3) + _span(26, 5) + [50],
    },
    {
        "id": "coorg-estate-cottage",
        "name": "Bean & Mist Estate Cottage",
        "location": "Madikeri, Coorg, Karnataka",
        "region": "Western Ghats",
        "photos": ["1542718610-a1d656d1884c", "1470071459604-3b5ec3a7fe05",
                   "1447933601403-0c6688de566e", "1582719478250-c89cae4dc85b"],
        "pricePerNight": 7400,
        "cleaningFee": 900,
        "rating": 4.86,
        "reviews": 289,
        "maxGuests": 4,
        "tags": ["cottage", "coffee", "plantation", "family"],
        "description": (
            "A restored 1920s planter's cottage inside a working 80-acre arabica estate. Mornings "
            "start with a plantation walk and a cup roasted twenty metres from your verandah; "
            "evenings bring pandi curry, rain on a tiled roof and mist rolling in over the ghats."
        ),
        "amenities": ["Coffee estate tour", "Verandah with hammock", "Kodava home cooking",
                      "Fireplace", "Bird-watching trails", "Free parking"],
        "blocked": _span(2, 2) + _span(15, 3) + [29, 43, 44],
    },
    {
        "id": "kibber-mud-home",
        "name": "Kibber Mud-Brick Homestay",
        "location": "Kibber, Spiti Valley, Himachal Pradesh",
        "region": "Himalayas",
        "photos": ["1626621331169-5f34be280ed9", "1626621341517-bbf3d9990a23",
                   "1464822759023-fed622ff2c3b", "1615874959474-d609969a20ed"],
        "pricePerNight": 3600,
        "cleaningFee": 500,
        "rating": 4.97,
        "reviews": 141,
        "maxGuests": 4,
        "tags": ["mud home", "homestay", "snow leopard", "offbeat"],
        "description": (
            "A traditional sun-dried mud-brick home at 4,200 m, kept warm by thick walls and a "
            "bukhari stove. Your Spitian hosts cook thukpa and tsampa, and in winter the village "
            "trackers take you looking for snow leopards and ibex on the cliffs above Kibber."
        ),
        "amenities": ["Bukhari stove", "Home-cooked meals", "Snow leopard tracking",
                      "Rooftop for stargazing", "Monastery visit", "Hot-water bottles"],
        "blocked": _span(9, 2) + _span(20, 4) + [38],
    },
    {
        "id": "dal-lake-houseboat",
        "name": "Shikara House on Dal",
        "location": "Dal Lake, Srinagar, Kashmir",
        "region": "Kashmir",
        "photos": ["1595815771614-ade9d652a65d", "1590490360182-c33d57733427",
                   "1464822759023-fed622ff2c3b"],
        "pricePerNight": 9800,
        "cleaningFee": 1200,
        "rating": 4.84,
        "reviews": 376,
        "maxGuests": 4,
        "tags": ["houseboat", "lake", "heritage", "romantic"],
        "description": (
            "A carved walnut-wood houseboat from 1948, moored on the quiet side of Dal Lake with the "
            "Zabarwan range behind it. Kahwa is served on the front porch, a shikara takes you to the "
            "floating vegetable market at dawn, and the evening wazwan is cooked on board."
        ),
        "amenities": ["Shikara rides", "Walnut-wood interiors", "Kashmiri wazwan",
                      "Heated bedrooms", "Lake-view porch", "Wi-Fi"],
        "blocked": _span(4, 3) + _span(16, 2) + _span(33, 4),
    },
    {
        "id": "kasol-aframe",
        "name": "Parvati A-Frame",
        "location": "Kasol, Parvati Valley, Himachal Pradesh",
        "region": "Himalayas",
        "photos": ["1601918774946-25832a4be0d6", "1499696010180-025ef6e1a8f9",
                   "1441974231531-c6227db76b6e", "1448375240586-882707db888b"],
        "pricePerNight": 5900,
        "cleaningFee": 800,
        "rating": 4.79,
        "reviews": 233,
        "maxGuests": 2,
        "tags": ["cabin", "forest", "river", "workation"],
        "description": (
            "A black timber A-frame tucked into a pine forest a short walk from the Parvati river. "
            "Floor-to-ceiling glass faces the valley, there's a hammock under the trees and fast "
            "fibre for a slow-travel workation. Trailheads for Kheerganga start nearby."
        ),
        "amenities": ["Floor-to-ceiling windows", "Fibre Wi-Fi", "Hammock", "Kitchenette",
                      "River access", "Bonfire pit"],
        "blocked": _span(6, 2) + _span(24, 3) + [47, 48],
    },
    {
        "id": "gokarna-palm-huts",
        "name": "Paradise Cove Palm Huts",
        "location": "Paradise Beach, Gokarna, Karnataka",
        "region": "Coast",
        "photos": ["1563911302283-d2bc129e7570", "1512343879784-a960bf40e7f2",
                   "1611892440504-42a792e24d32", "1584132967334-10e028bd69f7"],
        "pricePerNight": 6800,
        "cleaningFee": 700,
        "rating": 4.83,
        "reviews": 198,
        "maxGuests": 3,
        "tags": ["beach", "huts", "pool", "yoga"],
        "description": (
            "Thatched palm-wood huts on a cove reachable only by boat or a cliff trail. A saltwater "
            "pool sits under the coconut palms, sunrise yoga happens on the deck and dinner is the "
            "day's catch grilled with Konkan spices, eaten with your feet in the sand."
        ),
        "amenities": ["Saltwater pool", "Sunrise yoga", "Beachfront", "Boat transfers",
                      "Seafood grill", "Outdoor shower"],
        "blocked": _span(3, 4) + _span(19, 2) + [35, 52],
    },
    {
        "id": "wayanad-bubble-dome",
        "name": "Wayanad Rainforest Dome",
        "location": "Vythiri, Wayanad, Kerala",
        "region": "Western Ghats",
        "photos": ["1521401830884-6c03c1c87ebb", "1596394516093-501ba68a0ba6",
                   "1578683010236-d716f9a3f461"],
        "pricePerNight": 10400,
        "cleaningFee": 1100,
        "rating": 4.9,
        "reviews": 156,
        "maxGuests": 2,
        "tags": ["dome", "treehouse", "rainforest", "romantic"],
        "description": (
            "A green geodesic dome on stilts in the Wayanad rainforest canopy, reached by a wooden "
            "stairway through the ferns. Lie in bed watching hornbills and giant squirrels, soak in "
            "the open-air deck tub, and fall asleep to the monsoon on the canvas."
        ),
        "amenities": ["Canopy deck", "Outdoor bathtub", "Plantation breakfast",
                      "Guided rainforest walk", "Ayurvedic massage", "Wi-Fi"],
        "blocked": _span(8, 3) + _span(28, 2) + [42, 55],
    },
]


def _public(stay: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """The stay as tools return it (contract shape plus a few booking-only fields)."""
    images = [img(p) for p in stay["photos"]]
    return {
        "id": stay["id"],
        "name": stay["name"],
        "location": stay["location"],
        "region": stay["region"],
        "image": images[0],
        "images": images,
        "pricePerNight": stay["pricePerNight"],
        "rating": stay["rating"],
        "reviews": stay["reviews"],
        "tags": list(stay["tags"]),
        "description": stay["description"],
        "amenities": list(stay["amenities"]),
        "maxGuests": stay["maxGuests"],
        "cleaningFee": stay["cleaningFee"],
        "blocked": _blocked(*stay["blocked"], today=today),
    }


def all_stays(today: date | None = None) -> list[dict[str, Any]]:
    return [_public(s, today) for s in _STAYS]


def find_stay(stay_id: str, today: date | None = None) -> dict[str, Any] | None:
    for s in _STAYS:
        if s["id"] == stay_id:
            return _public(s, today)
    return None


def all_image_urls() -> list[str]:
    return [img(p) for s in _STAYS for p in s["photos"]]
