"""Unauthenticated 'instant insight' for the destination-first onboarding hook.

Given only a destination (+ optional date), returns everything we can compute
WITHOUT a user or a wardrobe — so a visitor gets the "aha" before signing up:

    weather · cultural dress-code alerts · places to visit ·
    a standard packing capsule (clearly labelled) · gap analysis (what to buy/borrow)

The capsule is weather-driven and generic on purpose. It is explicitly labelled
so the visitor knows it isn't yet based on their own closet — see `capsule_note`.
Once they personalise (pick a home region / add items), the authenticated engine
takes over with their real wardrobe.

No Mistral / no torch / no DB writes — this path must always render fast.
"""

import datetime

from ritha.services.places import fallback_highlights
from ritha.services.weather import get_weather_for_location

# Weather-bucket → a compact, universally-useful packing capsule. Each item is a
# (category, name) the destination climate calls for — not culturally specific.
_CAPSULE_BY_BUCKET = {
    "cold": [
        ("outerwear", "Warm coat"),
        ("top", "Wool sweater ×2"),
        ("top", "Thermal base layer"),
        ("bottom", "Warm trousers / jeans"),
        ("footwear", "Closed boots"),
        ("accessory", "Scarf, gloves & beanie"),
    ],
    "cool": [
        ("outerwear", "Light jacket"),
        ("top", "Long-sleeve tops ×2"),
        ("top", "Cotton tee ×2"),
        ("bottom", "Jeans / chinos"),
        ("footwear", "Sneakers"),
        ("accessory", "Light scarf"),
    ],
    "mild": [
        ("top", "Shirts / tops ×3"),
        ("bottom", "Chinos / jeans"),
        ("outerwear", "Layer for the evenings"),
        ("footwear", "Comfortable walking shoes"),
        ("accessory", "Day bag"),
    ],
    "warm": [
        ("top", "Linen / cotton shirts ×3"),
        ("top", "Breathable tees"),
        ("bottom", "Shorts / light trousers"),
        ("dress", "Summer dress"),
        ("footwear", "Sandals"),
        ("accessory", "Sun hat & sunglasses"),
    ],
}

# The climate-critical pieces most people won't already own for a given trip —
# surfaced as "what you'll likely need to buy or borrow".
_GAPS_BY_BUCKET = {
    "cold": [
        ("Warm coat", "Nights drop below freezing — a light jacket won't cut it."),
        ("Closed boots", "Wet/cold streets; sandals and canvas shoes won't do."),
        ("Scarf, gloves & beanie", "The layers that make everything else warm enough."),
    ],
    "cool": [
        ("Light jacket", "Cool mornings and evenings need a shell you can shed."),
        ("Closed shoes", "Too cool for open sandals most of the day."),
    ],
    "mild": [
        ("A packable layer", "Evenings dip — one layer keeps the days versatile."),
    ],
    "warm": [
        ("Breathable footwear", "Humidity is relentless — sandals or mesh sneakers."),
        ("Sun protection", "Hat + sunglasses for long days outdoors."),
    ],
}


def _bucket(temp_c) -> str:
    try:
        t = float(temp_c)
    except (TypeError, ValueError):
        return "mild"
    if t < 9:
        return "cold"
    if t < 17:
        return "cool"
    if t < 25:
        return "mild"
    return "warm"


def _bucket_word(bucket: str) -> str:
    return {"cold": "cold", "cool": "cool", "mild": "mild", "warm": "warm & humid"}.get(bucket, "mild")


def _parse_date(value):
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _dress_code_alerts(places: list[dict]) -> list[str]:
    """Distil per-place clothing tips into a short list of destination dress-code alerts."""
    alerts, seen = [], set()
    for p in places:
        tip = (p.get("clothing_tip") or "").strip()
        if not tip:
            continue
        # Prioritise religious/formal spots — that's where dress codes bite.
        key = tip.lower()
        if key in seen:
            continue
        seen.add(key)
        if p.get("type") in {"religious", "temple", "mosque", "church", "shrine"} or p.get("formality") in {
            "smart",
            "formal",
        }:
            alerts.insert(0, tip)  # front of the list
        else:
            alerts.append(tip)
    return alerts[:4]


def trip_insights(destination: str, date=None, gender: str = "women", weather: dict | None = None) -> dict:
    """Return the unauthenticated instant-insight payload for a destination."""
    destination = (destination or "").strip()

    # 1. Weather (caller may inject `weather` to skip the network call — used in tests).
    if not weather:
        try:
            weather = get_weather_for_location(destination, _parse_date(date)) or {}
        except Exception:
            weather = {}

    bucket = _bucket(weather.get("temp_c"))

    # 2. Places + dress-code alerts (curated fallback — always renders, no Mistral).
    places = fallback_highlights(destination, limit=6)
    dress_code = _dress_code_alerts(places)

    # 3. Standard weather-driven packing capsule (clearly labelled, see capsule_note).
    capsule = [{"category": c, "name": n} for c, n in _CAPSULE_BY_BUCKET[bucket]]
    if weather.get("is_raining") or weather.get("is_wet"):
        capsule.append({"category": "outerwear", "name": "Packable rain shell"})

    # 4. Gap analysis — the climate-critical pieces to buy or borrow.
    gaps = [{"name": n, "why": w} for n, w in _GAPS_BY_BUCKET[bucket]]
    if weather.get("is_raining") or weather.get("is_wet"):
        gaps.append({"name": "Waterproof shell", "why": "Rain in the forecast — stay dry without bulk."})

    return {
        "destination": destination,
        "date": date if isinstance(date, str) else (date.isoformat() if isinstance(date, datetime.date) else None),
        "weather": weather,
        "dress_code": dress_code,
        "places": places,
        "capsule": capsule,
        "capsule_note": (
            f"Based on a standard capsule for {destination or 'this destination'}'s "
            f"{_bucket_word(bucket)} weather — personalise it with your own wardrobe in one tap."
        ),
        "gaps": gaps,
        "is_preview": True,
    }
