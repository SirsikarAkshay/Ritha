"""
Weekly-looks agent: a week of non-repeating daily outfits.
"""

import datetime

from agents.services._common import _has_mistral, _wardrobe_for_user

# ── Weekly Looks ─────────────────────────────────────────────────────────────


def run_weekly_looks(user, input_data: dict) -> dict:
    """
    Generate 7 days of outfits in one pass.
    Tracks used items across days so outfits stay unique.
    Returns a list of per-day results with weather, events, and outfit.
    """
    from itinerary.models import CalendarEvent
    from outfits.models import OutfitItem, OutfitRecommendation
    from ritha.services.event_classifier import dominant_formality
    from ritha.services.weather import _fallback, get_weather_forecast
    from wardrobe.models import ClothingItem

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=6)

    if "weather" not in input_data and "location" not in input_data and "lat" not in input_data:
        if user.location_name:
            input_data = {**input_data, "location": user.location_name}
        elif user.location_lat and user.location_lon:
            input_data = {**input_data, "lat": user.location_lat, "lon": user.location_lon}

    location = input_data.get("location", "")
    forecasts = []
    if location:
        forecasts = get_weather_forecast(location, today, end_date)
    elif "lat" in input_data and "lon" in input_data:
        from ritha.services.weather import get_weather

        for i in range(7):
            d = today + datetime.timedelta(days=i)
            forecasts.append(get_weather(input_data["lat"], input_data["lon"], d))
    if len(forecasts) < 7:
        for i in range(len(forecasts), 7):
            d = today + datetime.timedelta(days=i)
            forecasts.append(_fallback("No location", d))

    wardrobe = _wardrobe_for_user(user)
    if not wardrobe:
        return {
            "status": "no_wardrobe",
            "message": "Add items to your wardrobe to get weekly looks.",
            "days": [],
        }

    week_events = list(
        CalendarEvent.objects.filter(
            user=user,
            start_time__date__gte=today,
            start_time__date__lte=end_date,
        )
        .exclude(raw_data__is_duplicate=True)
        .values(
            "id",
            "title",
            "event_type",
            "formality",
            "start_time",
            "end_time",
            "location",
        )
    )

    event_objs_all = list(
        CalendarEvent.objects.filter(
            user=user,
            start_time__date__gte=today,
            start_time__date__lte=end_date,
        ).exclude(raw_data__is_duplicate=True)
    )

    used_item_ids = set()
    days_output = []

    for day_idx in range(7):
        day_date = today + datetime.timedelta(days=day_idx)
        weather = forecasts[day_idx]
        day_events = [e for e in week_events if str(e["start_time"].date()) == day_date.isoformat()]
        day_event_objs = [e for e in event_objs_all if e.start_time.date() == day_date]
        required_formality = dominant_formality(day_event_objs)

        if _has_mistral():
            day_output = _weekly_day_mistral(
                user,
                wardrobe,
                day_events,
                weather,
                required_formality,
                day_date,
                used_item_ids,
                day_idx,
            )
        else:
            day_output = _weekly_day_stub(
                wardrobe,
                weather,
                required_formality,
                used_item_ids,
                day_idx,
            )

        new_ids = set(day_output.get("item_ids", []))
        used_item_ids |= new_ids

        rec, _created = OutfitRecommendation.objects.get_or_create(
            user=user,
            date=day_date,
            source="daily",
            defaults={"notes": day_output.get("notes", ""), "weather_snapshot": weather},
        )
        if not _created:
            rec.notes = day_output.get("notes", "")
            rec.weather_snapshot = weather
            rec.accepted = None
            rec.save(update_fields=["notes", "weather_snapshot", "accepted"])

        item_ids = day_output.get("item_ids", [])
        if item_ids:
            rec.outfititem_set.all().delete()
            items = ClothingItem.objects.filter(id__in=item_ids, user=user)
            OutfitItem.objects.bulk_create([OutfitItem(outfit=rec, clothing_item=item, role="main") for item in items])

        days_output.append(
            {
                "date": day_date.isoformat(),
                "day_label": day_date.strftime("%A"),
                "weather": weather,
                "events": day_events,
                "required_formality": required_formality,
                "item_ids": item_ids,
                "notes": day_output.get("notes", ""),
                "recommendation_id": rec.id,
            }
        )

    return {"status": "ok", "days": days_output}


def _weekly_day_stub(wardrobe, weather, required_formality, used_item_ids, day_idx) -> dict:
    """Pick items for one day, avoiding already-used items."""
    is_cold = weather.get("is_cold", False)
    is_hot = weather.get("is_hot", False)
    is_raining = weather.get("is_raining", False)
    season_hint = "winter" if is_cold else ("summer" if is_hot else "all")

    matched = [i for i in wardrobe if i["formality"] == required_formality]
    if not matched:
        matched = wardrobe

    seasonal = [i for i in matched if i["season"] in (season_hint, "all")]
    pool = seasonal or matched

    fresh = [i for i in pool if i["id"] not in used_item_ids]
    if len(fresh) < 2:
        fresh = pool

    CATEGORY_SLOTS = ["top", "bottom", "outerwear", "footwear", "accessory"]
    if day_idx % 3 == 1:
        CATEGORY_SLOTS = ["dress", "outerwear", "footwear", "accessory"]

    picks = []
    seen_cats = set()
    for cat in CATEGORY_SLOTS:
        candidates = [i for i in fresh if i["category"] == cat and i["id"] not in {p["id"] for p in picks}]
        if not candidates:
            candidates = [i for i in pool if i["category"] == cat and i["id"] not in {p["id"] for p in picks}]
        if candidates:
            candidates.sort(key=lambda i: (i["id"] in used_item_ids, i.get("times_worn", 0) or 0))
            picks.append(candidates[0])
            seen_cats.add(cat)
        if len(picks) >= 4:
            break

    if len(picks) < 2:
        for item in fresh:
            if item["category"] not in seen_cats:
                picks.append(item)
                seen_cats.add(item["category"])
            if len(picks) >= 3:
                break

    if is_cold and not any(p["category"] == "outerwear" for p in picks):
        outer = [i for i in pool if i["category"] == "outerwear"]
        if outer:
            outer.sort(key=lambda i: (i["id"] in used_item_ids,))
            picks.append(outer[0])

    day_name = (datetime.date.today() + datetime.timedelta(days=day_idx)).strftime("%A")
    notes = f"{day_name}: {required_formality} day"
    if is_cold:
        notes += " — cold, layers recommended"
    elif is_hot:
        notes += " — warm, light fabrics"
    if is_raining:
        notes += ". Rain expected, grab waterproof!"

    return {"item_ids": [p["id"] for p in picks], "notes": notes}


def _weekly_day_mistral(user, wardrobe, events, weather, required_formality, day_date, used_item_ids, day_idx) -> dict:
    from ritha.services.mistral_client import chat_json

    avoid_str = ", ".join(str(i) for i in used_item_ids) if used_item_ids else "none"
    prompt = f"""You are Ritha, a personal AI stylist. Pick the best outfit for ONE day.

Date       : {day_date.isoformat()} ({day_date.strftime("%A")})
Weather    : {weather}
Formality  : {required_formality}
Calendar   : {events}
Wardrobe   : {wardrobe}

IMPORTANT — this is day {day_idx + 1} of a 7-day weekly plan.
Items already used on earlier days (AVOID reusing): [{avoid_str}]

Rules:
- Only use item IDs from the wardrobe list
- Pick 2-4 items across different categories (top, bottom, outerwear, footwear)
- AVOID items already used on earlier days — maximize variety
- If wardrobe is small, you may reuse footwear but try to vary tops/bottoms
- Match weather and formality
- Give a concise, friendly note (1-2 sentences)

Return JSON: {{"item_ids": [1, 2, 3], "notes": "..."}}"""
    try:
        result = chat_json(prompt)
        ids = result.get("item_ids", [])
        valid_ids = {i["id"] for i in wardrobe}
        result["item_ids"] = [i for i in ids if i in valid_ids]
        return result
    except Exception:
        return _weekly_day_stub(wardrobe, weather, required_formality, used_item_ids, day_idx)
