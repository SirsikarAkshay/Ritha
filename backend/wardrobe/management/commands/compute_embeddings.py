"""Backfill ClothingItem.embedding for items with images.

The recommendation engine prefers item-level visual compatibility over the
13-category co-occurrence matrix. That preference activates once an item has
a stored embedding. This command computes embeddings for every active item
that has an image but no stored vector — safe to run repeatedly, cheap when
there's nothing to do.

    python manage.py compute_embeddings                  # all active items
    python manage.py compute_embeddings --user 42        # one user only
    python manage.py compute_embeddings --recompute      # force overwrite
    python manage.py compute_embeddings --limit 100      # cap per run
"""
from __future__ import annotations

import logging
import time

import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Q

from wardrobe.models import ClothingItem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Compute ClothingItem.embedding for items missing one.'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, default=None,
                            help='Restrict to a single user id.')
        parser.add_argument('--limit', type=int, default=None,
                            help='Process at most N items this run.')
        parser.add_argument('--recompute', action='store_true',
                            help='Recompute embeddings even when already present.')

    def handle(self, *args, **opts):
        from ml.inference import get_embedding

        qs = ClothingItem.objects.filter(is_active=True).exclude(image='')
        if opts['user']:
            qs = qs.filter(user_id=opts['user'])
        if not opts['recompute']:
            qs = qs.filter(Q(embedding__isnull=True) | Q(embedding=b''))
        if opts['limit']:
            qs = qs[:opts['limit']]

        total = qs.count()
        if total == 0:
            self.stdout.write('Nothing to do.')
            return

        self.stdout.write(f'Computing embeddings for {total} item(s)…')
        ok = 0
        failed = 0
        t0 = time.time()
        for item in qs.iterator():
            try:
                # ImageFieldFile.path raises if the file moved or never existed
                # — treat as a soft skip rather than aborting the batch.
                path = item.image.path
            except (ValueError, FileNotFoundError):
                failed += 1
                continue
            try:
                emb = get_embedding(path).astype(np.float32)
                item.embedding = emb.tobytes()
                item.save(update_fields=['embedding'])
                ok += 1
            except Exception as exc:
                logger.warning('embedding failed for item %s: %s', item.id, exc)
                failed += 1

        elapsed = time.time() - t0
        self.stdout.write(
            f'Done. ok={ok} failed={failed} elapsed={elapsed:.1f}s '
            f'({elapsed / max(ok, 1):.2f}s/item)'
        )
