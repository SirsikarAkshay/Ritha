"""Scorer that compares a recommended outfit against persona expectations.

Each persona's `expected` dict is a rubric. The scorer evaluates each rubric
key independently and returns:
    {
        'passed':   bool,           # all required checks passed
        'score':    float (0..1),   # fraction of soft+hard checks that passed
        'failures': list[str],      # human-readable failure descriptions
        'rubric':   dict,           # per-check pass/fail
    }

Hard checks (`must_*`, `forbid_*`) failing → `passed=False`.
Soft checks (`should_*`) failing → reduce `score` but don't fail the persona.
"""
from __future__ import annotations

# Ordered formality scale used for at_least / below comparisons.
_FORMALITY_RANK = {
    'activewear':   0,
    'casual':       1,
    'casual_smart': 2,
    'smart':        3,
    'formal':       4,
}


def _formality_rank(f: str | None) -> int:
    return _FORMALITY_RANK.get(f or 'casual', 1)


def score_outfit(picks: list[dict], expected: dict, full_outfit: dict | None = None) -> dict:
    """Score `picks` (list of chosen ClothingItem-shaped dicts) against rubric.

    `full_outfit` carries the wider response — used to inspect transitions
    (tier 1.5) since those don't live on the per-item picks.
    """
    failures: list[str] = []
    rubric: dict[str, bool] = {}
    soft_total = 0
    soft_passed = 0
    full_outfit = full_outfit or {}

    cats = {p['category'] for p in picks}
    formalities = {p.get('formality') for p in picks}
    seasons = {p.get('season') for p in picks}

    # A dress is a legitimate substitute for top+bottom in any rubric that
    # asks for them. Building this in once means personas don't need to
    # branch on dress-vs-separates every time.
    has_dress = 'dress' in cats
    cats_effective = cats | ({'top', 'bottom'} if has_dress else set())

    # ── must_include_category ────────────────────────────────────────────────
    for required_cat in expected.get('must_include_category', []):
        ok = required_cat in cats_effective
        rubric[f'must_include_category:{required_cat}'] = ok
        if not ok:
            failures.append(f"missing required category '{required_cat}' (got {sorted(cats)})")

    # ── must_include_formality_at_least ──────────────────────────────────────
    floor = expected.get('must_include_formality_at_least')
    if floor:
        floor_rank = _formality_rank(floor)
        ok = any(_formality_rank(f) >= floor_rank for f in formalities)
        rubric[f'must_include_formality_at_least:{floor}'] = ok
        if not ok:
            failures.append(f"no item meets formality floor '{floor}' (got {sorted(f or '∅' for f in formalities)})")

    # ── forbid_categories ────────────────────────────────────────────────────
    for forbidden in expected.get('forbid_categories', []):
        ok = forbidden not in cats
        rubric[f'forbid_categories:{forbidden}'] = ok
        if not ok:
            failures.append(f"forbidden category '{forbidden}' was picked")

    # ── forbid_seasonal ──────────────────────────────────────────────────────
    for bad_season in expected.get('forbid_seasonal', []):
        offenders = [p['name'] for p in picks if p.get('season') == bad_season]
        ok = not offenders
        rubric[f'forbid_seasonal:{bad_season}'] = ok
        if not ok:
            failures.append(f"picked {bad_season}-season items: {offenders}")

    # ── forbid_formality_below ───────────────────────────────────────────────
    floor_below = expected.get('forbid_formality_below')
    if floor_below:
        floor_rank = _formality_rank(floor_below)
        offenders = [p['name'] for p in picks if _formality_rank(p.get('formality')) < floor_rank]
        ok = not offenders
        rubric[f'forbid_formality_below:{floor_below}'] = ok
        if not ok:
            failures.append(f"items below formality floor '{floor_below}': {offenders}")

    # ── forbid_formality_above ───────────────────────────────────────────────
    ceiling = expected.get('forbid_formality_above')
    if ceiling:
        ceiling_rank = _formality_rank(ceiling)
        offenders = [p['name'] for p in picks if _formality_rank(p.get('formality')) > ceiling_rank]
        ok = not offenders
        rubric[f'forbid_formality_above:{ceiling}'] = ok
        if not ok:
            failures.append(f"items above formality ceiling '{ceiling}': {offenders}")

    # ── must_match_season_or_all ─────────────────────────────────────────────
    # (informational — surfaced as a soft check)
    if expected.get('must_match_season_or_all'):
        soft_total += 1
        ok = all(s in (None, 'all') or s for s in seasons)
        rubric['must_match_season_or_all'] = ok
        if ok:
            soft_passed += 1

    # ── should_include_outerwear / warm layer ────────────────────────────────
    if expected.get('should_include_outerwear'):
        soft_total += 1
        ok = 'outerwear' in cats
        rubric['should_include_outerwear'] = ok
        if ok:
            soft_passed += 1
        else:
            failures.append('soft: no outerwear picked despite rain/cold')

    if expected.get('should_include_warm_layer'):
        soft_total += 1
        warm = 'outerwear' in cats or any(
            'wool' in (p.get('material') or '').lower() or 'knit' in (p.get('name') or '').lower()
            for p in picks
        )
        rubric['should_include_warm_layer'] = warm
        if warm:
            soft_passed += 1
        else:
            failures.append('soft: no warm layer picked for cold day')

    if expected.get('should_prefer_summer'):
        soft_total += 1
        summer_count = sum(1 for s in seasons if s == 'summer')
        ok = summer_count >= 1
        rubric['should_prefer_summer'] = ok
        if ok:
            soft_passed += 1

    # ── Trip-day override: must_include_item_ids / must_exclude_item_ids ─────
    pick_ids = {p.get('id') for p in picks}
    for required_id in expected.get('must_include_item_ids', []):
        ok = required_id in pick_ids
        rubric[f'must_include_item_id:{required_id}'] = ok
        if not ok:
            failures.append(f"missing required item id {required_id} (got {sorted(pick_ids)})")
    for forbidden_id in expected.get('must_exclude_item_ids', []):
        ok = forbidden_id not in pick_ids
        rubric[f'must_exclude_item_id:{forbidden_id}'] = ok
        if not ok:
            failures.append(f"forbidden item id {forbidden_id} was picked")

    # ── §3.3 cultural hard filter: forbidden tagged items ────────────────────
    forbidden_tags = expected.get('forbid_tagged_items') or []
    if forbidden_tags:
        offenders = []
        for p in picks:
            blob = (p.get('name') or '').lower() + ' ' + ' '.join((p.get('tags') or [])).lower()
            for tag in forbidden_tags:
                if tag.lower() in blob:
                    offenders.append((p['name'], tag))
                    break
        ok = not offenders
        rubric['forbid_tagged_items'] = ok
        if not ok:
            failures.append(f"picked items with forbidden tags: {offenders}")

    # ── multi-context (transitions) — tier 1.5 ────────────────────────────────
    if expected.get('must_have_transitions'):
        transitions = (full_outfit or {}).get('outfit_transitions') or []
        min_count = expected.get('transition_count_at_least', 1)
        ok = len(transitions) >= min_count
        rubric['must_have_transitions'] = ok
        if not ok:
            failures.append(f'must_have_transitions: got {len(transitions)} (need ≥{min_count})')

    if expected.get('must_cover_formalities'):
        # Either base outfit OR transitions cover all listed formalities.
        covered = set(formalities)
        for t in (full_outfit or {}).get('outfit_transitions') or []:
            covered.update(t.get('formalities_covered') or [])
        for needed in expected['must_cover_formalities']:
            ok = needed in covered
            rubric[f'must_cover_formalities:{needed}'] = ok
            if not ok:
                failures.append(f"missing required formality '{needed}' across day (got {sorted(covered)})")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    hard_keys = [k for k in rubric if k.startswith(('must_', 'forbid_')) and not k.startswith('must_match_')]
    hard_passed = sum(1 for k in hard_keys if rubric[k])
    hard_total = len(hard_keys) or 1

    score = (hard_passed + soft_passed) / max(hard_total + soft_total, 1)
    passed = all(rubric[k] for k in hard_keys)

    return {
        'passed':   passed,
        'score':    round(score, 3),
        'failures': failures,
        'rubric':   rubric,
    }
