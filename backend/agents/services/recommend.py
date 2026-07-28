"""
Smart-recommend + place-outfit agents (thin wrappers over the destination engine).
"""

from agents.services.planner import _merge_wardrobe_across_cities


def run_smart_recommend(user, input_data: dict) -> dict:
    """
    Unified recommendation agent.  Combines the trained fashion ML model,
    live weather data, and Mistral-powered cultural intelligence to produce
    outfit recommendations.  Items found in the user's wardrobe are returned
    directly; gaps include shopping links.

    If `cities` (list[str]) is provided alongside `country`, runs a per-city
    recommendation in parallel and returns an aggregated multi-city response.
    """
    from concurrent.futures import ThreadPoolExecutor

    from ritha.services.recommendation_engine import recommend

    cities = [c for c in (input_data.get("cities") or []) if isinstance(c, str) and c.strip()]
    country = (input_data.get("country") or "").strip()

    if len(cities) > 1:

        def _run(city: str) -> dict:
            payload = dict(input_data)
            payload["destination"] = f"{city}, {country}" if country else city
            payload.pop("cities", None)
            return recommend(user, payload)

        with ThreadPoolExecutor(max_workers=min(4, len(cities))) as ex:
            results = list(ex.map(_run, cities))

        merged_wardrobe = _merge_wardrobe_across_cities(cities, results)

        return {
            "multi_city": True,
            "country": country,
            "cities": [{"city": c, "recommendation": r} for c, r in zip(cities, results, strict=False)],
            "wardrobe_summary": merged_wardrobe,
        }

    # Single-destination path (possibly with one city)
    if cities and not input_data.get("destination"):
        only = cities[0]
        input_data = dict(input_data)
        input_data["destination"] = f"{only}, {country}" if country else only

    return recommend(user, input_data)


# Dress-formality of a place → the occasion the engine understands.
_PLACE_FORMALITY_TO_OCCASION = {
    "casual": "casual",
    "casual_smart": "smart_casual",
    "smart": "business",
    "formal": "formal",
}
# Religious sites want modest, respectful dress regardless of stated formality.
_MODEST_PLACE_TYPES = {"religious", "temple", "mosque", "church", "shrine"}


def run_place_outfit(user, input_data: dict) -> dict:
    """Build an outfit for one specific place by reusing the recommendation engine.

    Maps the place's dress formality (and type) to an occasion, then asks the
    engine for wardrobe matches under that destination's weather + culture.
    """
    from ritha.services.recommendation_engine import recommend

    place = (input_data.get("place") or "").strip()
    destination = (input_data.get("destination") or "").strip() or place
    place_type = (input_data.get("place_type") or "").strip().lower()
    formality = input_data.get("formality") or "casual_smart"

    if place_type in _MODEST_PLACE_TYPES:
        occasion = "cultural_visit"
    else:
        occasion = _PLACE_FORMALITY_TO_OCCASION.get(formality, "smart_casual")

    payload = {"destination": destination, "occasion": occasion}
    raw_date = input_data.get("date")
    if raw_date is not None:
        payload["date"] = raw_date.isoformat() if hasattr(raw_date, "isoformat") else raw_date
    for key in ("lat", "lon", "location", "weather"):
        if input_data.get(key) is not None:
            payload[key] = input_data[key]

    rec = recommend(user, payload)
    outfit = rec.get("outfit", {}) or {}
    return {
        "status": "ok",
        "place": place,
        "destination": destination,
        "occasion": occasion,
        "clothing_tip": input_data.get("clothing_tip", "") or "",
        "wardrobe_matches": rec.get("wardrobe_matches", []),
        "outfit": outfit,
        "notes": outfit.get("notes", ""),
        "shopping_suggestions": rec.get("shopping_suggestions", []),
        "weather": rec.get("weather", {}),
    }
