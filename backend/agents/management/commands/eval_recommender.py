"""Compare rule-based vs Mistral outfit selection on the persona eval set.

Runs every persona through `_daily_look_stub` and `_daily_look_mistral`,
scores each with the existing rubric, prints a side-by-side table.

Mistral responses are cached to disk under `ml/eval/_mistral_cache/` so
re-runs are free. Pass --no-cache to force fresh calls.

    python manage.py eval_recommender
    python manage.py eval_recommender --stub-only
    python manage.py eval_recommender --no-cache
    python manage.py eval_recommender --json out.json
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from ml.eval.personas import all_personas, adversarial_personas
from ml.eval.harness import score_outfit, _formality_rank
from agents.services import (
    _daily_look_stub,
    _daily_look_mistral,
    _build_outfit_transitions,
    _has_mistral,
)


CACHE_DIR = Path(__file__).resolve().parents[3] / 'ml' / 'eval' / '_mistral_cache'


def _resolve_picks(item_ids, wardrobe):
    by_id = {w['id']: w for w in wardrobe}
    return [by_id[i] for i in item_ids if i in by_id]


def _persona_required_formality(persona):
    if not persona.events:
        return 'casual'
    ranked = sorted(persona.events,
                    key=lambda e: _formality_rank(e.get('formality')),
                    reverse=True)
    return ranked[0].get('formality') or 'casual'


def _run_stub(persona, required_formality):
    trip_plan = persona.expected.get('__trip_day_plan')
    if trip_plan:
        return {
            'status':      'trip',
            'item_ids':    list(trip_plan['item_ids']),
            'notes':       '',
            'destination': trip_plan.get('destination'),
        }
    cultural_rules = persona.expected.get('__cultural_rules')
    cultural = {'rules': cultural_rules} if cultural_rules else None
    return _daily_look_stub(persona.wardrobe, persona.weather, required_formality,
                            cultural=cultural)


def _run_mistral(persona, required_formality, use_cache=True):
    # Mirror run_daily_look: trip-plan override short-circuits before any
    # selection model runs. Without this branch, Mistral would be asked to
    # pick a daily look while a saved trip plan should win — a production
    # behavior the eval needs to model accurately.
    trip_plan = persona.expected.get('__trip_day_plan')
    if trip_plan:
        return {
            'status':      'trip',
            'item_ids':    list(trip_plan['item_ids']),
            'notes':       '',
            'destination': trip_plan.get('destination'),
        }

    cache_path = CACHE_DIR / f'{persona.name}.json'
    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text())
    cultural_rules = persona.expected.get('__cultural_rules')
    cultural = {'rules': cultural_rules} if cultural_rules else None
    result = _daily_look_mistral(
        None, persona.wardrobe, persona.events, persona.weather, required_formality,
        cultural=cultural,
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2, default=str))
    return result


def _score_one(persona, output):
    if persona.expected.get('must_have_transitions'):
        output['outfit_transitions'] = _build_outfit_transitions(
            persona.events, persona.wardrobe, persona.weather,
        )
    picks = _resolve_picks(output.get('item_ids', []), persona.wardrobe)
    return score_outfit(picks, persona.expected, full_outfit=output), picks


class Command(BaseCommand):
    help = 'Compare rule-based vs Mistral outfit selection on the persona set.'

    def add_arguments(self, parser):
        parser.add_argument('--stub-only',     action='store_true')
        parser.add_argument('--mistral-only',  action='store_true')
        parser.add_argument('--no-cache',      action='store_true')
        parser.add_argument('--no-adversarial', action='store_true',
                            help='Skip adversarial personas (gap-tracking cases).')
        parser.add_argument('--json', type=str, default=None,
                            help='Write full results to JSON path.')

    def handle(self, *args, **opts):
        run_stub    = not opts['mistral_only']
        run_mistral = not opts['stub_only'] and _has_mistral()

        if opts['mistral_only'] and not _has_mistral():
            self.stderr.write('Mistral unavailable — set MISTRAL_API_KEY or drop --mistral-only.')
            return

        if not opts['stub_only'] and not _has_mistral():
            self.stdout.write('(Mistral unavailable — running stub only.)')

        golden_rows = self._run_group(
            all_personas(), run_stub, run_mistral, use_cache=not opts['no_cache'],
        )
        self.stdout.write('\n=== Golden personas ===')
        self._print_table(golden_rows, run_stub, run_mistral)
        self._print_summary(golden_rows, run_stub, run_mistral)
        self._print_disagreements(golden_rows, run_stub, run_mistral)

        adversarial_rows = []
        if not opts['no_adversarial']:
            adversarial_rows = self._run_group(
                adversarial_personas(), run_stub, run_mistral, use_cache=not opts['no_cache'],
            )
            self.stdout.write('\n=== Adversarial personas (gap tracking — failures expected) ===')
            self._print_table(adversarial_rows, run_stub, run_mistral)
            self._print_summary(adversarial_rows, run_stub, run_mistral)
            self._print_failure_detail(adversarial_rows, run_stub, run_mistral)

        if opts['json']:
            Path(opts['json']).write_text(json.dumps(
                {'golden': golden_rows, 'adversarial': adversarial_rows},
                indent=2, default=str,
            ))
            self.stdout.write(f'\nWrote {opts["json"]}')

    def _run_group(self, personas, run_stub, run_mistral, use_cache):
        rows = []
        for persona in personas:
            rf = _persona_required_formality(persona)
            row = {'persona': persona.name, 'required_formality': rf}

            if run_stub:
                out = _run_stub(persona, rf)
                result, picks = _score_one(persona, out)
                row['stub'] = {
                    'passed':   result['passed'],
                    'score':    result['score'],
                    'picks':    [p['name'] for p in picks],
                    'failures': result['failures'],
                }

            if run_mistral:
                try:
                    out = _run_mistral(persona, rf, use_cache=use_cache)
                    result, picks = _score_one(persona, out)
                    row['mistral'] = {
                        'passed':   result['passed'],
                        'score':    result['score'],
                        'picks':    [p['name'] for p in picks],
                        'failures': result['failures'],
                    }
                except Exception as exc:
                    row['mistral'] = {
                        'passed':   False,
                        'score':    0.0,
                        'picks':    [],
                        'failures': [f'error: {type(exc).__name__}: {exc}'],
                    }

            rows.append(row)
        return rows

    def _print_failure_detail(self, rows, run_stub, run_mistral):
        for r in rows:
            lines = []
            if run_stub and not r['stub']['passed']:
                lines += [f"    stub picks: {r['stub']['picks']}"]
                lines += [f"    stub fail : {f}" for f in r['stub']['failures']]
            if run_mistral and not r['mistral']['passed']:
                lines += [f"    mistral picks: {r['mistral']['picks']}"]
                lines += [f"    mistral fail : {f}" for f in r['mistral']['failures']]
            if lines:
                self.stdout.write(f"  {r['persona']}")
                for ln in lines:
                    self.stdout.write(ln)

    def _print_table(self, rows, run_stub, run_mistral):
        cols = [('persona', 28)]
        if run_stub:
            cols += [('stub', 6), ('stub_score', 12)]
        if run_mistral:
            cols += [('mistral', 9), ('mistral_score', 15)]

        self.stdout.write('')
        self.stdout.write(''.join(name.ljust(w) for name, w in cols))
        self.stdout.write('-' * sum(w for _, w in cols))
        for r in rows:
            parts = [r['persona'].ljust(cols[0][1])]
            if run_stub:
                s = r['stub']
                parts.append(('PASS' if s['passed'] else 'FAIL').ljust(6))
                parts.append(f"{s['score']:.3f}".ljust(12))
            if run_mistral:
                m = r['mistral']
                parts.append(('PASS' if m['passed'] else 'FAIL').ljust(9))
                parts.append(f"{m['score']:.3f}".ljust(15))
            self.stdout.write(''.join(parts))

    def _print_summary(self, rows, run_stub, run_mistral):
        n = len(rows)
        self.stdout.write('')
        if run_stub:
            p = sum(1 for r in rows if r['stub']['passed'])
            avg = sum(r['stub']['score'] for r in rows) / max(n, 1)
            self.stdout.write(f'Stub:    {p}/{n} passed  avg score {avg:.3f}')
        if run_mistral:
            p = sum(1 for r in rows if r['mistral']['passed'])
            avg = sum(r['mistral']['score'] for r in rows) / max(n, 1)
            self.stdout.write(f'Mistral: {p}/{n} passed  avg score {avg:.3f}')

    def _print_disagreements(self, rows, run_stub, run_mistral):
        if not (run_stub and run_mistral):
            return
        diffs = [r for r in rows if r['stub']['passed'] != r['mistral']['passed']]
        if not diffs:
            return
        self.stdout.write('\nDisagreements:')
        for r in diffs:
            winner = 'mistral' if r['mistral']['passed'] else 'stub'
            self.stdout.write(f"  {r['persona']:28}  winner={winner}")
            loser = r['stub'] if winner == 'mistral' else r['mistral']
            for f in loser['failures'][:3]:
                self.stdout.write(f"    - {f}")
