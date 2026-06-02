"""Print the cosine-similarity distribution across stored item embeddings.

Used for calibrating the thresholds in `recommendation_engine._embedding_pair_delta`
(currently 0.40 floor / 0.85 duplicate penalty / peak at 0.50). The natural
distribution shifts with the underlying image content — picsum scenic photos
in dev sit much lower than real clothing photos in prod — so the right
thresholds aren't fixed; they should track the data.

Run periodically against representative wardrobes:

    python manage.py embedding_distribution                  # all users
    python manage.py embedding_distribution --user 42        # single user
    python manage.py embedding_distribution --by-category    # within vs across
"""
from __future__ import annotations

import numpy as np
from django.core.management.base import BaseCommand

from wardrobe.models import ClothingItem


# Mirrors the bands hard-coded in recommendation_engine._embedding_pair_delta —
# update both together when retuning.
_FLOOR    = 0.40
_PEAK     = 0.50
_DUP_FLAG = 0.85


def _quantiles(values: np.ndarray) -> dict:
    if values.size == 0:
        return {}
    return {
        'count':  int(values.size),
        'min':    float(values.min()),
        'p10':    float(np.quantile(values, 0.10)),
        'p25':    float(np.quantile(values, 0.25)),
        'median': float(np.quantile(values, 0.50)),
        'p75':    float(np.quantile(values, 0.75)),
        'p90':    float(np.quantile(values, 0.90)),
        'p99':    float(np.quantile(values, 0.99)),
        'max':    float(values.max()),
    }


def _zone_occupancy(values: np.ndarray) -> dict:
    if values.size == 0:
        return {}
    return {
        f'< {_FLOOR}':            float((values < _FLOOR).mean()),
        f'{_FLOOR}–{_DUP_FLAG}':  float(((values >= _FLOOR) & (values <= _DUP_FLAG)).mean()),
        f'> {_DUP_FLAG}':         float((values > _DUP_FLAG).mean()),
    }


class Command(BaseCommand):
    help = 'Print cosine-similarity distribution across stored item embeddings.'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, default=None,
                            help='Restrict analysis to a single user id.')
        parser.add_argument('--by-category', action='store_true',
                            help='Split into within-category vs cross-category pairs.')

    def handle(self, *args, **opts):
        qs = ClothingItem.objects.exclude(embedding__isnull=True).exclude(embedding=b'')
        if opts['user']:
            qs = qs.filter(user_id=opts['user'])

        rows = list(qs.values('id', 'category', 'embedding'))
        if len(rows) < 2:
            self.stdout.write(f'Need ≥2 items with embeddings; got {len(rows)}.')
            return

        embs = np.stack([np.frombuffer(r['embedding'], dtype=np.float32) for r in rows])
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms

        sims = embs @ embs.T
        iu = np.triu_indices_from(sims, k=1)
        all_pairs = sims[iu]

        self.stdout.write(f'Items with embeddings: {len(rows)}'
                          f'{" (user " + str(opts["user"]) + ")" if opts["user"] else ""}')
        self._print_distribution('All pairs', all_pairs)

        if opts['by_category']:
            cats = np.array([r['category'] for r in rows])
            same_cat = cats[iu[0]] == cats[iu[1]]
            self._print_distribution('Within-category pairs',  all_pairs[same_cat])
            self._print_distribution('Cross-category pairs',   all_pairs[~same_cat])

    def _print_distribution(self, label: str, values: np.ndarray):
        self.stdout.write('')
        self.stdout.write(f'── {label} ──')
        q = _quantiles(values)
        if not q:
            self.stdout.write('  (no pairs)')
            return
        self.stdout.write(f"  count   : {q['count']}")
        for k in ('min', 'p10', 'p25', 'median', 'p75', 'p90', 'p99', 'max'):
            self.stdout.write(f"  {k:7} : {q[k]:.3f}")
        self.stdout.write('  zone occupancy (cosine):')
        for band, frac in _zone_occupancy(values).items():
            self.stdout.write(f"    {band:14}: {100 * frac:5.1f}%")
