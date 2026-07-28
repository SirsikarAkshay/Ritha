"""
Daily-look agent: calendar-aware outfit for a single day (+ trip-day awareness).
"""

import datetime

from agents.services._common import _get_weather, _has_mistral, _today_str, _wardrobe_for_user

# ── Outfit reasoning ──────────────────────────────────────────────────────────
# Produces a list of one-line "why" bullets that explain a recommendation.
# Runs *after* item selection so it works for both Mistral- and stub-picked
# outfits. The frontend can render these in a "Why this outfit?" panel.
#
# Each reasoning entry is a dict so the UI can group / icon by type:
#   {"type": "weather"|"calendar"|"formality"|"wear_balance"|"culture", "text": "..."}
#
# Bullets are deterministic — same inputs produce the same explanation. No LLM
# call here; that would defeat the cost win from §1.5.


def _explain_outfit(
    picks_ids: list,
    wardrobe: list,
    weather: dict | None,
    events: list,
    required_formality: str,
    trip: dict | None = None,
) -> list[dict]:
    if not picks_ids:
        return []

    by_id = {w["id"]: w for w in (wardrobe or [])}
    chosen = [by_id[i] for i in picks_ids if i in by_id]
    if not chosen:
        return []

    bullets: list[dict] = []
    weather = weather or {}

    # ── Trip context (highest-priority bullet) ───────────────────────────────
    if trip:
        dest = trip.get("destination") or trip.get("name") or "your trip"
        bullets.append(
            {"type": "trip", "text": f"You're traveling — pulled this outfit from your saved plan for {dest}."}
        )

    # ── Weather rationale ─────────────────────────────────────────────────────
    temp = weather.get("temperature_c")
    if weather.get("is_raining"):
        bullets.append({"type": "weather", "text": "Rain expected — picked layers you can shed indoors."})
    elif weather.get("is_cold"):
        if temp is not None:
            bullets.append(
                {"type": "weather", "text": f"Cold day ({round(temp)}°C) — chose warmer fabrics and outerwear."}
            )
        else:
            bullets.append({"type": "weather", "text": "Cold day — chose warmer fabrics and outerwear."})
    elif weather.get("is_hot"):
        if temp is not None:
            bullets.append({"type": "weather", "text": f"Warm day ({round(temp)}°C) — kept it light and breathable."})
        else:
            bullets.append({"type": "weather", "text": "Warm day — kept it light and breathable."})

    # ── Calendar / formality rationale ───────────────────────────────────────
    formal_event = next(
        (e for e in (events or []) if (e.get("formality") or "") in ("formal", "smart", "casual_smart")),
        None,
    )
    if formal_event and required_formality in ("formal", "smart", "casual_smart"):
        title = (formal_event.get("title") or "a meeting").strip()
        bullets.append(
            {
                "type": "calendar",
                "text": f'"{title}" on your calendar — chose pieces that read {required_formality.replace("_", " ")}.',
            }
        )
    elif required_formality and required_formality != "casual":
        bullets.append(
            {
                "type": "formality",
                "text": f"Today's plan calls for {required_formality.replace('_', ' ')} — selected accordingly.",
            }
        )

    # ── Wear-balance rationale ───────────────────────────────────────────────
    # Surface the least-worn item among the picks. Reactivates dormant wardrobe.
    with_counts = [c for c in chosen if c.get("times_worn") is not None]
    if with_counts:
        least = min(with_counts, key=lambda c: c.get("times_worn") or 0)
        worn = least.get("times_worn") or 0
        if worn <= 2:
            name = least.get("name") or least.get("category", "this item")
            bullets.append(
                {"type": "wear_balance", "text": f"Featured your {name} — you've only worn it {worn}× recently."}
            )

    # ── Wardrobe completeness ────────────────────────────────────────────────
    cats = {c.get("category") for c in chosen}
    has_outerwear = "outerwear" in cats
    if (weather.get("is_cold") or weather.get("is_raining")) and not has_outerwear:
        bullets.append(
            {"type": "weather", "text": "No outerwear in your wardrobe matched today — consider adding a jacket."}
        )

    return bullets


# ── Recency penalty (§1.1) ────────────────────────────────────────────────────
# Items worn very recently get a sliding score penalty so the recommender stops
# suggesting the same outfit two days running. The penalty is multiplicative on
# the item's selection score (1.0 = no change, 0.0 = exclude).

_RECENCY_PENALTY_DAYS = {0: 0.15, 1: 0.30, 2: 0.55, 3: 0.80}
_RECENCY_DEFAULT = 1.00  # 4+ days ago → no penalty


def _recency_factor(item: dict, today: datetime.date | None = None) -> float:
    last = item.get("last_worn")
    if not last:
        return _RECENCY_DEFAULT
    today = today or datetime.date.today()
    if isinstance(last, str):
        try:
            last = datetime.date.fromisoformat(last)
        except ValueError:
            return _RECENCY_DEFAULT
    delta = (today - last).days
    if delta < 0:
        return _RECENCY_DEFAULT
    return _RECENCY_PENALTY_DAYS.get(delta, _RECENCY_DEFAULT)


def _wear_balance_factor(item: dict, wardrobe: list[dict]) -> float:
    """Boost items worn ≤2× recently. Reactivates dormant wardrobe items."""
    worn = item.get("times_worn") or 0
    if worn <= 2:
        return 1.15
    if worn <= 5:
        return 1.05
    return 1.00


def _recently_worn_ids(wardrobe: list[dict], days: int = 3, today: datetime.date | None = None) -> list[int]:
    today = today or datetime.date.today()
    out = []
    for item in wardrobe:
        last = item.get("last_worn")
        if not last:
            continue
        if isinstance(last, str):
            try:
                last = datetime.date.fromisoformat(last)
            except ValueError:
                continue
        if (today - last).days < days:
            out.append(item["id"])
    return out


# ── Multi-context day solver (§1.5) ──────────────────────────────────────────
# When the day's calendar spans multiple distinct formality buckets (gym at 6,
# office at 10, dinner at 7), a single base outfit cannot cover all contexts.
# This builder produces a list of `transitions` — small, actionable swaps the
# user can do mid-day without re-dressing entirely.
#
# The output is intentionally minimal: each transition names a time, a swap
# (item to put on / take off), and the formality target it satisfies. The
# frontend renders this as a timeline below the base outfit.

_FORMALITY_RANK_INTERNAL = {
    "activewear": 0,
    "casual": 1,
    "casual_smart": 2,
    "smart": 3,
    "formal": 4,
}

# Two formalities are "distinct" if their rank differs by ≥2 (e.g. activewear
# vs. smart). Rank-1 differences (smart vs. formal, casual vs. casual_smart)
# are usually handleable with the same outfit + minor accessory swap, not a
# full transition.
_TRANSITION_THRESHOLD = 2


def _build_outfit_transitions(events: list[dict], wardrobe: list[dict], weather: dict | None) -> list[dict]:
    if not events:
        return []

    # Sort events chronologically and bucket by formality.
    def _start(e):
        return e.get("start_time") or ""

    events_sorted = sorted(events, key=_start)

    formalities_present = {e.get("formality") or "casual" for e in events_sorted}
    if len(formalities_present) < 2:
        return []

    ranks = [_FORMALITY_RANK_INTERNAL.get(f, 1) for f in formalities_present]
    if (max(ranks) - min(ranks)) < _TRANSITION_THRESHOLD:
        return []

    # Index wardrobe by category for swap lookups.
    by_category: dict[str, list[dict]] = {}
    for item in wardrobe:
        by_category.setdefault(item.get("category"), []).append(item)

    def _best_for(formality: str, category: str) -> dict | None:
        pool = by_category.get(category, [])
        if not pool:
            return None
        # Prefer exact formality match, then nearest formality.
        target_rank = _FORMALITY_RANK_INTERNAL.get(formality, 1)
        ranked = sorted(
            pool,
            key=lambda i: (
                0 if (i.get("formality") == formality) else 1,
                abs(_FORMALITY_RANK_INTERNAL.get(i.get("formality"), 1) - target_rank),
                -1 * _wear_balance_factor(i, wardrobe),  # tie-break: under-worn first
            ),
        )
        return ranked[0]

    # The base outfit is built for the day's dominant (highest) formality,
    # not the chronologically first one. Anything else needs a transition,
    # whether it occurs before or after the dominant event.
    base_formality = max(
        (e.get("formality") or "casual" for e in events_sorted),
        key=lambda f: _FORMALITY_RANK_INTERNAL.get(f, 1),
    )

    transitions: list[dict] = []
    seen_formalities: set[str] = set()
    for ev in events_sorted:
        formality = ev.get("formality") or "casual"
        if formality == base_formality or formality in seen_formalities:
            continue
        seen_formalities.add(formality)

        picks: dict[str, dict] = {}
        for cat in ("top", "bottom", "footwear", "outerwear"):
            best = _best_for(formality, cat)
            if best:
                picks[cat] = best

        if not picks:
            continue

        when = (ev.get("start_time") or "")[11:16] or "—"
        title = (ev.get("title") or formality.replace("_", " ")).strip()

        # Build a human-readable swap description.
        swap_parts = []
        for cat, item in picks.items():
            swap_parts.append(f"{cat}: {item.get('name', cat)}")

        transitions.append(
            {
                "time": when,
                "event_title": title,
                "target_formality": formality,
                "formalities_covered": [formality],
                "swap_to": [
                    {"category": cat, "item_id": item["id"], "item_name": item.get("name", cat)}
                    for cat, item in picks.items()
                ],
                "description": f'At {when} for "{title}": switch to {", ".join(swap_parts)}',
            }
        )

    return transitions


def _today_events(user):
    from itinerary.models import CalendarEvent

    today = datetime.date.today()
    return list(
        CalendarEvent.objects.filter(user=user, start_time__date=today).values(
            "id", "title", "event_type", "formality", "start_time", "end_time", "location"
        )
    )


# ── Daily Look ────────────────────────────────────────────────────────────────


def _active_trip_day_plan(user, target_date: datetime.date):
    """If `target_date` falls inside an active trip with a saved recommendation,
    return (trip, day_plan_dict). Otherwise (None, None).

    A "day plan" is the per-day entry inside Trip.saved_recommendation['day_plans']
    produced by run_outfit_planner. If the trip exists but has no matching day
    in its plan (e.g. plan was generated before dates were extended), we still
    return the trip with a None day_plan so the caller can include trip context
    in the response without forcing the items.

    Multiple overlapping trips are unusual but possible (e.g. a long trip with
    a side trip): the trip with the latest start_date wins so the more-specific
    plan takes priority.
    """
    from itinerary.models import Trip

    trips = (
        Trip.objects.filter(user=user, start_date__lte=target_date, end_date__gte=target_date)
        .exclude(saved_recommendation__isnull=True)
        .order_by("-start_date")
    )
    for trip in trips:
        rec = trip.saved_recommendation or {}
        for plan in rec.get("day_plans") or []:
            if plan.get("date") == target_date.isoformat():
                return trip, plan
        # Trip exists but no exact day match — surface the trip anyway so the
        # daily-look output can show "you're on a trip" context.
        return trip, None
    return None, None


def run_daily_look(user, input_data: dict) -> dict:
    """
    Generate today's outfit and persist an OutfitRecommendation record.

    Trip override: if `today` falls inside a saved trip plan, the items from
    that trip's day plan win over the wardrobe-based algorithm. The dashboard
    can then show "From your Paris trip" instead of a generic daily look.
    """
    from itinerary.models import CalendarEvent
    from outfits.models import OutfitItem, OutfitRecommendation
    from ritha.services.event_classifier import dominant_formality
    from wardrobe.models import ClothingItem

    # Allow cron jobs to generate looks for a specific date
    _date_str = input_data.get("_target_date")
    today = datetime.date.fromisoformat(_date_str) if _date_str else datetime.date.today()
    # Use user's saved location if not overridden in input_data
    if "weather" not in input_data and "location" not in input_data and "lat" not in input_data:
        if user.location_name:
            input_data = {**input_data, "location": user.location_name}
        elif user.location_lat and user.location_lon:
            input_data = {**input_data, "lat": user.location_lat, "lon": user.location_lon}
    weather = _get_weather(input_data)
    wardrobe = _wardrobe_for_user(user)
    events = _today_events(user)

    if not wardrobe:
        return {
            "status": "no_wardrobe",
            "message": "Add at least one item to your wardrobe to get a daily look.",
            "weather": weather,
        }

    # Determine required formality from today's calendar
    event_objs = CalendarEvent.objects.filter(user=user, start_time__date=today)
    required_formality = dominant_formality(list(event_objs))

    # ── Trip override ────────────────────────────────────────────────────────
    # If today is inside an active trip with a saved day plan, use that plan's
    # items as the daily look. Drop items the user has since deleted from
    # wardrobe so a stale plan doesn't surface ghost item IDs.
    trip, day_plan = _active_trip_day_plan(user, today)
    output = None
    rec_source = "daily"
    rec_trip = None

    if trip and day_plan:
        plan_ids = list(day_plan.get("item_ids") or [])
        if plan_ids:
            valid_ids = list(
                ClothingItem.objects.filter(id__in=plan_ids, user=user, is_active=True).values_list("id", flat=True)
            )
            if valid_ids:
                day_label = day_plan.get("day") or "?"
                notes = (
                    f"From your trip to {trip.destination or trip.name} "
                    f"(day {day_label} of {(trip.end_date - trip.start_date).days + 1})."
                )
                if day_plan.get("notes"):
                    notes = f"{notes} {day_plan['notes']}"
                output = {
                    "status": "trip",
                    "item_ids": valid_ids,
                    "notes": notes,
                    "trip_id": trip.id,
                    "trip_name": trip.name,
                    "destination": trip.destination,
                }
                rec_source = "trip"
                rec_trip = trip

    # ── Standard daily-look path ─────────────────────────────────────────────
    if output is None:
        # §2.1 — load the user's learned style profile (None if not yet built).
        from outfits.style_profile import get_or_empty as _get_style_profile

        style_profile = _get_style_profile(user)

        # Cultural rules for the user's home location, if set. The trip path
        # (above) doesn't need this — saved trip plans were already generated
        # with cultural filtering at trip time.
        cultural = _daily_look_cultural(user, today, weather)

        if _has_mistral():
            output = _daily_look_mistral(user, wardrobe, events, weather, required_formality, cultural=cultural)
        else:
            output = _daily_look_stub(
                wardrobe, weather, required_formality, style_profile=style_profile, cultural=cultural
            )

        # If a trip exists for today but had no day-plan match, surface it
        # as context so the dashboard can show "you're on a trip" without
        # overriding the recommendation.
        if trip is not None:
            output["trip_id"] = trip.id
            output["trip_name"] = trip.name
            output["destination"] = trip.destination

    # Persist OutfitRecommendation. (date, source) is the natural key — a user
    # could have BOTH a 'daily' and a 'trip' record for the same day if they
    # generate the daily look before AND after saving a trip recommendation,
    # so we look up by both fields not just by date.
    rec, _created = OutfitRecommendation.objects.get_or_create(
        user=user,
        date=today,
        source=rec_source,
        defaults={
            "notes": output.get("notes", ""),
            "weather_snapshot": weather,
            "trip": rec_trip,
        },
    )
    if not _created:
        rec.notes = output.get("notes", "")
        rec.weather_snapshot = weather
        if rec.trip_id != (rec_trip.id if rec_trip else None):
            rec.trip = rec_trip
        rec.save()

    # Attach clothing items
    item_ids = output.get("item_ids", [])
    if item_ids:
        rec.outfititem_set.all().delete()
        items = ClothingItem.objects.filter(id__in=item_ids, user=user)
        OutfitItem.objects.bulk_create([OutfitItem(outfit=rec, clothing_item=item, role="main") for item in items])

    output["recommendation_id"] = rec.id
    output["source"] = rec_source
    output["required_formality"] = required_formality
    output["weather"] = weather
    output["reasoning"] = _explain_outfit(
        item_ids,
        wardrobe,
        weather,
        events,
        required_formality,
        trip={"destination": trip.destination, "name": trip.name} if trip else None,
    )
    output["outfit_transitions"] = _build_outfit_transitions(events, wardrobe, weather)
    return output


def _daily_look_cultural(user, today: datetime.date, weather: dict) -> dict | None:
    """Fetch cultural rules for the user's home location, or None if unset.

    The result is cached for 30 days inside `_fetch_cultural_context`, so a
    given user/location/month tuple costs at most one Mistral call. Without a
    location we can't ask sensibly — return None and let callers behave as
    if no cultural constraints apply.
    """
    destination = getattr(user, "location_name", None) or (
        f"{user.location_lat},{user.location_lon}"
        if getattr(user, "location_lat", None) and getattr(user, "location_lon", None)
        else None
    )
    if not destination:
        return None

    from ritha.services.recommendation_engine import _fetch_cultural_context

    try:
        return _fetch_cultural_context(destination, today.isoformat(), weather, "casual")
    except Exception:
        # Cultural context is best-effort. A failure here must not break the
        # daily look — proceed without rules rather than 500 the request.
        return None


def _daily_look_stub(wardrobe, weather, required_formality, style_profile=None, cultural: dict | None = None) -> dict:
    """Pick best-matching items deterministically (no LLM call).

    Scoring layers (each multiplies the item's score):
        - formality match            (1.5 if exact, 0.6 otherwise)
        - season match               (1.3 if seasonal or 'all', 0.5 otherwise)
        - recency penalty (§1.1)     — items worn in last 3 days down-ranked
        - wear-balance boost (§1.2)  — under-worn items lifted slightly
        - per-user style profile (§2.1) — category-pair / item-pair / color
          biases applied during slot selection

    `cultural` (optional): same shape as in `recommendation_engine.recommend()`.
    Items violating any `severity == 'required'` rule are removed from the
    candidate pool before scoring (§3.3 — hard filter, not a scoring penalty).
    """
    if cultural:
        from ritha.services.recommendation_engine import (
            _cultural_hard_filters,
            _wardrobe_passes_cultural_filter,
        )

        hf = _cultural_hard_filters(cultural)
        if hf.get("wardrobe_tags"):
            wardrobe = [w for w in wardrobe if _wardrobe_passes_cultural_filter(w, hf)]

    is_cold = weather.get("is_cold", False)
    is_hot = weather.get("is_hot", False)
    is_raining = weather.get("is_raining", False)

    season_hint = "winter" if is_cold else ("summer" if is_hot else "all")
    today = datetime.date.today()

    def _score(item):
        s = 1.0
        s *= 1.5 if item.get("formality") == required_formality else 0.6
        s *= 1.3 if item.get("season") in (season_hint, "all") else 0.5
        s *= _recency_factor(item, today)
        s *= _wear_balance_factor(item, wardrobe)
        return s

    # Score every item, then assemble an outfit by category slots so the
    # core (top + bottom + footwear OR dress + footwear) is always covered
    # before secondary slots (outerwear, activewear, accessory) compete.
    scored = sorted(wardrobe, key=_score, reverse=True)

    # Profile biases (§2.1) are applied per-slot, not in the base score,
    # so they only kick in once we know what's already been picked.
    _apply_profile = None
    if style_profile is not None:
        from outfits.style_profile import apply_to_score as _apply_profile

    def _slot_score(it, current_picks):
        s = _score(it)
        if _apply_profile and current_picks:
            s = _apply_profile(s, it, current_picks, style_profile)
        if current_picks:
            from ritha.services.color_harmony import (
                candidate_color_score,
                extract_colors,
            )

            used = set()
            for p in current_picks:
                used |= extract_colors(p)
            cand = extract_colors(it)
            if used and cand:
                harmony = candidate_color_score(cand, used)
                if harmony is None:
                    s *= 1.1 if not (cand & used) else 0.85
                else:
                    s *= 1.0 + harmony
        return s

    def _best_in(current_picks, *categories) -> dict | None:
        ranked = sorted(
            (it for it in scored if it.get("category") in categories),
            key=lambda it: _slot_score(it, current_picks),
            reverse=True,
        )
        for it in ranked:
            if _slot_score(it, current_picks) >= 0.15:
                return it
        return ranked[0] if ranked else None

    picks: list[dict] = []
    seen_ids: set = set()

    def _add(item):
        if item and item["id"] not in seen_ids:
            picks.append(item)
            seen_ids.add(item["id"])

    # Prefer a dress over top+bottom when one fits the day's formality/weather.
    dress = _best_in(picks, "dress")
    if dress and _score(dress) >= 1.5:  # only if it's a strong fit
        _add(dress)
    else:
        _add(_best_in(picks, "top"))
        _add(_best_in(picks, "bottom"))

    _add(_best_in(picks, "footwear"))

    # Cold / wet day → outerwear is part of the core outfit, not a bonus.
    if (is_cold or is_raining) and len(picks) < 4:
        _add(_best_in(picks, "outerwear"))

    # If the day's events specifically need an extra (e.g. activewear for a
    # gym block), the multi-context transitions builder handles it. Don't
    # double up here.

    # Final fallback: tiny wardrobe couldn't fill core slots → take whatever.
    if not picks:
        picks = scored[:3]

    notes = f"Outfit for a {required_formality} day"
    if is_cold:
        notes += " — it's cold, so layers are recommended"
    elif is_hot:
        notes += " — it's warm, so light fabrics are best"
    if is_raining:
        notes += ". Don't forget a waterproof layer!"

    return {
        "status": "stub",
        "item_ids": [i["id"] for i in picks],
        "notes": notes,
    }


def _daily_look_mistral(user, wardrobe, events, weather, required_formality, cultural: dict | None = None) -> dict:
    """LLM-driven outfit selection.

    `cultural` (optional) is the same shape as the cultural-context dict used
    by `recommendation_engine.recommend()` — `{'rules': [{type, severity, ...}]}`.
    When present, items violating any `severity == 'required'` rule are pruned
    from the wardrobe *before* the prompt is built (defense in depth — the
    prompt also forbids them in plain English).
    """
    from ritha.services.mistral_client import chat_json
    from ritha.services.recommendation_engine import (
        _cultural_hard_filters,
        _wardrobe_passes_cultural_filter,
    )

    hard = _cultural_hard_filters(cultural or {})
    forbidden_tags = hard.get("wardrobe_tags") or set()
    if forbidden_tags:
        wardrobe = [w for w in wardrobe if _wardrobe_passes_cultural_filter(w, hard)]

    avoid_ids = _recently_worn_ids(wardrobe, days=3)
    underworn_ids = [i["id"] for i in wardrobe if (i.get("times_worn") or 0) <= 2]

    events_summary = _summarize_events_for_prompt(events)
    multi_context = _has_multi_context_day(events)

    cultural_block = ""
    cultural_inline = ""
    if forbidden_tags or hard.get("reasons"):
        rule_lines = (
            "\n".join(f"- {r.get('description', r.get('rule_type', 'rule'))}" for r in hard.get("reasons", []))
            or "- (cultural rules apply)"
        )
        cultural_block = (
            f"\nCultural constraints — REQUIRED, not optional:\n{rule_lines}\n"
            f"The Wardrobe below is already filtered to remove violating items; "
            f"trust the list and do not invent IDs.\n"
        )
        if forbidden_tags:
            cultural_inline = (
                f"- Hard rule: never pick an item whose name or tags contain any of: {sorted(forbidden_tags)}"
            )

    multi_context_guidance = ""
    if multi_context:
        multi_context_guidance = (
            f"- The day has events at different formality levels. The system handles "
            f"activewear/workout transitions separately — focus on ONE outfit for the "
            f"highest-formality event ({required_formality}). Do NOT include gym or "
            f"workout items; they are added by a separate transitions builder."
        )

    prompt = f"""You are Ritha, a personal AI stylist.

Date              : {_today_str()}
Weather           : {weather}
Required formality: {required_formality}   (the day's highest-formality event)
Today's events    : {events_summary}
Wardrobe          : {wardrobe}
Recently worn     : {avoid_ids}        # avoid — worn in the last 3 days
Under-worn        : {underworn_ids}        # prefer when otherwise tied
{cultural_block}
Pick ONE outfit:

- Use only item IDs from the Wardrobe above
- 2-4 items spanning top + bottom + footwear (or dress + footwear), optional outerwear
- Match the required formality ({required_formality})
- Prefer season- and weather-appropriate items
- Avoid items in `Recently worn` unless no alternative exists
- Prefer `Under-worn` items when otherwise tied
{multi_context_guidance}
{cultural_inline}
- Give a concise explanation (max 2 sentences)

Return JSON: {{"item_ids": [1, 2, 3], "notes": "...", "layer_swap": "optional tip"}}"""
    result = chat_json(prompt)
    result["status"] = "ai"
    return result


def _summarize_events_for_prompt(events: list[dict]) -> str:
    if not events:
        return "(no events)"
    lines = []
    for e in events:
        t = (e.get("start_time") or "")[11:16] or "?"
        title = e.get("title", "")
        formality = e.get("formality", "?")
        lines.append(f"{t} {title} ({formality})")
    return "; ".join(lines)


def _has_multi_context_day(events: list[dict]) -> bool:
    if len(events or []) < 2:
        return False
    ranks = {_FORMALITY_RANK_INTERNAL.get(e.get("formality", "casual"), 1) for e in events}
    return (max(ranks) - min(ranks)) >= _TRANSITION_THRESHOLD
