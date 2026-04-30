"""Eval-set regression tests for the deterministic recommender path.

Each persona produces an outfit via the stub recommender (no Mistral call),
and the result is scored against the persona's rubric. Failures here mean
the recommender regressed on a behavior we previously cared about.

Tier 1 (recency penalty), tier 1.5 (multi-context), and tier 2.1
(per-user weights) all add behaviors that should produce *new* passing
rubric checks; this file is the place to assert them.

Run:
    pytest backend/tests/test_recommendation_eval.py -v
"""
from __future__ import annotations

import datetime

import pytest

from ml.eval.personas import all_personas
from ml.eval.harness import score_outfit
from agents.services import _daily_look_stub, _build_outfit_transitions


def _resolve_picks(item_ids: list[int], wardrobe: list[dict]) -> list[dict]:
    by_id = {w['id']: w for w in wardrobe}
    return [by_id[i] for i in item_ids if i in by_id]


def _persona_required_formality(persona) -> str:
    """Highest formality across the persona's events; falls back to casual."""
    from ml.eval.harness import _formality_rank
    if not persona.events:
        return 'casual'
    ranked = sorted(persona.events, key=lambda e: _formality_rank(e.get('formality')), reverse=True)
    return ranked[0].get('formality') or 'casual'


@pytest.mark.parametrize('persona', all_personas(), ids=lambda p: p.name)
def test_persona_recommendation(persona):
    """Each persona must satisfy its rubric's hard checks."""
    required_formality = _persona_required_formality(persona)

    # §3.3 — apply cultural hard filter to wardrobe before the stub runs.
    # The recommendation engine does this for the multi-signal path; for
    # the stub path used in eval we pre-filter explicitly so the persona
    # exercises the same exclusion logic.
    wardrobe = persona.wardrobe
    cultural_rules = persona.expected.get('__cultural_rules')
    if cultural_rules:
        from ritha.services.recommendation_engine import (
            _cultural_hard_filters, _wardrobe_passes_cultural_filter,
        )
        hf = _cultural_hard_filters({'rules': cultural_rules})
        wardrobe = [w for w in wardrobe if _wardrobe_passes_cultural_filter(w, hf)]

    # Trip override: emulate run_daily_look's trip-day-plan branch. Real path
    # reads Trip.saved_recommendation from the DB; the eval injects the plan
    # directly so this can run pure-function.
    trip_plan = persona.expected.get('__trip_day_plan')
    if trip_plan:
        output = {
            'status':      'trip',
            'item_ids':    list(trip_plan['item_ids']),
            'notes':       f"From your trip to {trip_plan.get('destination', 'destination')}.",
            'destination': trip_plan.get('destination'),
        }
    else:
        output = _daily_look_stub(wardrobe, persona.weather, required_formality)

    # Tier 1.5: multi-context personas exercise the transitions builder.
    if persona.expected.get('must_have_transitions'):
        output['outfit_transitions'] = _build_outfit_transitions(
            persona.events, persona.wardrobe, persona.weather,
        )

    picks = _resolve_picks(output.get('item_ids', []), persona.wardrobe)

    result = score_outfit(picks, persona.expected, full_outfit=output)

    if not result['passed']:
        msg = f"\nPersona '{persona.name}' failed:\n  " + "\n  ".join(result['failures'])
        msg += f"\nPicks: {[p['name'] for p in picks]}"
        msg += f"\nRubric: {result['rubric']}"
        pytest.fail(msg)

    # Even when passed, surface soft-check details so regressions are visible.
    assert result['score'] >= 0.7, (
        f"Persona '{persona.name}' passed hard checks but soft score {result['score']} < 0.7. "
        f"Failures: {result['failures']}"
    )


def test_eval_summary(capsys):
    """Print a hit-rate summary; never fails. Useful for `pytest -s` runs."""
    personas = all_personas()
    pass_count = 0
    score_sum = 0.0
    for persona in personas:
        rf = _persona_required_formality(persona)
        trip_plan = persona.expected.get('__trip_day_plan')
        if trip_plan:
            out = {'status': 'trip', 'item_ids': list(trip_plan['item_ids']),
                   'notes': '', 'destination': trip_plan.get('destination')}
        else:
            out = _daily_look_stub(persona.wardrobe, persona.weather, rf)
        if persona.expected.get('must_have_transitions'):
            out['outfit_transitions'] = _build_outfit_transitions(
                persona.events, persona.wardrobe, persona.weather,
            )
        picks = _resolve_picks(out.get('item_ids', []), persona.wardrobe)
        result = score_outfit(picks, persona.expected, full_outfit=out)
        pass_count += 1 if result['passed'] else 0
        score_sum  += result['score']
        print(f"  {persona.name:24} pass={result['passed']!s:5} score={result['score']}")

    avg = score_sum / max(len(personas), 1)
    print(f"\nEval summary: {pass_count}/{len(personas)} passed, avg score {avg:.3f}")
