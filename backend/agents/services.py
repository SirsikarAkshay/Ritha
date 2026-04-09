"""
Agent service layer.
Each function takes a User + input_data dict and returns an output_data dict.
Weather is fetched automatically via Open-Meteo (no key needed).
Mistral AI calls are activated once MISTRAL_API_KEY is set.
"""
import datetime
from django.conf import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_mistral() -> bool:
    from arokah.services.mistral_client import _has_mistral as _check
    return _check()


def _today_str() -> str:
    return datetime.date.today().isoformat()


def _get_weather(input_data: dict) -> dict:
    """
    Return a WeatherSnapshot.
    Priority:
      1. weather dict passed directly in input_data (test / override)
      2. lat/lon from input_data  → Open-Meteo by coordinates
      3. location string          → geocode then Open-Meteo
      4. fallback to default snapshot
    """
    from arokah.services.weather import get_weather, get_weather_for_location, _fallback

    if 'weather' in input_data and isinstance(input_data['weather'], dict):
        snap = input_data['weather']
        if snap:  # allow empty dict to trigger auto-fetch
            return snap

    if 'lat' in input_data and 'lon' in input_data:
        return get_weather(input_data['lat'], input_data['lon'])

    if 'location' in input_data:
        return get_weather_for_location(input_data['location'])

    return _fallback('No location provided', datetime.date.today())


def _wardrobe_for_user(user):
    from wardrobe.models import ClothingItem
    return list(ClothingItem.objects.filter(user=user, is_active=True).values(
        'id', 'name', 'category', 'formality', 'season', 'colors', 'tags', 'weight_grams'))


def _today_events(user):
    from itinerary.models import CalendarEvent
    today = datetime.date.today()
    return list(CalendarEvent.objects.filter(user=user, start_time__date=today).values(
        'id', 'title', 'event_type', 'formality', 'start_time', 'end_time', 'location'))


# ── Daily Look ────────────────────────────────────────────────────────────────

def run_daily_look(user, input_data: dict) -> dict:
    """
    Generate today's outfit and persist an OutfitRecommendation record.
    """
    from outfits.models import OutfitRecommendation, OutfitItem
    from wardrobe.models import ClothingItem
    from arokah.services.event_classifier import dominant_formality
    from itinerary.models import CalendarEvent

    # Allow cron jobs to generate looks for a specific date
    _date_str = input_data.get('_target_date')
    today = datetime.date.fromisoformat(_date_str) if _date_str else datetime.date.today()
    # Use user's saved location if not overridden in input_data
    if 'weather' not in input_data and 'location' not in input_data and 'lat' not in input_data:
        if user.location_name:
            input_data = {**input_data, 'location': user.location_name}
        elif user.location_lat and user.location_lon:
            input_data = {**input_data, 'lat': user.location_lat, 'lon': user.location_lon}
    weather  = _get_weather(input_data)
    wardrobe = _wardrobe_for_user(user)
    events   = _today_events(user)

    if not wardrobe:
        return {
            'status':  'no_wardrobe',
            'message': 'Add at least one item to your wardrobe to get a daily look.',
            'weather': weather,
        }

    # Determine required formality from today's calendar
    event_objs = CalendarEvent.objects.filter(user=user, start_time__date=today)
    required_formality = dominant_formality(list(event_objs))

    if _has_mistral():
        output = _daily_look_mistral(user, wardrobe, events, weather, required_formality)
    else:
        output = _daily_look_stub(wardrobe, weather, required_formality)

    # Persist OutfitRecommendation
    rec, _created = OutfitRecommendation.objects.get_or_create(
        user=user, date=today, source='daily',
        defaults={
            'notes':            output.get('notes', ''),
            'weather_snapshot': weather,
        }
    )
    if not _created:
        rec.notes            = output.get('notes', '')
        rec.weather_snapshot = weather
        rec.save()

    # Attach clothing items
    item_ids = output.get('item_ids', [])
    if item_ids:
        rec.outfititem_set.all().delete()
        items = ClothingItem.objects.filter(id__in=item_ids, user=user)
        OutfitItem.objects.bulk_create([
            OutfitItem(outfit=rec, clothing_item=item, role='main') for item in items
        ])

    output['recommendation_id'] = rec.id
    output['required_formality'] = required_formality
    output['weather']            = weather
    return output


def _daily_look_stub(wardrobe, weather, required_formality) -> dict:
    """Pick best-matching items without calling OpenAI."""
    is_cold   = weather.get('is_cold', False)
    is_hot    = weather.get('is_hot', False)
    is_raining = weather.get('is_raining', False)

    season_hint = 'winter' if is_cold else ('summer' if is_hot else 'all')

    # Filter by formality match
    matched = [i for i in wardrobe if i['formality'] == required_formality]
    if not matched:
        matched = wardrobe  # fall back to full wardrobe

    # Prefer season-appropriate items
    seasonal = [i for i in matched if i['season'] in (season_hint, 'all')]
    pool = seasonal or matched

    # Pick up to 3 items across categories
    seen_cats, picks = set(), []
    for item in pool:
        if item['category'] not in seen_cats:
            picks.append(item)
            seen_cats.add(item['category'])
        if len(picks) == 3:
            break

    notes = f"Outfit for a {required_formality} day"
    if is_cold:
        notes += " — it's cold, so layers are recommended"
    elif is_hot:
        notes += " — it's warm, so light fabrics are best"
    if is_raining:
        notes += ". Don't forget a waterproof layer!"

    return {
        'status':   'stub',
        'item_ids': [i['id'] for i in picks],
        'notes':    notes,
    }


def _daily_look_mistral(user, wardrobe, events, weather, required_formality) -> dict:
    from arokah.services.mistral_client import chat_json
    prompt = f"""You are Arokah, a personal AI stylist. Given the user's wardrobe and today's
calendar + weather, recommend the best outfit.

Date       : {_today_str()}
Weather    : {weather}
Formality  : {required_formality}
Calendar   : {events}
Wardrobe   : {wardrobe}

Rules:
- Only use item IDs from the wardrobe list above
- Pick 2-4 items across different categories (top, bottom, outerwear, footwear)
- Prefer season-appropriate, weather-appropriate items
- Match the required formality level
- Give a concise, friendly explanation (max 2 sentences)

Return JSON: {{"item_ids": [1, 2, 3], "notes": "...", "layer_swap": "optional tip"}}"""
    result = chat_json(prompt)
    result['status'] = 'ai'
    return result


# ── Packing List ──────────────────────────────────────────────────────────────

def run_packing_list(user, input_data: dict) -> dict:
    days       = int(input_data.get('days', 3))
    activities = input_data.get('activities', [])
    wardrobe   = _wardrobe_for_user(user)

    if not wardrobe:
        return {'status': 'no_wardrobe', 'message': 'Add items to your wardrobe first.'}

    if _has_mistral():
        return _packing_list_mistral(wardrobe, days, activities)
    return _packing_list_stub(wardrobe, days, activities)


def _packing_list_stub(wardrobe, days, activities) -> dict:
    """5-4-3-2-1 capsule heuristic."""
    targets = {'top': 5, 'bottom': 4, 'outerwear': 3, 'footwear': 2, 'accessory': 1}

    # Scale for trip length (max doubles at 10+ days)
    scale = min(2.0, 1.0 + (days - 3) * 0.1) if days > 3 else 1.0

    # Include activewear if needed
    if any(a.lower() in ('gym', 'hiking', 'beach', 'sport', 'workout') for a in activities):
        targets['activewear'] = 2

    picks, weight = [], 0
    for cat, quota in targets.items():
        items = [i for i in wardrobe if i['category'] == cat][:round(quota * scale)]
        picks.extend(items)
        weight += sum(i.get('weight_grams') or 0 for i in items)

    return {
        'status':                 'stub',
        'item_ids':               [i['id'] for i in picks],
        'packing_list':           picks,
        'estimated_weight_grams': weight,
        'days':                   days,
        'notes':                  f"5-4-3-2-1 capsule for {days} days. Estimated weight: {weight}g.",
    }


def _packing_list_mistral(wardrobe, days, activities) -> dict:
    from arokah.services.mistral_client import chat_json
    prompt = f"""You are Arokah, a packing expert. Recommend a minimal capsule wardrobe using
the 5-4-3-2-1 rule for a {days}-day trip with activities: {activities}.

Wardrobe: {wardrobe}

Return JSON: {{"item_ids": [...], "estimated_weight_grams": 0, "notes": "..."}}"""
    result = chat_json(prompt)
    result['status'] = 'ai'
    return result


# ── Conflict Detector ─────────────────────────────────────────────────────────

def run_conflict_detector(user, input_data: dict) -> dict:
    from itinerary.models import CalendarEvent

    raw_date = input_data.get('date', None)
    if hasattr(raw_date, 'isoformat'):
        date = raw_date.isoformat()
    else:
        date = raw_date or _today_str()
    weather = _get_weather({**input_data, 'weather': input_data.get('weather', {})})

    events = list(CalendarEvent.objects.filter(user=user, start_time__date=date))
    conflicts = []

    rain_chance = weather.get('precipitation_probability', 0)
    temp_c      = weather.get('temp_c', 15)
    is_raining  = weather.get('is_raining', False)

    for event in events:
        etype = event.event_type

        # Outdoor workout + rain
        if etype == 'workout' and rain_chance > 70:
            conflicts.append({
                'type':    'weather_activity',
                'event':   event.title,
                'message': f"{rain_chance}% chance of rain — consider indoor gear for your workout.",
                'severity': 'warning',
            })

        # Travel day + heavy rain or storm
        if etype == 'travel' and weather.get('wmo_code', 0) in {65, 80, 81, 82, 95, 96, 99}:
            conflicts.append({
                'type':    'weather_travel',
                'event':   event.title,
                'message': "Severe weather forecast on your travel day — pack a heavy waterproof and check transport updates.",
                'severity': 'warning',
            })

        # Formal event + very cold
        if etype in ('external_meeting', 'wedding', 'interview') and temp_c < 5:
            conflicts.append({
                'type':    'weather_formality',
                'event':   event.title,
                'message': f"It'll be {temp_c}°C — make sure your smart outfit includes a warm coat.",
                'severity': 'info',
            })

        # Social dinner + heavy rain
        if etype == 'social' and is_raining:
            conflicts.append({
                'type':    'weather_social',
                'event':   event.title,
                'message': "Rain expected — consider whether open-toe shoes or suede items are a good idea tonight.",
                'severity': 'info',
            })

    return {
        'date':           date,
        'weather':        weather,
        'conflicts':      conflicts,
        'events_checked': len(events),
    }


# ── Cultural Advisor ──────────────────────────────────────────────────────────

def run_cultural_advisor(user, input_data: dict) -> dict:
    from cultural.models import CulturalRule, LocalEvent
    from arokah.services.weather import get_weather_for_location

    country = input_data.get('country', '')
    city    = input_data.get('city', '')
    month   = input_data.get('month', datetime.date.today().month)

    # Fetch live weather for the destination. Used by the AI to tailor clothing
    # recommendations (temperature, rain, wind) and by the wardrobe matcher to
    # favour season-appropriate items. Falls back gracefully if Open-Meteo is
    # unreachable — the rest of the advice still renders.
    weather_query = city if city else country
    try:
        weather = get_weather_for_location(weather_query)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            'Weather lookup failed for %s: %s', weather_query, exc
        )
        weather = None

    rules = list(CulturalRule.objects.filter(country__iexact=country).values(
        'rule_type', 'description', 'severity', 'place_name', 'city'))
    if city:
        rules = [r for r in rules if not r['city'] or r['city'].lower() == city.lower()]

    events = list(LocalEvent.objects.filter(
        country__iexact=country,
        start_month__lte=month,
        end_month__gte=month,
    ).values('name', 'clothing_note', 'description'))

    # When the DB has nothing (or almost nothing) for this destination, ask the
    # AI to generate a real cultural clothing brief. The curated DB still wins
    # when it has data, to keep authoritative rules stable.
    ai_brief = None
    if _has_mistral() and len(rules) < 3:
        ai_brief = _generate_cultural_brief_ai(country, city, month, weather)
        if ai_brief:
            # Merge AI-generated rules into the list so the existing UI renders them.
            for r in ai_brief.get('rules', []):
                rules.append({
                    'rule_type':   r.get('rule_type') or 'general',
                    'description': r.get('description') or '',
                    'severity':    r.get('severity') or 'info',
                    'place_name':  r.get('place_name') or '',
                    'city':        r.get('city') or '',
                })
            for ev in ai_brief.get('local_events', []):
                events.append({
                    'name':          ev.get('name') or '',
                    'clothing_note': ev.get('clothing_note') or '',
                    'description':   ev.get('description') or '',
                })

    rules  = _consolidate_rules(rules)
    events = _dedupe_events(events)

    # Generate a curated list of popular destinations + upcoming events in the
    # next ~14 days, each with specific clothing guidance. This is what powers
    # the itinerary-style highlights section in the UI.
    highlights: list[dict] = []
    if _has_mistral():
        highlights = _generate_destination_highlights_ai(country, city, weather)

    # Match the user's wardrobe against the rules AND the highlights so the
    # recommendations cover both general etiquette and specific outings.
    wardrobe_matches: list[dict] = []
    gaps: list[dict] = []
    if _has_mistral() and (rules or highlights):
        wardrobe_matches, gaps = _match_wardrobe_against_rules(
            user, country, city, rules, highlights, weather,
        )

    return {
        'country':          country,
        'city':             city,
        'rules':            rules,
        'local_events':     events,
        'highlights':       highlights,
        'weather':          weather,
        'summary':          (ai_brief or {}).get('summary', ''),
        'source':           'ai' if ai_brief else 'database',
        'wardrobe_matches': wardrobe_matches,
        'gaps':             gaps,
    }


def _weather_cache_bucket(weather: dict | None) -> str:
    """Collapse a weather snapshot into a coarse bucket for cache keying.

    Rounds temperature to the nearest 5°C and flags rain/cold/hot. Two queries
    in the same bucket share cached advice; queries across buckets regenerate.
    """
    if not weather:
        return 'none'
    temp = weather.get('temp_c')
    if not isinstance(temp, (int, float)):
        temp = 15
    bucket_temp = round(temp / 5) * 5
    flags = ''
    if weather.get('is_cold'):    flags += 'c'
    if weather.get('is_hot'):     flags += 'h'
    if weather.get('is_raining'): flags += 'r'
    return f't{bucket_temp}{flags or "m"}'


def _weather_context_line(weather: dict | None) -> str:
    """Format the weather snapshot for inclusion in an LLM prompt.

    Returns an empty string if no weather is available, so callers can cleanly
    concatenate without conditionals.
    """
    if not weather:
        return ''
    temp      = weather.get('temp_c')
    tmin      = weather.get('temp_min_c')
    tmax      = weather.get('temp_max_c')
    condition = weather.get('condition', 'unknown')
    precip    = weather.get('precipitation_mm', 0)
    wind      = weather.get('wind_kmh', 0)
    is_cold   = weather.get('is_cold', False)
    is_hot    = weather.get('is_hot', False)
    is_rain   = weather.get('is_raining', False)

    flags = []
    if is_cold: flags.append('COLD')
    if is_hot:  flags.append('HOT')
    if is_rain: flags.append('RAINING')
    flag_str = f' [{", ".join(flags)}]' if flags else ''

    def _fmt(v):
        return f'{v:.0f}' if isinstance(v, (int, float)) else '?'

    return (
        f'Current weather: {condition}, {_fmt(temp)}°C '
        f'(daily range {_fmt(tmin)}–{_fmt(tmax)}°C), '
        f'precipitation {_fmt(precip)}mm, wind {_fmt(wind)}km/h.{flag_str}'
    )


def _generate_destination_highlights_ai(country: str, city: str,
                                        weather: dict | None = None) -> list[dict]:
    """Generate a list of popular destinations + upcoming events with clothing advice.

    Returns a list of dicts shaped as:
        {
          "type": "destination" | "event",
          "name": "...",
          "when": "year-round" | "Dec 20 - Jan 5" | "...",
          "description": "...",
          "clothing": "...",
          "formality": "casual | casual_smart | smart | formal | activewear",
        }

    Cached 7 days per (country, city, ISO week) so highlights refresh weekly
    for upcoming events while still protecting the rate limit.
    """
    from django.core.cache import cache
    from arokah.services.mistral_client import chat_json

    today = datetime.date.today()
    iso_week = today.strftime('%G-W%V')  # stable cache key that refreshes weekly
    weather_bucket = _weather_cache_bucket(weather)
    cache_key = (
        f'cultural_highlights:'
        f'{country.lower().strip()}:{city.lower().strip()}:'
        f'{iso_week}:{weather_bucket}'
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    place = f'{city}, {country}' if city else country
    today_str    = today.strftime('%B %d, %Y')  # e.g. "April 08, 2026"
    two_weeks    = (today + datetime.timedelta(days=14)).strftime('%B %d, %Y')

    weather_line = _weather_context_line(weather)
    weather_block = f'{weather_line}\n\n' if weather_line else ''

    prompt = (
        f'You are a local travel expert. A traveller is visiting {place}. '
        f'Today is {today_str}.\n\n'
        f'{weather_block}'
        'Generate TWO things:\n\n'
        '1. POPULAR DESTINATIONS — the 4-6 most iconic places to visit in this '
        'location (famous landmarks, temples, markets, neighbourhoods, beaches, etc.). '
        'For each, give the name, a one-sentence description, specific clothing '
        'recommendations appropriate for that place, and the formality level.\n\n'
        f'2. UPCOMING EVENTS — any notable festivals, ceremonies, cultural events, '
        f'or seasonal happenings between {today_str} and {two_weeks} (the next 14 '
        'days). Only include events that genuinely happen in this window based on '
        'your knowledge of local calendars. If there are no notable events in this '
        'window, return an empty events list — do NOT invent fake events.\n\n'
        'Return JSON EXACTLY in this shape:\n'
        '{\n'
        '  "destinations": [\n'
        '    {\n'
        '      "name":        "Sensō-ji Temple",\n'
        '      "description": "Tokyo\'s oldest Buddhist temple in Asakusa.",\n'
        '      "clothing":    "Modest attire covering shoulders and knees. Comfortable walking shoes that slip off easily for entering inner halls.",\n'
        '      "formality":   "casual_smart"\n'
        '    }\n'
        '  ],\n'
        '  "events": [\n'
        '    {\n'
        '      "name":        "Cherry Blossom Festival",\n'
        '      "when":        "April 5 - April 15",\n'
        '      "description": "Peak hanami season in the city parks.",\n'
        '      "clothing":    "Layers for cool evenings. Light pastel colours are traditional. Comfortable flats for long walks.",\n'
        '      "formality":   "casual"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        'Rules:\n'
        '- Be SPECIFIC. Name real places, not generic categories.\n'
        '- Clothing advice must be actionable (e.g. "long skirt covering knees" not '
        '"modest attire").\n'
        '- formality MUST be one of: casual, casual_smart, smart, formal, activewear.\n'
        '- Each destination name must be unique. Each event name must be unique.\n'
        '- Do not invent events that do not genuinely occur in the given window.\n'
        '- Tie clothing recommendations to the current weather shown above '
        '(e.g. rain jacket if raining, insulated coat if cold, breathable linen '
        'if hot). If an outdoor event is clearly inappropriate for the current '
        'weather, prefer alternatives that still make sense.'
    )

    try:
        result = chat_json(prompt)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            'Destination highlights generation failed for %s: %s', place, exc
        )
        return []

    valid_formality = {'casual', 'casual_smart', 'smart', 'formal', 'activewear'}
    highlights: list[dict] = []

    seen_names: set[str] = set()

    for d in (result.get('destinations') or [])[:6]:
        name = str(d.get('name') or '').strip()[:120]
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        form = str(d.get('formality') or 'casual').strip().lower()
        highlights.append({
            'type':        'destination',
            'name':        name,
            'when':        'year-round',
            'description': str(d.get('description') or '').strip()[:300],
            'clothing':    str(d.get('clothing') or '').strip()[:500],
            'formality':   form if form in valid_formality else 'casual',
        })

    for ev in (result.get('events') or [])[:4]:
        name = str(ev.get('name') or '').strip()[:120]
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        form = str(ev.get('formality') or 'casual').strip().lower()
        highlights.append({
            'type':        'event',
            'name':        name,
            'when':        str(ev.get('when') or 'upcoming').strip()[:80],
            'description': str(ev.get('description') or '').strip()[:300],
            'clothing':    str(ev.get('clothing') or '').strip()[:500],
            'formality':   form if form in valid_formality else 'casual',
        })

    cache.set(cache_key, highlights, timeout=60 * 60 * 24 * 7)  # 7 days
    return highlights


# Severity ordering: higher = stronger. Used when merging duplicate rules.
_SEVERITY_RANK = {'info': 0, 'warning': 1, 'required': 2}


def _consolidate_rules(rules: list[dict]) -> list[dict]:
    """Merge rules that share (rule_type, place_name).

    The AI sometimes emits multiple rules about the same venue (three "mosque"
    rules each covering a different aspect). Consolidate them into one rule per
    (rule_type, normalized place_name):
      - concatenate unique descriptions with " " separator
      - keep the strongest severity
      - preserve first-seen order
    Keys compare case-insensitively and whitespace-normalized.
    """
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []

    for r in rules:
        rtype = (r.get('rule_type') or 'general').strip().lower()
        place = (r.get('place_name') or '').strip().lower()
        key   = (rtype, place)

        desc = (r.get('description') or '').strip()
        sev  = (r.get('severity') or 'info').strip().lower()

        if key not in merged:
            merged[key] = {
                'rule_type':   r.get('rule_type') or 'general',
                'description': desc,
                'severity':    sev if sev in _SEVERITY_RANK else 'info',
                'place_name':  r.get('place_name') or '',
                'city':        r.get('city') or '',
            }
            order.append(key)
            continue

        existing = merged[key]
        # Append description only if it adds new content
        if desc and desc.lower() not in existing['description'].lower():
            existing['description'] = (
                existing['description'] + ' ' + desc if existing['description'] else desc
            )
        # Upgrade severity to the strongest seen
        if _SEVERITY_RANK.get(sev, 0) > _SEVERITY_RANK.get(existing['severity'], 0):
            existing['severity'] = sev

    return [merged[k] for k in order]


def _dedupe_events(events: list[dict]) -> list[dict]:
    """Drop duplicate events by case-insensitive name."""
    seen: set[str] = set()
    result: list[dict] = []
    for ev in events:
        name_key = (ev.get('name') or '').strip().lower()
        if not name_key or name_key in seen:
            continue
        seen.add(name_key)
        result.append(ev)
    return result


def _match_wardrobe_against_rules(user, country: str, city: str,
                                  rules: list[dict],
                                  highlights: list[dict] | None = None,
                                  weather: dict | None = None):
    """Match user's wardrobe items to cultural rules + destination highlights.

    Returns `(wardrobe_matches, gaps)`:
      - wardrobe_matches: list of {item_id, name, category, reason} — items the
        user already owns that satisfy one or more rules or highlights.
      - gaps: list of {description, category, why, search_links} — things the
        user should pack but doesn't own. search_links are Google Shopping /
        Amazon search URLs pre-filled with a location-aware query.

    Cached per (user, destination, wardrobe_version, highlights_version) so
    edits to the wardrobe OR regenerated highlights bust the cache naturally.
    """
    from django.core.cache import cache
    from wardrobe.models import ClothingItem
    from arokah.services.mistral_client import chat_json

    wardrobe = list(ClothingItem.objects.filter(user=user, is_active=True).values(
        'id', 'name', 'category', 'formality', 'season', 'colors', 'tags'))

    # Use the latest updated_at across the wardrobe as a cheap version key so
    # any add/edit/delete invalidates the cache.
    from django.db.models import Max
    version = ClothingItem.objects.filter(user=user).aggregate(
        v=Max('updated_at')
    )['v']
    version_key = version.isoformat() if version else 'empty'

    # Include a highlights fingerprint so regenerated highlights also bust cache.
    highlights = highlights or []
    hl_fp = ','.join(sorted(h.get('name', '') for h in highlights))[:120]

    weather_bucket = _weather_cache_bucket(weather)
    cache_key = (
        f'cultural_match:{user.pk}:'
        f'{country.lower().strip()}:{city.lower().strip()}:'
        f'{version_key}:{hash(hl_fp) & 0xffffffff:x}:{weather_bucket}'
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached['matches'], cached['gaps']

    # Build a compact rules summary for the prompt
    rules_text = '\n'.join(
        f'- [{r.get("severity", "info")}] '
        f'{(r.get("place_name") or "general").strip()}: {r.get("description", "")}'
        for r in rules
    ) or '(none)'

    highlights_text = '\n'.join(
        f'- {h["type"].upper()}: {h["name"]} '
        f'({h.get("when", "year-round")}) — {h.get("clothing", "")}'
        for h in highlights
    ) or '(none)'

    if wardrobe:
        wardrobe_text = '\n'.join(
            f'- id={i["id"]} | {i["name"]} '
            f'(category={i["category"]}, formality={i["formality"]}, '
            f'colors={i.get("colors") or []})'
            for i in wardrobe
        )
    else:
        wardrobe_text = '(empty)'

    place = f'{city}, {country}' if city else country
    weather_line = _weather_context_line(weather)
    weather_block = f'{weather_line}\n\n' if weather_line else ''
    prompt = (
        f'You are helping a traveller visiting {place}. Below are the current '
        'weather, cultural dress-code rules, specific popular destinations / '
        'upcoming events they will visit, and their current wardrobe.\n\n'
        f'{weather_block}'
        f'CULTURAL RULES:\n{rules_text}\n\n'
        f'PLACES & EVENTS THEY WILL VISIT:\n{highlights_text}\n\n'
        f'TRAVELLER\'S WARDROBE:\n{wardrobe_text}\n\n'
        'Your task:\n'
        '1. Pick items from the wardrobe that work for EITHER the cultural rules '
        'OR the specific places/events above. Explicitly name which rule or which '
        'place/event each item is for in the "reason" field (e.g. "Covers shoulders '
        'for Senso-ji Temple visit").\n'
        '2. Identify GAPS — things the traveller should bring but does NOT already '
        'own. Prioritise gaps that would prevent them from visiting a specific place '
        'or event on the list above. For each gap, give a clear 2-4 word description, '
        'a category from [top, bottom, dress, outerwear, footwear, accessory], a '
        'one-sentence "why" naming the rule/place/event it addresses, and a short '
        'shopping search query (3-6 words, no brand names).\n\n'
        'Return JSON EXACTLY in this shape:\n'
        '{\n'
        '  "matches": [\n'
        '    {"item_id": 12, "reason": "Covers shoulders for Senso-ji Temple visit"}\n'
        '  ],\n'
        '  "gaps": [\n'
        '    {\n'
        '      "description": "Lightweight headscarf",\n'
        '      "category": "accessory",\n'
        '      "why": "Required for visiting the Blue Mosque",\n'
        '      "search_query": "lightweight cotton headscarf women"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        'Rules:\n'
        '- If the wardrobe is empty, return "matches": [] and list all essentials as gaps.\n'
        '- Do not invent item_ids that are not in the wardrobe list above.\n'
        '- Maximum 8 matches and 6 gaps. Prefer fewer, higher-quality suggestions.\n'
        '- Gap categories MUST be one of: top, bottom, dress, outerwear, footwear, accessory.\n'
        '- Respect the current weather: prefer wardrobe items and gap suggestions '
        'that are appropriate for the temperature and conditions shown above '
        '(no heavy wool coats when it is hot, no sandals when it is freezing, '
        'include a rain layer when it is raining).'
    )

    try:
        result = chat_json(prompt)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            'Wardrobe matching failed for %s: %s', place, exc
        )
        return [], []

    # Cross-reference returned item_ids with actual wardrobe + enrich with name/category
    wardrobe_by_id = {i['id']: i for i in wardrobe}
    wardrobe_matches: list[dict] = []
    for m in (result.get('matches') or [])[:8]:
        try:
            item_id = int(m.get('item_id'))
        except (TypeError, ValueError):
            continue
        item = wardrobe_by_id.get(item_id)
        if not item:
            continue
        wardrobe_matches.append({
            'item_id':  item_id,
            'name':     item['name'],
            'category': item['category'],
            'reason':   str(m.get('reason') or '')[:300],
        })

    gaps: list[dict] = []
    valid_gap_cats = {'top', 'bottom', 'dress', 'outerwear', 'footwear', 'accessory'}
    for g in (result.get('gaps') or [])[:6]:
        desc  = str(g.get('description') or '').strip()[:120]
        if not desc:
            continue
        cat = str(g.get('category') or '').strip().lower()
        if cat not in valid_gap_cats:
            cat = 'other'
        why = str(g.get('why') or '').strip()[:300]
        search_query = str(g.get('search_query') or desc).strip()[:120]
        gaps.append({
            'description':  desc,
            'category':     cat,
            'why':          why,
            'search_links': _build_shopping_links(search_query, country),
        })

    cache.set(cache_key, {'matches': wardrobe_matches, 'gaps': gaps},
              timeout=60 * 60 * 24 * 7)  # 7 days
    return wardrobe_matches, gaps


def _build_shopping_links(query: str, country: str) -> list[dict]:
    """Build shopping search URLs pre-filled for the given query + country.

    We cannot directly recommend product links without a commerce API, but
    deep links into Google Shopping / Amazon / Etsy land the user on a
    localized search page with real products in one click.
    """
    from urllib.parse import quote_plus

    q = quote_plus(query.strip())
    # Country → Amazon regional TLD mapping. Falls back to .com.
    amazon_tld = {
        'india':          'in',
        'united kingdom': 'co.uk',
        'uk':             'co.uk',
        'england':        'co.uk',
        'germany':        'de',
        'france':         'fr',
        'italy':          'it',
        'spain':          'es',
        'japan':          'co.jp',
        'canada':         'ca',
        'australia':      'com.au',
        'mexico':         'com.mx',
        'brazil':         'com.br',
        'netherlands':    'nl',
        'sweden':         'se',
        'turkey':         'com.tr',
        'united arab emirates': 'ae',
        'uae':            'ae',
        'saudi arabia':   'sa',
        'singapore':      'sg',
    }.get(country.lower().strip(), 'com')

    return [
        {
            'label': 'Google Shopping',
            'url':   f'https://www.google.com/search?tbm=shop&q={q}',
        },
        {
            'label': f'Amazon ({amazon_tld})',
            'url':   f'https://www.amazon.{amazon_tld}/s?k={q}',
        },
        {
            'label': 'Etsy',
            'url':   f'https://www.etsy.com/search?q={q}',
        },
    ]


def _generate_cultural_brief_ai(country: str, city: str, month: int,
                                weather: dict | None = None) -> dict | None:
    """Ask Mistral to produce a structured cultural clothing brief.

    Returns a dict with `rules`, `local_events`, `summary`, or None if the
    call fails. Values are shaped to match the DB schema so the UI needs no
    changes.

    Cache key includes a weather bucket so the advice refreshes when conditions
    change meaningfully (e.g. cold → hot, dry → rainy), while still protecting
    the Mistral rate limit across rapid repeat queries.
    """
    from django.core.cache import cache
    from arokah.services.mistral_client import chat_json

    # Weather bucket: stable across small fluctuations (±3°C) and flips between
    # cold/mild/hot and dry/wet. This keeps the cache useful without pinning
    # advice to stale conditions.
    bucket = _weather_cache_bucket(weather)
    cache_key = (
        f'cultural_brief:{country.lower().strip()}:{city.lower().strip()}:'
        f'{month}:{bucket}'
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    month_name = datetime.date(2000, month, 1).strftime('%B')
    place = f'{city}, {country}' if city else country
    weather_line = _weather_context_line(weather)
    weather_block = f'\n{weather_line}\n' if weather_line else ''

    prompt = (
        f'You are a cultural etiquette and clothing advisor. Generate concrete, '
        f'practical dress-code guidance for a traveller visiting {place} in {month_name}.\n'
        f'{weather_block}'
        'Return JSON with EXACTLY these keys:\n'
        '{\n'
        '  "summary": "2-3 sentence overview of how to dress respectfully and comfortably here.",\n'
        '  "rules": [\n'
        '    {\n'
        '      "rule_type":   "cover_head | cover_shoulders | cover_knees | remove_shoes | modest_dress | no_bare_feet | festival_wear | color_warning | general",\n'
        '      "description": "Specific actionable guidance (1-2 sentences).",\n'
        '      "severity":    "required | warning | info",\n'
        '      "place_name":  "Specific venue/situation if applicable (e.g. \'temples\', \'mosques\', \'government buildings\'), or empty string",\n'
        '      "city":        ""\n'
        '    }\n'
        '  ],\n'
        '  "local_events": [\n'
        '    {\n'
        '      "name":          "Festival or seasonal event happening around this month",\n'
        '      "description":   "Brief context",\n'
        '      "clothing_note": "What to wear / avoid during this event"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        'Requirements:\n'
        '- Produce 5-8 rules covering religious sites, general public dress norms, '
        'footwear conventions, weather-appropriate clothing for the season, and any '
        'color/style warnings.\n'
        '- Use the current weather above to make clothing advice concrete (e.g. '
        '"bring a waterproof layer" if raining, "linen and light cotton" if hot, '
        '"insulated coat and hat" if cold). Tie recommendations to the actual '
        'temperature and conditions shown, not generic seasonal tips.\n'
        '- CRITICAL: each rule MUST be unique. Do NOT produce multiple rules for the '
        'same place_name (e.g. only ONE rule for "mosques", ONE for "temples", ONE for '
        '"beaches"). If there are multiple things to say about a single place, '
        'CONSOLIDATE them into one rule with a combined description.\n'
        '- Each rule_type + place_name combination must appear at most once across '
        'the entire list.\n'
        '- Include 0-3 local_events only if genuinely relevant for this month.\n'
        '- Be specific and factual. No hedging, no "it depends".\n'
        '- Severity: "required" = legal/religious obligation; "warning" = strong social '
        'norm; "info" = helpful tip.'
    )

    try:
        result = chat_json(prompt)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            'Cultural advisor AI generation failed for %s: %s', place, exc
        )
        return None

    # Cache success for 30 days — advice is stable, and this protects the
    # rate limit on future repeat lookups of the same destination.
    cache.set(cache_key, result, timeout=60 * 60 * 24 * 30)
    return result


# ── Trip Outfit Planner ───────────────────────────────────────────────────────

def run_outfit_planner(user, input_data: dict) -> dict:
    """
    Generate a per-day outfit plan for a trip.
    Input: trip_id OR (start_date, end_date, destination, activities)
    """
    import datetime as dt
    from arokah.services.weather import get_weather_for_location

    trip_id = input_data.get('trip_id')
    activities = input_data.get('activities', [])

    if trip_id:
        from itinerary.models import Trip
        try:
            trip = Trip.objects.get(id=trip_id, user=user)
            start      = trip.start_date
            end        = trip.end_date
            destination = trip.destination
        except Trip.DoesNotExist:
            return {'status': 'error', 'message': f'Trip {trip_id} not found.'}
    else:
        try:
            sd = input_data.get('start_date', '')
            ed = input_data.get('end_date', '')
            start       = sd if isinstance(sd, dt.date) else dt.date.fromisoformat(sd)
            end         = ed if isinstance(ed, dt.date) else dt.date.fromisoformat(ed)
            destination = input_data.get('destination', '')
        except (ValueError, TypeError):
            return {'status': 'error', 'message': 'Provide trip_id or start_date/end_date/destination.'}

    wardrobe = _wardrobe_for_user(user)
    if not wardrobe:
        return {'status': 'no_wardrobe', 'message': 'Add items to your wardrobe first.'}

    # Fetch weather for the trip destination (first day as proxy)
    weather = get_weather_for_location(destination, start) if destination else _get_weather({})

    days_count = (end - start).days + 1

    if _has_mistral():
        return _outfit_planner_mistral(wardrobe, start, end, destination, activities, weather)

    # ── Stub: rotate wardrobe items across days ───────────────────────────────
    day_plans = []
    tops       = [i for i in wardrobe if i['category'] == 'top']
    bottoms    = [i for i in wardrobe if i['category'] == 'bottom']
    outerwear  = [i for i in wardrobe if i['category'] == 'outerwear']
    footwear   = [i for i in wardrobe if i['category'] == 'footwear']
    activewear = [i for i in wardrobe if i['category'] == 'activewear']

    for i in range(days_count):
        date = start + dt.timedelta(days=i)
        day_items = []
        if tops:      day_items.append(tops[i % len(tops)])
        if bottoms:   day_items.append(bottoms[i % len(bottoms)])
        if outerwear and weather.get('is_cold'): day_items.append(outerwear[i % len(outerwear)])
        if footwear:  day_items.append(footwear[i % len(footwear)])
        # Add activewear on alternating days if available
        if activewear and i % 2 == 0: day_items.append(activewear[i % len(activewear)])

        day_plans.append({
            'date':     date.isoformat(),
            'day':      i + 1,
            'item_ids': [item['id'] for item in day_items],
            'items':    day_items,
        })

    # Deduplicate packing list (unique item IDs across all days)
    all_ids  = list({item_id for day in day_plans for item_id in day['item_ids']})
    all_items = [i for i in wardrobe if i['id'] in all_ids]
    weight   = sum(i.get('weight_grams') or 0 for i in all_items)

    return {
        'status':                 'stub',
        'destination':            destination,
        'start_date':             start.isoformat(),
        'end_date':               end.isoformat(),
        'days':                   days_count,
        'weather_preview':        weather,
        'day_plans':              day_plans,
        'packing_list_ids':       all_ids,
        'estimated_weight_grams': weight,
        'notes': f"Mix-and-match plan for {days_count} days in {destination}. Estimated bag weight: {weight}g.",
    }


def _outfit_planner_mistral(wardrobe, start, end, destination, activities, weather) -> dict:
    import datetime as dt
    from arokah.services.mistral_client import chat_json
    days_count = (end - start).days + 1
    prompt = f"""You are Arokah, an expert travel stylist. Create a day-by-day outfit plan
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
    result['status']      = 'ai'
    result['destination'] = destination
    result['start_date']  = start.isoformat()
    result['end_date']    = end.isoformat()
    result['days']        = days_count
    return result

