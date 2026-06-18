"""Builds and applies per-user style profiles (§2.1).

`rebuild_for_user(user)` scans recent OutfitRecommendation + OutfitItem feedback
and produces a UserStyleProfile snapshot. Cheap to rerun (a few hundred ms per
user with thousands of feedback rows), so it's safe to schedule nightly.

`apply(score, item_a, item_b, profile)` is the hook recommendation engines
call at scoring time to bias by the user's learned preferences.

Why a snapshot table instead of computing on the fly:
  - Recommendation paths are latency-sensitive; we don't want to scan history
    for every recommend() call.
  - Snapshots are easy to inspect for debugging ("why does the model think
    user X dislikes navy?") and reset (just delete the row).
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from outfits.models import UserStyleProfile

# History window for rebuilding. 90 days lets us catch seasonal preference
# shifts without diluting recent signal with year-old data.
_HISTORY_DAYS = 90

# Weights are clamped to a reasonable range so a single bad streak can't
# permanently exclude a category combination.
_WEIGHT_MIN = 0.5
_WEIGHT_MAX = 1.5


def _clamp(x: float) -> float:
    return max(_WEIGHT_MIN, min(_WEIGHT_MAX, x))


def rebuild_for_user(user) -> UserStyleProfile:
    """(Re)compute and persist the user's style profile snapshot."""
    from wardrobe.models import ClothingItem

    from outfits.models import OutfitItem, OutfitRecommendation, UserStyleProfile

    cutoff = timezone.now() - timedelta(days=_HISTORY_DAYS)
    recs = (
        OutfitRecommendation.objects.filter(user=user, created_at__gte=cutoff)
        .exclude(accepted__isnull=True)
        .prefetch_related("outfititem_set__clothing_item")
    )

    # ── Category-pair weights ────────────────────────────────────────────────
    pair_pos: Counter = Counter()
    pair_neg: Counter = Counter()
    feedback_count = 0

    for rec in recs:
        items = list(rec.outfititem_set.all())
        if not items:
            continue
        feedback_count += 1
        cats = sorted({(oi.clothing_item.category or "other") for oi in items})
        for i, a in enumerate(cats):
            for b in cats[i + 1 :]:
                if rec.accepted is True:
                    pair_pos[(a, b)] += 1
                elif rec.accepted is False:
                    pair_neg[(a, b)] += 1

    pair_weights = {}
    for key in set(pair_pos) | set(pair_neg):
        pos = pair_pos[key]
        neg = pair_neg[key]
        total = pos + neg
        if total < 2:  # too little signal to act on
            continue
        # Wilson-style smoothed ratio centered at 1.0
        ratio = (pos + 1) / (total + 2)  # 0..1
        weight = 0.7 + (ratio * 0.6)  # ~0.7..1.3
        pair_weights[f"{key[0]}|{key[1]}"] = round(_clamp(weight), 3)

    # ── Item-pair negatives ──────────────────────────────────────────────────
    # If the user has rejected the same exact pair (item_a, item_b) ≥2 times,
    # remember it as a hard negative.
    item_pair_neg: Counter = Counter()
    for rec in recs.filter(accepted=False):
        ids = sorted({oi.clothing_item_id for oi in rec.outfititem_set.all()})
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                item_pair_neg[(a, b)] += 1
    hard_negatives = [list(k) for k, count in item_pair_neg.items() if count >= 2]

    # ── Color affinities ─────────────────────────────────────────────────────
    color_likes: Counter = Counter()
    color_total: Counter = Counter()
    for oi in OutfitItem.objects.filter(outfit__user=user, outfit__created_at__gte=cutoff):
        item = oi.clothing_item
        for color in item.colors or []:
            color_total[color] += 1
            if oi.liked is True or (oi.liked is None and oi.outfit.accepted is True):
                color_likes[color] += 1

    color_affinities = {}
    for color, total in color_total.items():
        likes = color_likes[color]
        if total < 2:
            continue
        ratio = likes / total
        weight = 0.8 + (ratio * 0.4)  # 0.8..1.2
        color_affinities[color] = round(_clamp(weight), 3)

    # ── Formality distribution (prior) ───────────────────────────────────────
    # Computed from active wardrobe, not feedback — reflects what the user
    # actually owns, useful when feedback is sparse.
    formality_counts = Counter(
        ClothingItem.objects.filter(user=user, is_active=True).values_list("formality", flat=True)
    )
    total_items = sum(formality_counts.values()) or 1
    formality_dist = {f: round(c / total_items, 3) for f, c in formality_counts.items()}

    profile, _created = UserStyleProfile.objects.update_or_create(
        user=user,
        defaults={
            "category_pair_weights": pair_weights,
            "item_pair_negatives": hard_negatives,
            "color_affinities": color_affinities,
            "formality_distribution": formality_dist,
            "feedback_count": feedback_count,
            "last_rebuilt": timezone.now(),
        },
    )
    return profile


def apply_to_score(base_score: float, item: dict, other_picks: list[dict], profile) -> float:
    """Apply per-user biases to a candidate item's score.

    `item` is the candidate; `other_picks` are items already chosen for the
    same outfit (used to look up category-pair and item-pair weights).
    `profile` is a UserStyleProfile (or None — passes through).
    """
    if profile is None:
        return base_score

    s = base_score

    # Category-pair weights
    cpw = profile.category_pair_weights or {}
    for other in other_picks:
        a = item.get("category") or "other"
        b = other.get("category") or "other"
        key = "|".join(sorted([a, b]))
        if key in cpw:
            s *= cpw[key]

    # Item-pair hard negatives
    item_id = item.get("id")
    if item_id is not None:
        for pair in profile.item_pair_negatives or []:
            if item_id in pair:
                other_id_in_pair = pair[1] if pair[0] == item_id else pair[0]
                if any(o.get("id") == other_id_in_pair for o in other_picks):
                    s *= 0.5  # strong down-rank, not exclusion

    # Color affinities
    ca = profile.color_affinities or {}
    for color in item.get("colors") or []:
        if color in ca:
            s *= ca[color]

    return s


def get_or_empty(user):
    """Return the user's style profile or a sentinel-shaped empty if none exists."""
    from outfits.models import UserStyleProfile

    try:
        return UserStyleProfile.objects.get(user=user)
    except UserStyleProfile.DoesNotExist:
        return None
