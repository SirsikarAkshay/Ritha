"""
Conflict-detector agent: flags calendar/weather/wardrobe clashes for a day.
"""

from agents.services._common import _get_weather, _today_str

# ── Conflict Detector ─────────────────────────────────────────────────────────


def run_conflict_detector(user, input_data: dict) -> dict:
    from itinerary.models import CalendarEvent

    raw_date = input_data.get("date", None)
    if hasattr(raw_date, "isoformat"):
        date = raw_date.isoformat()
    else:
        date = raw_date or _today_str()
    weather = _get_weather({**input_data, "weather": input_data.get("weather", {})})

    events = list(CalendarEvent.objects.filter(user=user, start_time__date=date))
    conflicts = []

    rain_chance = weather.get("precipitation_probability", 0)
    temp_c = weather.get("temp_c", 15)
    is_raining = weather.get("is_raining", False)

    for event in events:
        etype = event.event_type

        # Outdoor workout + rain
        if etype == "workout" and rain_chance > 70:
            conflicts.append(
                {
                    "type": "weather_activity",
                    "event": event.title,
                    "message": f"{rain_chance}% chance of rain — consider indoor gear for your workout.",
                    "severity": "warning",
                }
            )

        # Travel day + heavy rain or storm
        if etype == "travel" and weather.get("wmo_code", 0) in {65, 80, 81, 82, 95, 96, 99}:
            conflicts.append(
                {
                    "type": "weather_travel",
                    "event": event.title,
                    "message": "Severe weather forecast on your travel day — pack a heavy waterproof and check transport updates.",
                    "severity": "warning",
                }
            )

        # Formal event + very cold
        if etype in ("external_meeting", "wedding", "interview") and temp_c < 5:
            conflicts.append(
                {
                    "type": "weather_formality",
                    "event": event.title,
                    "message": f"It'll be {temp_c}°C — make sure your smart outfit includes a warm coat.",
                    "severity": "info",
                }
            )

        # Social dinner + heavy rain
        if etype == "social" and is_raining:
            conflicts.append(
                {
                    "type": "weather_social",
                    "event": event.title,
                    "message": "Rain expected — consider whether open-toe shoes or suede items are a good idea tonight.",
                    "severity": "info",
                }
            )

    return {
        "date": date,
        "weather": weather,
        "conflicts": conflicts,
        "events_checked": len(events),
    }
