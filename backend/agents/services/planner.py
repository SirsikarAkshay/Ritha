"""
Outfit-planner agent: multi-day / multi-city trip outfit plans.
"""

from agents.services._common import _get_weather, _has_mistral, _wardrobe_for_user

# ── Trip Outfit Planner ───────────────────────────────────────────────────────


def run_outfit_planner(user, input_data: dict) -> dict:
    """
    Generate a per-day outfit plan for a trip.
    Input: trip_id OR (start_date, end_date, destination, activities)
    """
    import datetime as dt

    from ritha.services.weather import get_weather_for_location

    trip_id = input_data.get("trip_id")
    activities = input_data.get("activities", [])

    if trip_id:
        from itinerary.models import Trip

        try:
            trip = Trip.objects.get(id=trip_id, user=user)
            start = trip.start_date
            end = trip.end_date
            destination = trip.destination
        except Trip.DoesNotExist:
            return {"status": "error", "message": f"Trip {trip_id} not found."}
    else:
        try:
            sd = input_data.get("start_date", "")
            ed = input_data.get("end_date", "")
            start = sd if isinstance(sd, dt.date) else dt.date.fromisoformat(sd)
            end = ed if isinstance(ed, dt.date) else dt.date.fromisoformat(ed)
            destination = input_data.get("destination", "")
        except (ValueError, TypeError):
            return {"status": "error", "message": "Provide trip_id or start_date/end_date/destination."}

    wardrobe = _wardrobe_for_user(user)
    if not wardrobe:
        return {"status": "no_wardrobe", "message": "Add items to your wardrobe first."}

    # Fetch weather for the trip destination (first day as proxy)
    weather = get_weather_for_location(destination, start) if destination else _get_weather({})

    days_count = (end - start).days + 1

    if _has_mistral():
        return _outfit_planner_mistral(wardrobe, start, end, destination, activities, weather)

    # ── Stub: rotate wardrobe items across days ───────────────────────────────
    day_plans = []
    tops = [i for i in wardrobe if i["category"] == "top"]
    bottoms = [i for i in wardrobe if i["category"] == "bottom"]
    outerwear = [i for i in wardrobe if i["category"] == "outerwear"]
    footwear = [i for i in wardrobe if i["category"] == "footwear"]
    activewear = [i for i in wardrobe if i["category"] == "activewear"]

    for i in range(days_count):
        date = start + dt.timedelta(days=i)
        day_items = []
        if tops:
            day_items.append(tops[i % len(tops)])
        if bottoms:
            day_items.append(bottoms[i % len(bottoms)])
        if outerwear and weather.get("is_cold"):
            day_items.append(outerwear[i % len(outerwear)])
        if footwear:
            day_items.append(footwear[i % len(footwear)])
        # Add activewear on alternating days if available
        if activewear and i % 2 == 0:
            day_items.append(activewear[i % len(activewear)])

        day_plans.append(
            {
                "date": date.isoformat(),
                "day": i + 1,
                "item_ids": [item["id"] for item in day_items],
                "items": day_items,
            }
        )

    # Deduplicate packing list (unique item IDs across all days)
    all_ids = list({item_id for day in day_plans for item_id in day["item_ids"]})
    all_items = [i for i in wardrobe if i["id"] in all_ids]
    weight = sum(i.get("weight_grams") or 0 for i in all_items)

    return {
        "status": "stub",
        "destination": destination,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": days_count,
        "weather_preview": weather,
        "day_plans": day_plans,
        "packing_list_ids": all_ids,
        "estimated_weight_grams": weight,
        "notes": f"Mix-and-match plan for {days_count} days in {destination}. Estimated bag weight: {weight}g.",
    }


def _outfit_planner_mistral(wardrobe, start, end, destination, activities, weather) -> dict:
    from ritha.services.mistral_client import chat_json

    days_count = (end - start).days + 1
    prompt = f"""You are Ritha, an expert travel stylist. Create a day-by-day outfit plan
for a {days_count}-day trip to {destination}.

Trip dates  : {start.isoformat()} to {end.isoformat()}
Activities  : {activities}
Weather     : {weather}
Wardrobe    : {wardrobe}

Rules:
- Only use item IDs from the wardrobe above
- Apply the 5-4-3-2-1 capsule logic (pack once, mix and match daily)
- Vary outfits each day
- Account for weather (cold/rain means include outerwear)
- Give each day a short note

Return JSON:
{{
  "day_plans": [{{"date": "YYYY-MM-DD", "day": 1, "item_ids": [1,2,3], "notes": "..."}}],
  "packing_list_ids": [1, 2, 3],
  "estimated_weight_grams": 0,
  "notes": "overall trip summary"
}}"""
    result = chat_json(prompt)
    result["status"] = "ai"
    result["destination"] = destination
    result["start_date"] = start.isoformat()
    result["end_date"] = end.isoformat()
    result["days"] = days_count
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 6. SMART RECOMMEND  (unified: ML + Weather + Cultural AI)
# ─────────────────────────────────────────────────────────────────────────────


def _merge_wardrobe_across_cities(cities: list, results: list) -> list:
    """
    Deduplicate wardrobe matches across multiple city recommendations.
    Returns a flat list where each item appears once with a `suitable_cities` list.
    """
    item_map = {}  # item_id -> {match data + suitable_cities}

    for city, rec in zip(cities, results, strict=False):
        matches = rec.get("wardrobe_matches") or []
        # Also collect from per-day plans
        for day in rec.get("days") or []:
            matches.extend(day.get("wardrobe_matches") or [])
        for m in matches:
            item = m.get("item") or {}
            item_id = item.get("id")
            if not item_id:
                continue
            if item_id in item_map:
                if city not in item_map[item_id]["suitable_cities"]:
                    item_map[item_id]["suitable_cities"].append(city)
            else:
                item_map[item_id] = {
                    "item": item,
                    "role": m.get("role", ""),
                    "ideal_category": m.get("ideal_category", ""),
                    "reason": m.get("reason", ""),
                    "in_wardrobe": True,
                    "suitable_cities": [city],
                }

    return list(item_map.values())
