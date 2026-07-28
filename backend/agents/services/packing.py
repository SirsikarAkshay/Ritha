"""
Packing-list agent: capacity-aware packing picks for a trip.
"""

from agents.services._common import _has_mistral, _wardrobe_for_user

# Category priority when trimming to fit a bag — higher = keep first. Bottoms and
# footwear are hardest to improvise, so they outrank spare tops/accessories.
_PACKING_CATEGORY_PRIORITY = {
    "bottom": 5.0,
    "footwear": 4.5,
    "top": 4.0,
    "dress": 3.5,
    "outerwear": 3.0,
    "activewear": 2.5,
    "formal": 2.0,
    "accessory": 1.5,
    "other": 1.0,
}
_PACKING_NEUTRALS = {"black", "white", "navy", "grey", "gray", "beige", "tan", "denim", "blue", "brown", "cream"}


def _packing_value(item: dict) -> float:
    """Versatility score: how much a garment earns its space in the bag."""
    v = _PACKING_CATEGORY_PRIORITY.get(item.get("category"), 1.0)
    if item.get("season") in ("all", "spring", "autumn"):
        v += 0.5  # season-flexible pieces travel better
    colors = [str(c).lower() for c in (item.get("colors") or [])]
    if any(c in _PACKING_NEUTRALS for c in colors):
        v += 0.4  # neutrals mix with everything → more outfits per item
    tags = [str(t).lower() for t in (item.get("tags") or [])]
    if "travel" in tags:
        v += 0.2
    v -= 0.02 * (item.get("times_worn") or 0)
    return max(0.1, v)


def _fit_to_capacity(picks: list, capacity: float) -> tuple:
    """Greedy 0/1 fit: guarantee a wearable base, then fill by value density.

    Each pick carries `_vol` (packed liters) and `_value`. Returns (fitted, left_behind).
    """
    remaining = float(capacity)
    fitted, chosen = [], set()

    # 1) Guarantee a wearable base: best-value bottom, footwear, top (if each fits).
    for cat in ("bottom", "footwear", "top"):
        for p in sorted(
            (p for p in picks if p["category"] == cat and p["id"] not in chosen),
            key=lambda p: -p["_value"],
        ):
            if p["_vol"] <= remaining:
                fitted.append(p)
                chosen.add(p["id"])
                remaining -= p["_vol"]
                break

    # 2) Fill remaining space by value-per-liter.
    left_behind = []
    for p in sorted(
        (p for p in picks if p["id"] not in chosen),
        key=lambda p: -(p["_value"] / max(p["_vol"], 0.1)),
    ):
        if p["_vol"] <= remaining:
            fitted.append(p)
            chosen.add(p["id"])
            remaining -= p["_vol"]
        else:
            left_behind.append(p)

    # Restore original capsule order for stable output.
    order = {p["id"]: idx for idx, p in enumerate(picks)}
    fitted.sort(key=lambda p: order.get(p["id"], 0))
    return fitted, left_behind


def _packing_headline(days: int, capacity, location: str) -> str:
    if days >= 7 and days % 7 == 0:
        weeks = days // 7
        dur = f"{weeks} week{'s' if weeks != 1 else ''}"
    else:
        dur = f"{days} day{'s' if days != 1 else ''}"
    where = f" in {location}" if location else ""
    if capacity:
        return f"How to pack for {dur}{where} in a {int(capacity)}L bag"
    return f"How to pack for {dur}{where}"


def _finalize_packing(picks: list, days: int, capacity, location: str, status: str, base_note: str) -> dict:
    """Attach volumes, fit to bag capacity, and assemble the response."""
    from ml.categories import estimate_packed_volume_liters

    for p in picks:
        p["_vol"] = estimate_packed_volume_liters(p.get("category"), p.get("material", ""))
        p["_value"] = _packing_value(p)

    left_behind = []
    if capacity:
        fitted, left_behind = _fit_to_capacity(picks, capacity)
    else:
        fitted = picks

    def _clean(item: dict) -> dict:
        out = {k: v for k, v in item.items() if not k.startswith("_")}
        out["packed_volume_liters"] = item["_vol"]
        return out

    packing_list = [_clean(p) for p in fitted]
    left_list = [
        {"id": p["id"], "name": p["name"], "category": p["category"], "packed_volume_liters": p["_vol"]}
        for p in left_behind
    ]
    volume = round(sum(p["_vol"] for p in fitted), 1)
    weight = sum(p.get("weight_grams") or 0 for p in fitted)
    headline = _packing_headline(days, capacity, location)

    if capacity:
        util = round(100 * volume / capacity)
        notes = f"{headline}. {len(fitted)} items ≈ {volume}L ({util}% of {int(capacity)}L), {weight}g."
        if left_list:
            notes += f" {len(left_list)} item(s) left out to fit the bag."
    else:
        util = None
        notes = f"{base_note} Estimated {volume}L, {weight}g."

    return {
        "status": status,
        "headline": headline,
        "item_ids": [p["id"] for p in fitted],
        "packing_list": packing_list,
        "left_behind": left_list,
        "estimated_weight_grams": weight,
        "estimated_volume_liters": volume,
        "bag_capacity_liters": int(capacity) if capacity else None,
        "capacity_utilization_pct": util,
        "days": days,
        "notes": notes,
    }


def run_packing_list(user, input_data: dict) -> dict:
    days = int(input_data.get("days", 3))
    activities = input_data.get("activities", [])
    capacity = input_data.get("bag_capacity_liters") or None
    location = (input_data.get("location") or "").strip()
    wardrobe = _wardrobe_for_user(user)

    if not wardrobe:
        return {"status": "no_wardrobe", "message": "Add items to your wardrobe first."}

    if _has_mistral():
        picks, status = _packing_ai_picks(wardrobe, days, activities, capacity), "ai"
        if not picks:  # AI returned nothing usable → fall back to the heuristic
            picks, status = _packing_stub_picks(wardrobe, days, activities), "stub"
    else:
        picks, status = _packing_stub_picks(wardrobe, days, activities), "stub"

    return _finalize_packing(picks, days, capacity, location, status, f"5-4-3-2-1 capsule for {days} days.")


def _packing_stub_picks(wardrobe, days, activities) -> list:
    """5-4-3-2-1 capsule heuristic → ordered list of wardrobe item dicts."""
    targets = {"top": 5, "bottom": 4, "outerwear": 3, "footwear": 2, "accessory": 1}
    scale = min(2.0, 1.0 + (days - 3) * 0.1) if days > 3 else 1.0
    if any(a.lower() in ("gym", "hiking", "beach", "sport", "workout") for a in activities):
        targets["activewear"] = 2

    picks = []
    for cat, quota in targets.items():
        picks.extend([i for i in wardrobe if i["category"] == cat][: round(quota * scale)])
    return picks


def _packing_ai_picks(wardrobe, days, activities, capacity) -> list:
    """Ask Mistral to choose a capsule; return validated wardrobe dicts (or [])."""
    from ritha.services.mistral_client import chat_json

    cap_line = f"\nThe bag holds about {int(capacity)} liters — prefer versatile, packable pieces." if capacity else ""
    prompt = f"""You are Ritha, a packing expert. Choose a minimal capsule wardrobe using the
5-4-3-2-1 rule for a {days}-day trip with activities: {activities}.{cap_line}

Wardrobe: {wardrobe}

Return JSON: {{"item_ids": [ints], "notes": "..."}} using only ids from the wardrobe."""
    try:
        result = chat_json(prompt) or {}
    except Exception:
        return []
    by_id = {w["id"]: w for w in wardrobe}
    return [by_id[i] for i in (result.get("item_ids") or []) if i in by_id]
