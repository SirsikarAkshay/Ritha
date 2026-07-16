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
import re

from ml.categories import estimate_packed_volume_liters

from ritha.services.places import fallback_highlights
from ritha.services.weather import get_weather_for_location

# Guests have no home city yet, so we assume a warm home climate consistent with
# the "standard South-India capsule" the preview is framed around. The visitor
# changes their real home city right after signing up (see the frontend
# assumption note). Overridable per-request via `home_city` / `home_temp_c`.
_ASSUMED_HOME = {"city": "Bengaluru", "temp_c": 26.0}

# A carry-on is the reference bag for the packing gauge (matches BAG_TYPE_LITERS).
_BAG_CAPACITY_L = 40

# Only surface the "your closet's built for X°C" headline once the gap is real.
_GAP_HEADLINE_THRESHOLD_C = 6

# Per-bucket "gap" cue — the one-line reason your everyday closet falls short.
_GAP_CUE_BY_BUCKET = {
    "cold": ("🧥", "You have no real cold-weather layers"),
    "cool": ("🧥", "Your closet's light on warm layers"),
    "mild": ("🧳", "One packable layer covers the day-night swing"),
    "warm": ("👕", "You'll want breathable, sweat-friendly fabrics"),
}

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


def _qty(name: str) -> int:
    """Pull the quantity out of a capsule line like 'Wool sweater ×2' → 2."""
    m = re.search(r"[×xX]\s*(\d+)", name or "")
    return int(m.group(1)) if m else 1


def _short_place(destination: str) -> str:
    """'Tokyo, Japan' → 'Tokyo' — the label for the gap headline."""
    return (destination or "there").split(",")[0].strip() or "there"


def _weather_gap(dest_temp_c, home: dict, dest_label: str) -> dict | None:
    """Home-vs-destination temperature comparison for the 'built for X°C' hook."""
    try:
        dest_t = round(float(dest_temp_c))
        home_t = round(float(home["temp_c"]))
    except (TypeError, ValueError, KeyError):
        return None
    delta = dest_t - home_t  # negative → destination is colder
    gap = {
        "home_city": home.get("city"),
        "home_temp_c": home_t,
        "dest_temp_c": dest_t,
        "delta_c": delta,
        "colder": delta < 0,
        "assumed_home": bool(home.get("assumed")),
        "headline": None,
    }
    if abs(delta) >= _GAP_HEADLINE_THRESHOLD_C:
        gap["headline"] = f"Your closet's built for {home_t}°C. {dest_label} isn't."
    return gap


def _seasonal_cue(dt: datetime.date | None, bucket: str) -> dict | None:
    """A month-tagged packing tip, e.g. 'Layer up for chilly April mornings'."""
    if not dt:
        return None
    month = dt.strftime("%B")
    if bucket in ("cold", "cool"):
        return {"icon": "🌅", "text": f"Layer up for chilly {month} mornings", "tag": f"{month} tip"}
    if bucket == "warm":
        return {"icon": "🧴", "text": f"Pack sun protection for the {month} heat", "tag": f"{month} tip"}
    return {"icon": "🌤", "text": f"Mild {month} days, cooler evenings — pack a layer", "tag": f"{month} tip"}


def _cues(bucket: str, dress_code: list[str], dt: datetime.date | None) -> list[dict]:
    """Three tagged cue cards: the closet gap, the local dress code, a seasonal tip."""
    cues: list[dict] = []
    icon, text = _GAP_CUE_BY_BUCKET.get(bucket, _GAP_CUE_BY_BUCKET["mild"])
    cues.append({"icon": icon, "text": text, "tag": "gap"})
    if dress_code:
        cues.append({"icon": "👟", "text": dress_code[0], "tag": "dress code"})
    seasonal = _seasonal_cue(dt, bucket)
    if seasonal:
        cues.append(seasonal)
    return cues[:3]


def _packing(capsule: list[dict]) -> dict:
    """Piece count + packed volume + % of a 40 L carry-on, for the guest gauge."""
    pieces, volume = 0, 0.0
    for it in capsule:
        q = _qty(it.get("name", ""))
        # Pass the item name as the "material" so bulk hints (wool, denim, down…)
        # in the label bump the estimate — same estimator the packing engine uses.
        volume += estimate_packed_volume_liters(it.get("category", "other"), it.get("name", "")) * q
        pieces += q
    volume = round(volume, 1)
    percent = round(100 * volume / _BAG_CAPACITY_L) if _BAG_CAPACITY_L else 0
    return {
        "piece_count": pieces,
        "line_count": len(capsule),
        "volume_l": volume,
        "bag_capacity_l": _BAG_CAPACITY_L,
        "percent_of_bag": percent,
        "note": f"{pieces} pieces travel fine · {volume} L",
    }


def trip_insights(
    destination: str,
    date=None,
    gender: str = "women",
    weather: dict | None = None,
    home_city: str | None = None,
    home_temp_c=None,
) -> dict:
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

    # 5. Weather gap — home-vs-destination temperature delta + tagged cue cards.
    home = dict(_ASSUMED_HOME)
    home["assumed"] = True
    if home_city:
        home["city"], home["assumed"] = home_city.strip() or home["city"], False
    if home_temp_c is not None:
        try:
            home["temp_c"], home["assumed"] = float(home_temp_c), False
        except (TypeError, ValueError):
            pass
    parsed_date = _parse_date(date)
    weather_gap = _weather_gap(weather.get("temp_c"), home, _short_place(destination))
    cues = _cues(bucket, dress_code, parsed_date)

    # 6. Packing gauge — piece count + packed volume + % of a 40 L carry-on.
    packing = _packing(capsule)

    return {
        "destination": destination,
        "date": date if isinstance(date, str) else (date.isoformat() if isinstance(date, datetime.date) else None),
        "weather": weather,
        "home": home,
        "weather_gap": weather_gap,
        "cues": cues,
        "dress_code": dress_code,
        "places": places,
        "capsule": capsule,
        "capsule_note": (
            f"Based on a standard capsule for {destination or 'this destination'}'s "
            f"{_bucket_word(bucket)} weather — personalise it with your own wardrobe in one tap."
        ),
        "packing": packing,
        "gaps": gaps,
        "is_preview": True,
    }
