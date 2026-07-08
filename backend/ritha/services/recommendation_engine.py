"""
Unified Recommendation Engine.

Combines three signals into scored outfit recommendations:
  1. ML model     — category compatibility from trained co-occurrence matrix
  2. Weather API  — temperature / conditions → appropriate clothing
  3. Mistral AI   — cultural context, etiquette, events, places to visit

Output distinguishes items the user *owns* (wardrobe matches) from items
they *need* (with shopping links).
"""

import datetime
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache

logger = logging.getLogger("ritha.recommendation")

# Cache TTLs (seconds)
# Cultural rules (dress codes, etiquette, festivals by month) are stable across
# months. The earlier 24h value over-spent Mistral budget — every active user
# was paying to regenerate "modest dress in Riyadh" once a day. 30 days reflects
# the actual rate of change while still surfacing seasonal events.
_CULTURAL_TTL = 60 * 60 * 24 * 30  # 30 days
_WEATHER_TTL = 60 * 30  # 30min — short-term forecast stability
_SHOPPING_TTL = 60 * 60 * 6  # 6h — shopping suggestions


def _cache_key(prefix: str, *parts) -> str:
    raw = "|".join(str(p).strip().lower() for p in parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]
    return f"ritha:rec:{prefix}:{digest}"


# Tokens stripped from destination strings before cache keying so that
# "Tokyo", "tokyo, japan", and "Tokyo Japan" all collapse to the same cache
# slot. Order matters — strip commas first so "tokyo,japan" → "tokyo japan"
# before whitespace collapse.
_DEST_NOISE_TOKENS = (
    "city of",
    "the city of",
    "greater",
    "metropolitan",
    "province",
    "prefecture",
    "region",
    "state of",
)


def _normalize_destination(destination: str) -> str:
    """Collapse common destination-string variations to a single canonical form.

    Used only as a cache key — the original string is still passed to Mistral
    so the model gets the user's exact phrasing.
    """
    s = (destination or "").lower().strip()
    s = s.replace(",", " ").replace(".", " ")
    for tok in _DEST_NOISE_TOKENS:
        s = s.replace(tok, " ")
    return " ".join(s.split())


# ── Public entry point ───────────────────────────────────────────────────────


def recommend(user, input_data: dict) -> dict:
    """
    Generate unified outfit recommendations.

    input_data keys:
        destination  (str, required) — city or country
        date         (str, optional) — YYYY-MM-DD, defaults to today
        start_date   (date, optional) — trip start for multi-day recs
        end_date     (date, optional) — trip end for multi-day recs
        occasion     (str, optional) — casual / business / formal / wedding /
                                        cultural_visit / travel / date / activewear
        location     (str, optional) — user's current location (for weather)
        lat / lon    (float, optional)

    Returns dict with `days` list for multi-day trips or flat structure for single-day.
    """
    destination = input_data.get("destination", "").strip()
    occasion = input_data.get("occasion", "casual").strip()

    if not destination:
        return {"error": "destination is required."}

    # Determine date range
    start_date = input_data.get("start_date")
    end_date = input_data.get("end_date")
    is_multi_day = start_date and end_date

    if is_multi_day:
        if not isinstance(start_date, datetime.date):
            start_date = datetime.date.fromisoformat(str(start_date))
        if not isinstance(end_date, datetime.date):
            end_date = datetime.date.fromisoformat(str(end_date))
        return _recommend_multi_day(user, destination, start_date, end_date, occasion, input_data)

    # Single-day fallback
    raw_date = input_data.get("date", datetime.date.today())
    date_str = (
        raw_date.isoformat()
        if isinstance(raw_date, datetime.date)
        else str(raw_date or datetime.date.today().isoformat())
    )

    return _recommend_single_day(user, destination, date_str, occasion, input_data)


def _recommend_single_day(user, destination, date_str, occasion, input_data):
    """Single-day recommendation (original behaviour)."""
    # Parallelize weather + wardrobe fetch + cultural context (all I/O bound).
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_weather = pool.submit(_fetch_weather, input_data, destination)
        f_wardrobe = pool.submit(_get_wardrobe, user)
        weather = f_weather.result()
        # Cultural depends on weather for prompt context — dispatch once weather ready.
        f_cultural = pool.submit(
            _fetch_cultural_context,
            destination,
            date_str,
            weather,
            occasion,
        )
        cultural = f_cultural.result()
        wardrobe_items = f_wardrobe.result()

    ml_scores = _ml_category_scores(weather, occasion)
    ideal_outfit = _build_ideal_outfit(ml_scores, weather, cultural, occasion)

    user_prefs = _get_user_item_scores(user)
    matches, gaps = _match_wardrobe(wardrobe_items, ideal_outfit, weather, user_prefs=user_prefs, cultural=cultural)

    if not wardrobe_items and not gaps:
        gaps = [
            {
                "role": item["role"],
                "ideal_category": item["category"],
                "wardrobe_category": item.get("wardrobe_category", "other"),
                "description": f"{item['category'].title()} for {item['role']}",
                "why": "Your wardrobe is empty — here are recommended products.",
            }
            for item in ideal_outfit
        ]

    outfit_score = _score_matched_outfit(matches)
    shopping = _build_shopping_suggestions(gaps, destination, weather, cultural, occasion)

    return {
        "weather": weather,
        "cultural": cultural,
        "outfit": {
            "ideal_categories": ideal_outfit,
            "score": outfit_score,
            "notes": _generate_outfit_notes(matches, gaps, weather, cultural, occasion),
        },
        "wardrobe_matches": matches,
        "shopping_suggestions": shopping,
        "metadata": {
            "signals_used": ["ml_compatibility", "weather", "cultural_ai"],
            "destination": destination,
            "occasion": occasion,
            "date": date_str,
            "generated_at": datetime.datetime.now().isoformat(),
        },
    }


def _recommend_multi_day(user, destination, start_date, end_date, occasion, input_data):
    """
    Generate per-day outfit recommendations for the full trip duration.
    Fetches weather forecast for all days in one call, cultural context once.
    Each day gets a unique outfit — already-assigned wardrobe items are deprioritised.
    """
    from ritha.services.weather import get_weather_forecast

    num_days = (end_date - start_date).days + 1

    # ── 1. Weather forecast for entire trip ──────────────────────────────
    forecasts = get_weather_forecast(destination, start_date, end_date)
    # Pad if API returned fewer days
    while len(forecasts) < num_days:
        forecasts.append(forecasts[-1] if forecasts else _fetch_weather(input_data, destination))

    # ── 2. Cultural context (fetched once for the destination) ───────────
    mid_date = start_date + datetime.timedelta(days=num_days // 2)
    cultural = _fetch_cultural_context(destination, mid_date.isoformat(), forecasts[0], occasion)

    # ── 3. Wardrobe + user preferences ─────────────────────────────────
    wardrobe_items = _get_wardrobe(user)
    user_prefs = _get_user_item_scores(user)

    # Track which wardrobe items have been used so we vary outfits per day
    used_item_ids = set()
    all_gaps = []

    day_plans = []
    for i in range(num_days):
        day_date = start_date + datetime.timedelta(days=i)
        weather = forecasts[i]

        # ML scoring for this day's weather
        ml_scores = _ml_category_scores(weather, occasion)
        ideal_outfit = _build_ideal_outfit(ml_scores, weather, cultural, occasion, day_index=i)

        # Filter wardrobe to prefer items not yet assigned
        available_items = [item for item in wardrobe_items if item["id"] not in used_item_ids]
        # Fall back to full wardrobe if we've used everything
        if not available_items:
            available_items = list(wardrobe_items)

        matches, gaps = _match_wardrobe(
            available_items, ideal_outfit, weather, day_index=i, user_prefs=user_prefs, cultural=cultural
        )

        if not wardrobe_items and not gaps:
            gaps = [
                {
                    "role": item["role"],
                    "ideal_category": item["category"],
                    "wardrobe_category": item.get("wardrobe_category", "other"),
                    "description": f"{item['category'].title()} for {item['role']}",
                    "why": "Your wardrobe is empty — here are recommended products.",
                }
                for item in ideal_outfit
            ]

        # Record used items
        for m in matches:
            used_item_ids.add(m["item"]["id"])

        all_gaps.extend(gaps)

        day_plans.append(
            {
                "day": i + 1,
                "date": day_date.isoformat(),
                "weather": weather,
                "outfit": {
                    "ideal_categories": ideal_outfit,
                    "score": _score_matched_outfit(matches),
                    "notes": _generate_outfit_notes(matches, gaps, weather, cultural, occasion),
                },
                "wardrobe_matches": matches,
                "gaps": gaps,
            }
        )

    # ── 4. Deduplicate gaps and generate shopping suggestions ────────────
    unique_gaps = _deduplicate_gaps(all_gaps)
    shopping = _build_shopping_suggestions(unique_gaps, destination, forecasts[0], cultural, occasion)

    return {
        "multi_day": True,
        "days": day_plans,
        "cultural": cultural,
        "shopping_suggestions": shopping,
        "metadata": {
            "signals_used": ["ml_compatibility", "weather_forecast", "cultural_ai"],
            "destination": destination,
            "occasion": occasion,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "num_days": num_days,
            "generated_at": datetime.datetime.now().isoformat(),
        },
    }


def _deduplicate_gaps(gaps: list) -> list:
    """Deduplicate gaps by role+category so we don't suggest the same item multiple times."""
    seen = set()
    unique = []
    for gap in gaps:
        key = (gap.get("role", ""), gap.get("ideal_category", ""))
        if key not in seen:
            seen.add(key)
            unique.append(gap)
    return unique


# ── Signal 1: Weather ────────────────────────────────────────────────────────


def _fetch_weather(input_data: dict, destination: str) -> dict:
    from ritha.services.weather import get_weather, get_weather_for_location

    if "weather" in input_data and isinstance(input_data["weather"], dict) and input_data["weather"]:
        return input_data["weather"]

    date_bucket = input_data.get("date") or datetime.date.today().isoformat()
    if "lat" in input_data and "lon" in input_data:
        lat = round(float(input_data["lat"]), 2)
        lon = round(float(input_data["lon"]), 2)
        key = _cache_key("weather_ll", lat, lon, date_bucket)
        hit = cache.get(key)
        if hit is not None:
            return hit
        result = get_weather(input_data["lat"], input_data["lon"])
        cache.set(key, result, _WEATHER_TTL)
        return result

    location = input_data.get("location", destination)
    key = _cache_key("weather_loc", location, date_bucket)
    hit = cache.get(key)
    if hit is not None:
        return hit
    result = get_weather_for_location(location)
    cache.set(key, result, _WEATHER_TTL)
    return result


# ── Signal 2: ML compatibility + weather scoring ─────────────────────────────


def _ml_category_scores(weather: dict, occasion: str) -> dict:
    """Combine ML compatibility matrix with weather appropriateness.

    Cached by (weather_bucket, occasion) — deterministic given those inputs.
    """
    bucket = _weather_bucket(weather)
    key = _cache_key("ml_scores", bucket, occasion)
    hit = cache.get(key)
    if hit is not None:
        return hit
    result = _ml_category_scores_compute(weather, occasion)
    cache.set(key, result, _CULTURAL_TTL)
    return result


def _ml_category_scores_compute(weather: dict, occasion: str) -> dict:
    try:
        from ml.categories import DATASET_CATEGORIES, OCCASION_FORMALITY
        from ml.inference import weather_appropriate_categories

        weather_scores = weather_appropriate_categories(weather)
        cat_scores = weather_scores["category_scores"]  # {category: 0..1}

        # Boost categories appropriate for the occasion
        formalities = OCCASION_FORMALITY.get(occasion, ["casual"])
        occasion_boosts = _occasion_category_boosts(occasion, formalities)

        # Final score = weather_score * 0.5 + occasion_boost * 0.3 + base * 0.2
        final = {}
        for cat in DATASET_CATEGORIES:
            w = cat_scores.get(cat, 0.5)
            o = occasion_boosts.get(cat, 0.5)
            final[cat] = round(w * 0.5 + o * 0.3 + 0.2, 3)

        return {
            "category_scores": final,
            "weather_bucket": weather_scores["weather_bucket"],
            "preferred": weather_scores["preferred"],
            "avoided": weather_scores["avoided"],
        }
    except FileNotFoundError:
        logger.warning("ML artifacts not found, using rule-based scoring only")
        return {"category_scores": {}, "weather_bucket": "mild", "preferred": [], "avoided": []}


def _occasion_category_boosts(occasion: str, formalities: list) -> dict:
    """Boost category scores based on occasion type."""
    from ml.categories import DATASET_CATEGORIES

    boosts = {cat: 0.5 for cat in DATASET_CATEGORIES}

    formal_cats = ["long sleeve top", "long sleeve dress", "trousers"]
    casual_cats = ["short sleeve top", "shorts", "vest", "skirt"]
    smart_cats = ["long sleeve top", "trousers", "short sleeve dress", "skirt"]
    active_cats = ["shorts", "vest", "short sleeve top"]

    if "formal" in formalities:
        for c in formal_cats:
            boosts[c] = 1.0
        for c in casual_cats:
            boosts[c] = 0.1
    elif "smart" in formalities or "casual_smart" in formalities:
        for c in smart_cats:
            boosts[c] = 0.9
    elif "activewear" in formalities:
        for c in active_cats:
            boosts[c] = 1.0
    else:
        for c in casual_cats:
            boosts[c] = 0.8

    return boosts


# ── Signal 3: Cultural context via Mistral ───────────────────────────────────


def _fetch_cultural_context(destination: str, date_str: str, weather: dict, occasion: str) -> dict:
    """Use Mistral to get cultural rules, events, etiquette, and places."""
    from ritha.services.mistral_client import _has_mistral

    if not _has_mistral():
        return _cultural_fallback(destination)

    # Cache by (canonical destination, month, occasion). Weather is intentionally
    # NOT in the key — cultural rules don't depend on temperature, and including
    # it fragmented the cache 3-4× per destination/month/occasion tuple.
    # Destination is normalized so "Tokyo" / "tokyo, japan" / "Tokyo Japan"
    # share a slot. The original string still goes to Mistral on a miss.
    month_bucket = (date_str or "")[:7]  # 'YYYY-MM'
    key = _cache_key("cultural", _normalize_destination(destination), month_bucket, occasion)
    hit = cache.get(key)
    if hit is not None:
        logger.info("cultural_cache_hit destination=%r month=%s", destination, month_bucket)
        return hit

    logger.info("cultural_cache_miss destination=%r month=%s", destination, month_bucket)
    try:
        result = _cultural_context_ai(destination, date_str, weather, occasion)
        cache.set(key, result, _CULTURAL_TTL)
        return result
    except Exception as exc:
        logger.warning("Cultural AI failed: %s", exc)
        return _cultural_fallback(destination)


def _weather_bucket(weather: dict) -> str:
    """Map a weather snapshot to a bucket for caching."""
    temp = weather.get("temp_c", 20) or 20
    wind = weather.get("wind_kmh", 0) or 0
    if temp < 0:
        band = "freezing"
    elif temp < 8:
        band = "cold"
    elif temp < 15:
        band = "cool"
    elif temp < 22:
        band = "mild"
    elif temp < 28:
        band = "warm"
    else:
        band = "hot"
    rain = "rain" if weather.get("is_raining") else "dry"
    windy = "_windy" if wind > 30 else ""
    return f"{band}_{rain}{windy}"


def _cultural_context_ai(destination: str, date_str: str, weather: dict, occasion: str) -> dict:
    from ritha.services.mistral_client import chat_json

    temp_desc = f"{weather.get('temp_c', 'unknown')}°C, {weather.get('condition', 'unknown')}"

    prompt = f"""You are Ritha, a culturally-aware travel fashion advisor.

Destination: {destination}
Date: {date_str}
Weather: {temp_desc}
Occasion: {occasion}

Return a JSON object with these exact keys:

{{
  "rules": [
    {{
      "type": "cover_shoulders | cover_knees | modest_dress | remove_shoes | color_warning | general",
      "description": "what the rule is",
      "severity": "required | warning | info",
      "applies_to": "where this applies (e.g. temples, mosques, churches)"
    }}
  ],
  "events": [
    {{
      "name": "event or festival name",
      "description": "brief description",
      "clothing_note": "what to wear or avoid",
      "date_range": "when it occurs"
    }}
  ],
  "highlights": [
    {{
      "name": "place or activity",
      "type": "landmark | restaurant | market | museum | nature",
      "description": "brief description",
      "clothing_tip": "what to wear there",
      "formality": "casual | smart_casual | formal"
    }}
  ],
  "general_tips": [
    "practical fashion tip for this destination and weather"
  ],
  "overall_dress_code": "brief summary of how locals dress"
}}

Include 3-5 rules (or fewer if the destination has few dress codes),
2-4 events happening around {date_str},
8-10 must-visit highlights with clothing advice,
and 3-5 general tips. Be specific to {destination}, not generic."""

    result = chat_json(prompt)

    from ritha.services.places import merge_highlights

    return {
        "rules": result.get("rules", []),
        "events": result.get("events", []),
        # Top up the AI list with curated places so every destination shows a
        # solid set (and de-dupes overlaps by name).
        "highlights": merge_highlights(result.get("highlights", []), destination),
        "general_tips": result.get("general_tips", []),
        "overall_dress_code": result.get("overall_dress_code", ""),
        "source": "ai",
    }


def _cultural_fallback(destination: str) -> dict:
    from ritha.services.places import fallback_highlights

    return {
        "rules": [],
        "events": [],
        # Curated places so the stub path (e.g. the demo, with no Mistral key)
        # still shows a rich places-to-visit list.
        "highlights": fallback_highlights(destination),
        "general_tips": [f"Check local dress codes before visiting {destination}."],
        "overall_dress_code": "No data available — check local guidelines.",
        "source": "fallback",
    }


# ── Ideal outfit builder ────────────────────────────────────────────────────


def _build_ideal_outfit(ml_scores: dict, weather: dict, cultural: dict, occasion: str, day_index: int = 0) -> list:
    """
    Determine the ideal outfit categories based on all three signals.
    Uses day_index to alternate outfit structures for variety across a week.
    Returns a list of {category, wardrobe_category, score, reason}.
    """
    from ml.categories import DATASET_TO_WARDROBE

    cat_scores = ml_scores.get("category_scores", {})

    tops = ["short sleeve top", "long sleeve top", "vest"]
    bottoms = ["trousers", "shorts", "skirt"]
    dresses = ["short sleeve dress", "long sleeve dress", "vest dress", "sling dress"]
    outerwear = ["long sleeve outwear", "short sleeve outwear"]
    extras = ["sling"]

    cultural_penalties = _cultural_penalties(cultural)
    hard_filters = _cultural_hard_filters(cultural)
    forbidden_dataset_cats = hard_filters["dataset_categories"]

    def adjusted_score(cat):
        if cat in forbidden_dataset_cats:
            return 0.0  # §3.3 — required cultural rule excludes this category
        base = cat_scores.get(cat, 0.5)
        penalty = cultural_penalties.get(cat, 0)
        return max(0, base - penalty)

    # Strip forbidden categories from each pool before ranking so the
    # outfit builder cannot pick them even as a desperate fallback.
    tops = [c for c in tops if c not in forbidden_dataset_cats]
    bottoms = [c for c in bottoms if c not in forbidden_dataset_cats]
    dresses = [c for c in dresses if c not in forbidden_dataset_cats]
    outerwear = [c for c in outerwear if c not in forbidden_dataset_cats]
    extras = [c for c in extras if c not in forbidden_dataset_cats]

    # Rank all options for each slot
    ranked_tops = sorted(tops, key=adjusted_score, reverse=True)
    ranked_bottoms = sorted(bottoms, key=adjusted_score, reverse=True)
    ranked_dresses = sorted(dresses, key=adjusted_score, reverse=True)

    # Use day_index to rotate through viable options instead of always picking #1
    def pick_rotated(ranked, day_idx):
        viable = [c for c in ranked if adjusted_score(c) > 0.15]
        if not viable:
            return ranked[0] if ranked else None
        return viable[day_idx % len(viable)]

    best_top = pick_rotated(ranked_tops, day_index)
    best_bottom = pick_rotated(ranked_bottoms, day_index)
    best_dress = pick_rotated(ranked_dresses, day_index)

    combo_a_score = (adjusted_score(best_top) + adjusted_score(best_bottom)) / 2 if best_top and best_bottom else 0
    combo_b_score = adjusted_score(best_dress) if best_dress else 0

    # Alternate between top+bottom and dress on different days when scores are close
    prefer_dress = False
    if combo_b_score > 0.15:
        score_diff = abs(combo_a_score - combo_b_score)
        if score_diff < 0.25:
            prefer_dress = day_index % 3 == 2
        elif combo_b_score > combo_a_score:
            prefer_dress = True

    outfit = []
    if prefer_dress and best_dress:
        outfit.append({"category": best_dress, "role": "dress", "score": adjusted_score(best_dress)})
    elif best_top and best_bottom:
        outfit.append({"category": best_top, "role": "top", "score": adjusted_score(best_top)})
        outfit.append({"category": best_bottom, "role": "bottom", "score": adjusted_score(best_bottom)})
    elif best_dress:
        outfit.append({"category": best_dress, "role": "dress", "score": adjusted_score(best_dress)})

    # Add outerwear if cold, rainy, or windy
    temp = weather.get("temp_c", 20)
    wind = weather.get("wind_kmh", 0) or 0
    if weather.get("is_cold") or weather.get("is_raining") or temp < 15 or wind > 35:
        ranked_outer = sorted(outerwear, key=adjusted_score, reverse=True)
        best_outer = pick_rotated(ranked_outer, day_index)
        if best_outer and adjusted_score(best_outer) > 0.2:
            outfit.append({"category": best_outer, "role": "outerwear", "score": adjusted_score(best_outer)})

    # Add accessory on some days for variety
    if day_index % 4 == 1 and extras:
        best_extra = max(extras, key=adjusted_score)
        if adjusted_score(best_extra) > 0.3:
            outfit.append({"category": best_extra, "role": "accessory", "score": adjusted_score(best_extra)})

    for item in outfit:
        item["wardrobe_category"] = DATASET_TO_WARDROBE.get(item["category"], "other")

    return outfit


def _cultural_penalties(cultural: dict) -> dict:
    """Penalize categories that conflict with cultural rules (warning/info)."""
    penalties = {}
    rules = cultural.get("rules", [])
    for rule in rules:
        rtype = rule.get("type", "")
        severity = rule.get("severity", "info")
        # `required` rules are now handled by `_cultural_hard_filters` (§3.3).
        # This soft path covers warning + info severity only.
        if severity == "required":
            continue
        penalty = {"warning": 0.3, "info": 0.1}.get(severity, 0.1)

        if rtype in ("cover_shoulders", "modest_dress"):
            penalties["vest"] = penalties.get("vest", 0) + penalty
            penalties["sling"] = penalties.get("sling", 0) + penalty
            penalties["sling dress"] = penalties.get("sling dress", 0) + penalty
        if rtype in ("cover_knees", "modest_dress"):
            penalties["shorts"] = penalties.get("shorts", 0) + penalty
            penalties["skirt"] = penalties.get("skirt", 0) + penalty

    return penalties


# ── §3.3 — Cultural rules as hard filters ────────────────────────────────────
# When a cultural rule has severity=='required' (e.g. shoulders covered in a
# specific religious site, modest dress mandated by local law), the
# corresponding categories are removed from candidate pools entirely. This
# is the difference between a tooltip the user has to read and a recommender
# that respects the constraint by construction.

# Maps cultural rule_type → dataset categories that violate that rule.
_HARD_FILTER_BY_RULE_TYPE = {
    "cover_shoulders": {"vest", "sling", "sling dress"},
    "cover_knees": {"shorts", "skirt"},
    "modest_dress": {"vest", "sling", "sling dress", "shorts", "skirt"},
    "no_bare_feet": set(),  # handled at wardrobe filter on footwear
}

# Wardrobe-side equivalents (Ritha categories) for filtering user-owned items.
# Empty set => no wardrobe-level filter for this rule type (the dataset-side
# filter is sufficient). 'tags' lookups are case-insensitive substring.
_HARD_FILTER_WARDROBE = {
    "cover_shoulders": {"tags": ["sleeveless", "tank", "spaghetti", "strapless"]},
    "cover_knees": {"categories": set(), "tags": ["shorts", "mini", "short skirt"]},
    # `modest_dress` is the union of cover_shoulders + cover_knees; if the
    # tag isn't blocked here it will be picked despite the required rule.
    "modest_dress": {
        "categories": set(),
        "tags": ["sleeveless", "tank", "spaghetti", "strapless", "shorts", "mini", "short skirt", "crop"],
    },
    "no_bare_feet": {"tags": ["sandal", "flip-flop", "slipper"]},
}


def _cultural_hard_filters(cultural: dict) -> dict:
    """Return the set of dataset categories and wardrobe filters that must
    be excluded due to severity='required' cultural rules.

    Returns:
        {
          'dataset_categories': set[str],   # categories to drop from ideal-outfit
          'wardrobe_tags':      set[str],   # lowercase tag substrings to exclude
          'reasons':            list[dict], # human-readable trace per filter applied
        }
    """
    forbidden_categories: set[str] = set()
    forbidden_tags: set[str] = set()
    reasons: list[dict] = []

    for rule in cultural.get("rules", []) or []:
        if (rule.get("severity") or "info") != "required":
            continue
        rtype = rule.get("type", "")
        if rtype in _HARD_FILTER_BY_RULE_TYPE:
            cats_for_rule = _HARD_FILTER_BY_RULE_TYPE[rtype]
            forbidden_categories.update(cats_for_rule)
        if rtype in _HARD_FILTER_WARDROBE:
            for tag in _HARD_FILTER_WARDROBE[rtype].get("tags", []):
                forbidden_tags.add(tag.lower())
        if rtype in _HARD_FILTER_BY_RULE_TYPE or rtype in _HARD_FILTER_WARDROBE:
            reasons.append(
                {
                    "rule_type": rtype,
                    "description": rule.get("description", ""),
                    "severity": "required",
                }
            )

    return {
        "dataset_categories": forbidden_categories,
        "wardrobe_tags": forbidden_tags,
        "reasons": reasons,
    }


def _wardrobe_passes_cultural_filter(item: dict, hard_filters: dict) -> bool:
    """True iff the wardrobe item is not blocked by any required cultural rule."""
    forbidden_tags = hard_filters.get("wardrobe_tags") or set()
    if not forbidden_tags:
        return True
    haystacks = []
    haystacks.append((item.get("name") or "").lower())
    for t in item.get("tags") or []:
        haystacks.append((t or "").lower())
    blob = " ".join(haystacks)
    return not any(bad in blob for bad in forbidden_tags)


# ── User preference scoring ─────────────────────────────────────────────────


def _get_user_item_scores(user) -> dict:
    """Load user's per-item acceptance scores from feedback history.
    Returns {item_id: float} where positive = preferred, negative = avoided.
    Cached for 10 minutes to avoid repeated DB hits within the same request batch.
    """
    cache_key = _cache_key("user_prefs", user.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from outfits.models import OutfitRecommendation

    recs = OutfitRecommendation.objects.filter(
        user=user,
        accepted__isnull=False,
    ).prefetch_related("outfititem_set")

    scores = {}
    for rec in recs:
        for oi in rec.outfititem_set.all():
            ci_id = oi.clothing_item_id
            if ci_id not in scores:
                scores[ci_id] = 0.0
            if rec.accepted:
                scores[ci_id] += 0.3
            else:
                scores[ci_id] -= 0.2
            if oi.liked is True:
                scores[ci_id] += 0.5
            elif oi.liked is False:
                scores[ci_id] -= 0.4

    cache.set(cache_key, scores, 600)
    return scores


# ── Wardrobe matching ────────────────────────────────────────────────────────


def _get_wardrobe(user) -> list:
    from wardrobe.images import attach_image_urls
    from wardrobe.models import ClothingItem

    items = list(
        ClothingItem.objects.filter(user=user, is_active=True).values(
            "id",
            "name",
            "category",
            "formality",
            "season",
            "colors",
            "tags",
            "weight_grams",
            "material",
            "brand",
            "image",
            "embedding",
        )
    )
    # `image_url` lets wardrobe_matches render the real garment photo in the UI.
    return attach_image_urls(items)


def _match_wardrobe(
    wardrobe_items: list,
    ideal_outfit: list,
    weather: dict,
    day_index: int = 0,
    user_prefs: dict = None,
    cultural: dict | None = None,
) -> tuple:
    """
    Match ideal outfit categories against user's wardrobe.
    Returns (matches, gaps).
    """
    from ml.categories import WARDROBE_TO_DATASET

    # §3.3 — drop wardrobe items that violate any required cultural rule
    # before they can be selected. The user's own bare-shoulder top is no
    # different from a recommendation that breaks the dress code.
    hard_filters = _cultural_hard_filters(cultural or {})
    if hard_filters["wardrobe_tags"]:
        wardrobe_items = [item for item in wardrobe_items if _wardrobe_passes_cultural_filter(item, hard_filters)]

    matches = []
    gaps = []
    used_colors = set()
    picked_items: list[dict] = []

    for ideal in ideal_outfit:
        target_wardrobe_cat = ideal.get("wardrobe_category", "other")
        target_dataset_cat = ideal.get("category", "")
        role = ideal.get("role", "main")

        # Find wardrobe items matching this category
        candidates = [item for item in wardrobe_items if item["category"] == target_wardrobe_cat]

        # Also check if any wardrobe item's dataset-mapped categories match
        if not candidates:
            candidates = [
                item for item in wardrobe_items if target_dataset_cat in WARDROBE_TO_DATASET.get(item["category"], [])
            ]

        if candidates:
            best = _pick_best_candidate(
                candidates,
                weather,
                ideal,
                used_colors=used_colors,
                day_index=day_index,
                user_prefs=user_prefs,
                picked_items=picked_items,
            )
            # Track colors used in this outfit for variety
            raw_colors = best.get("colors") or ""
            if isinstance(raw_colors, list):
                used_colors.update(c.lower().strip() for c in raw_colors if isinstance(c, str) and c.strip())
            elif isinstance(raw_colors, str) and raw_colors:
                used_colors.update(c.strip() for c in raw_colors.lower().split(",") if c.strip())
            picked_items.append(best)
            matches.append(
                {
                    # Drop the raw ML embedding from the API payload — it's a
                    # memoryview/bytes on Postgres (not JSON-serializable) and
                    # internal-only. picked_items keeps the full dict for scoring.
                    "item": {k: v for k, v in best.items() if k != "embedding"},
                    "role": role,
                    "ideal_category": target_dataset_cat,
                    "reason": f"Matches {role} — {target_dataset_cat} "
                    f"(weather: {weather.get('condition', 'N/A')}, "
                    f"{weather.get('temp_c', '?')}°C)",
                    "in_wardrobe": True,
                }
            )
        else:
            gaps.append(
                {
                    "role": role,
                    "ideal_category": target_dataset_cat,
                    "wardrobe_category": target_wardrobe_cat,
                    "description": f"{target_dataset_cat.title()} for {role}",
                    "why": f"No {target_wardrobe_cat} items in your wardrobe that fit the {role} role for this outfit.",
                }
            )

    return matches, gaps


def _pick_best_candidate(
    candidates: list,
    weather: dict,
    ideal: dict,
    used_colors: set = None,
    day_index: int = 0,
    user_prefs: dict = None,
    picked_items: list[dict] | None = None,
) -> dict:
    """Score wardrobe candidates and pick the best fit, favoring variety and user preferences.

    `picked_items` is the list of items already selected for this outfit
    (in slot order). When their embeddings are stored, each candidate gets
    a small bonus for being a coherent visual match and a penalty for
    being a near-duplicate of an already-picked item.
    """
    temp = weather.get("temp_c", 20)
    is_raining = weather.get("is_raining", False)
    used_colors = used_colors or set()

    # Pre-normalize picked items' embeddings once so the per-candidate inner
    # loop is just dot products. Items without stored embeddings are silently
    # excluded — the per-candidate signal degrades to 0 rather than failing.
    picked_embs = _normalized_embeddings(picked_items or [])

    def score(item):
        s = 0.0

        # Season match (0–1.0)
        season = item.get("season", "all")
        if season == "all":
            s += 0.5
        elif temp < 5 and season == "winter":
            s += 1.0
        elif temp > 28 and season == "summer":
            s += 1.0
        elif 5 <= temp < 15 and season in ("winter", "autumn"):
            s += 0.9
        elif 15 <= temp <= 25 and season in ("spring", "autumn"):
            s += 0.8
        elif temp > 25 and season in ("summer", "spring"):
            s += 0.9
        else:
            s += 0.2

        # Material suitability (0–0.5)
        material = (item.get("material") or "").lower()
        if temp < 10 and material in ("wool", "fleece", "cashmere", "leather"):
            s += 0.5
        elif temp > 25 and material in ("linen", "cotton", "silk", "rayon"):
            s += 0.5
        elif is_raining and material in ("polyester", "nylon", "gore-tex"):
            s += 0.4
        elif material:
            s += 0.2

        # Color harmony in CIELAB. Replaces the prior set-equality check.
        # Falls back to set-equality only when neither the candidate's nor
        # the outfit's colors are in our Lab table (truly unknown names).
        from ritha.services.color_harmony import (
            candidate_color_score,
            extract_colors,
        )

        colors = extract_colors(item)
        if used_colors and colors:
            harmony = candidate_color_score(colors, used_colors)
            if harmony is None:
                s += -0.3 if (colors & used_colors) else 0.2
            else:
                s += harmony

        # Wear count — prefer less-worn items for freshness
        wear_count = item.get("wear_count", 0) or 0
        s -= min(wear_count * 0.02, 0.3)

        # Day-based rotation: slight deterministic shuffle so day 1 and day 2
        # don't always pick the same top-scoring item
        item_hash = hash(item.get("id", 0)) % 100
        rotation_bonus = 0.15 if (item_hash % 7) == (day_index % 7) else 0
        s += rotation_bonus

        # User feedback preference: boost items the user has accepted before,
        # penalize items they've rejected
        if user_prefs:
            pref = user_prefs.get(item.get("id"), 0.0)
            s += max(min(pref, 0.8), -0.6)

        # Visual compatibility against already-picked items (Tier 4 — embedding
        # signal in selection, not just post-hoc scoring). Capped at ±0.20 to
        # stay comparable to the existing season/material weights; nothing
        # happens for items without stored embeddings, so this is safe to ship
        # before backfill completes.
        if picked_embs:
            s += _embedding_pair_delta(item, picked_embs)

        return s

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def _normalized_embeddings(items: list[dict]) -> list:
    """Return unit-norm float32 embeddings for items that have one."""
    import numpy as np

    out = []
    for it in items:
        blob = it.get("embedding")
        if not blob:
            continue
        try:
            v = np.frombuffer(blob, dtype=np.float32)
        except Exception:
            continue
        n = float(np.linalg.norm(v))
        if n == 0.0:
            continue
        out.append(v / n)
    return out


def _embedding_pair_delta(item: dict, picked_embs: list) -> float:
    """Score `item` against already-picked items via embedding cosine similarity.

    Mean cosine sim across picks is mapped through a sweet-spot function:
        sim ≈ 0.5  →  +0.20  (pleasing variety — different but related vibe)
        sim < 0.4  →  ~0.0   (unrelated — no signal either way)
        sim > 0.85 →  -0.20  (near-duplicate — penalize)

    Returns 0.0 when the candidate has no stored embedding.
    """
    import numpy as np

    blob = item.get("embedding")
    if not blob:
        return 0.0
    try:
        v = np.frombuffer(blob, dtype=np.float32)
    except Exception:
        return 0.0
    n = float(np.linalg.norm(v))
    if n == 0.0:
        return 0.0
    v = v / n

    sims = [float(np.dot(v, p)) for p in picked_embs]
    if not sims:
        return 0.0
    mean_sim = sum(sims) / len(sims)

    if mean_sim < 0.40:
        return 0.0
    if mean_sim > 0.85:
        return -0.20
    # Triangular peak at 0.5; max +0.20.
    return 0.20 * (1.0 - 2.0 * abs(mean_sim - 0.5))


# ── Outfit scoring ───────────────────────────────────────────────────────────


def _score_matched_outfit(matches: list) -> float:
    """Score the final matched outfit.

    Prefers item-level embedding compatibility (`score_outfit_by_embeddings`)
    when every picked item has a stored visual feature vector. Falls back to
    the 13×13 category co-occurrence matrix when any embedding is missing —
    the typical case for a freshly-onboarded user whose `compute_embeddings`
    backfill hasn't run yet.
    """
    in_wardrobe = [m for m in matches if m.get("in_wardrobe")]
    if len(in_wardrobe) < 2:
        return 1.0 if in_wardrobe else 0.0

    item_ids = [m["item"]["id"] for m in in_wardrobe if m.get("item", {}).get("id")]
    if len(item_ids) == len(in_wardrobe):
        try:
            from ml.inference import score_outfit_by_embeddings

            score = score_outfit_by_embeddings(item_ids)
            if score is not None:
                return round(score, 3)
        except Exception as exc:
            logger.warning("embedding scorer failed (%s); falling back to category matrix", exc)

    categories = [m.get("ideal_category", "") for m in in_wardrobe]
    try:
        from ml.inference import score_outfit

        return round(score_outfit(categories), 3)
    except FileNotFoundError:
        return 0.5


# ── Shopping recommendations ─────────────────────────────────────────────────


def _build_shopping_suggestions(gaps: list, destination: str, weather: dict, cultural: dict, occasion: str) -> list:
    """Generate specific product recommendations with shopping links for gaps."""
    if not gaps:
        return []

    # Cache by (destination, weather_bucket, occasion, gap-signature). Gap signature
    # is stable across users with the same missing categories.
    gap_sig = "|".join(sorted(f"{g.get('role', '')}:{g.get('ideal_category', '')}" for g in gaps))
    key = _cache_key("shopping", destination, _weather_bucket(weather), occasion, gap_sig)
    hit = cache.get(key)
    if hit is not None:
        # Re-stamp the cached suggestions with per-call `why` text from live gaps.
        return _restamp_shopping(hit, gaps)

    from ritha.services.mistral_client import _has_mistral

    if _has_mistral():
        try:
            result = _shopping_suggestions_ai(gaps, destination, weather, cultural, occasion)
            cache.set(key, result, _SHOPPING_TTL)
            return result
        except Exception as exc:
            logger.warning("AI shopping suggestions failed (%s): %s", type(exc).__name__, exc)

    result = _shopping_suggestions_fallback(gaps, destination, weather)
    cache.set(key, result, _SHOPPING_TTL)
    return result


def _restamp_shopping(cached: list, gaps: list) -> list:
    """Preserve per-request `why` text on cached shopping entries."""
    why_by_role = {g.get("role", "main"): g.get("why", "") for g in gaps}
    out = []
    for entry in cached:
        e = dict(entry)
        e["why"] = why_by_role.get(e.get("role", "main"), e.get("why", ""))
        out.append(e)
    return out


def _shopping_suggestions_ai(gaps: list, destination: str, weather: dict, cultural: dict, occasion: str) -> list:
    """Use Mistral to generate specific, relevant product recommendations."""
    import urllib.parse

    from ritha.services.mistral_client import chat_json

    gap_descriptions = [f"- {g['role']}: need a {g['ideal_category']} ({g.get('wardrobe_category', '')})" for g in gaps]
    temp = weather.get("temp_c", 20)
    condition = weather.get("condition", "mild")
    dress_code = cultural.get("overall_dress_code", "")
    tips = cultural.get("general_tips", [])
    tips_text = "; ".join(tips[:3]) if tips else "none"

    prompt = f"""You are Ritha, a fashion shopping advisor.

A user is traveling to {destination} for a {occasion} occasion.
Weather: {temp}°C, {condition}
Local dress code: {dress_code}
Cultural tips: {tips_text}

They are missing these items for a complete outfit:
{chr(10).join(gap_descriptions)}

For EACH missing item, recommend 2-3 specific products they should buy.
Return JSON:
{{
  "recommendations": [
    {{
      "role": "top / bottom / outerwear / dress",
      "products": [
        {{
          "name": "specific product name (e.g. 'Uniqlo AIRism Cotton Crew Neck T-Shirt')",
          "brand": "brand name",
          "description": "why this product fits the destination, weather, and occasion",
          "price_range": "$XX-$XX",
          "search_query": "exact search query to find this product online"
        }}
      ]
    }}
  ]
}}

Be specific with real brand names and actual products. Consider:
- Weather appropriateness ({temp}°C, {condition})
- Cultural requirements for {destination}
- The {occasion} occasion
- Quality and versatility for travel"""

    result = chat_json(prompt)
    recs = result.get("recommendations", [])

    # Merge AI product suggestions with shopping links
    suggestions = []
    for i, gap in enumerate(gaps):
        rec = recs[i] if i < len(recs) else {}
        products = rec.get("products", [])

        for product in products:
            query = product.get("search_query", product.get("name", gap["description"]))
            encoded = urllib.parse.quote_plus(query)

            suggestions.append(
                {
                    "name": product.get("name", gap["description"]),
                    "brand": product.get("brand", ""),
                    "description": product.get("description", ""),
                    "price_range": product.get("price_range", ""),
                    "role": gap.get("role", "main"),
                    "category": gap.get("wardrobe_category", "other"),
                    "why": gap.get("why", ""),
                    "links": {
                        "google_shopping": f"https://www.google.com/search?tbm=shop&q={encoded}",
                        "amazon": f"https://www.amazon.com/s?k={encoded}",
                        "asos": f"https://www.asos.com/search/?q={encoded}",
                    },
                }
            )

        # If AI returned no products for this gap, add a fallback
        if not products:
            query = f"{gap['ideal_category']} {occasion} {destination}"
            encoded = urllib.parse.quote_plus(query)
            suggestions.append(
                {
                    "name": f"{gap['ideal_category'].title()} for {occasion}",
                    "brand": "",
                    "description": f"A {gap['ideal_category']} suitable for {occasion} in {destination}.",
                    "price_range": "",
                    "role": gap.get("role", "main"),
                    "category": gap.get("wardrobe_category", "other"),
                    "why": gap.get("why", ""),
                    "links": {
                        "google_shopping": f"https://www.google.com/search?tbm=shop&q={encoded}",
                        "amazon": f"https://www.amazon.com/s?k={encoded}",
                        "asos": f"https://www.asos.com/search/?q={encoded}",
                    },
                }
            )

    return suggestions


def _shopping_suggestions_fallback(gaps: list, destination: str, weather: dict) -> list:
    """Rule-based shopping suggestions when AI is unavailable."""
    import urllib.parse

    temp = weather.get("temp_c", 20)
    suggestions = []

    for gap in gaps:
        cat = gap.get("ideal_category", "")
        role = gap.get("role", "main")

        # Generate a weather-appropriate search query
        if temp < 10:
            modifier = "warm winter"
        elif temp > 28:
            modifier = "lightweight breathable summer"
        else:
            modifier = "versatile"

        query = f"{modifier} {cat} {destination}"
        encoded = urllib.parse.quote_plus(query)

        suggestions.append(
            {
                "name": f"{modifier.title()} {cat.title()}",
                "brand": "",
                "description": f"A {modifier} {cat} suitable for {destination} "
                f"({weather.get('temp_c', '?')}°C, {weather.get('condition', 'unknown')}).",
                "price_range": "",
                "role": role,
                "category": gap.get("wardrobe_category", "other"),
                "why": gap.get("why", ""),
                "links": {
                    "google_shopping": f"https://www.google.com/search?tbm=shop&q={encoded}",
                    "amazon": f"https://www.amazon.com/s?k={encoded}",
                    "asos": f"https://www.asos.com/search/?q={encoded}",
                },
            }
        )

    return suggestions


# ── Notes generation ─────────────────────────────────────────────────────────


def _generate_outfit_notes(matches, gaps, weather, cultural, occasion) -> str:
    """Generate a human-readable outfit summary."""
    parts = []

    # Weather context
    temp = weather.get("temp_c", "?")
    cond = weather.get("condition", "unknown")
    parts.append(f"Weather: {temp}°C, {cond}.")

    # Outfit summary
    if matches:
        item_names = [m["item"]["name"] for m in matches]
        parts.append(f"Recommended from your wardrobe: {', '.join(item_names)}.")

    if gaps:
        gap_descs = [g["description"] for g in gaps]
        parts.append(f"You're missing: {', '.join(gap_descs)} — check the shopping links below.")

    # Cultural tips
    tips = cultural.get("general_tips", [])
    if tips:
        parts.append(f"Style tip: {tips[0]}")

    dress_code = cultural.get("overall_dress_code", "")
    if dress_code:
        parts.append(f"Local dress code: {dress_code}")

    return " ".join(parts)
