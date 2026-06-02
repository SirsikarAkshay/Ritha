"""Attach deterministic placeholder images to dev wardrobe items.

Each item without an image gets a unique 224×224 photo from picsum.photos,
seeded by item id so the same item always gets the same image across runs.
The resulting embeddings won't be fashion-realistic, but they're diverse
enough to exercise the selection-time embedding signal end-to-end in dev.

This command refuses to run when DEBUG is False — picsum images aren't
appropriate as production wardrobe content.

    python manage.py seed_wardrobe_images               # all items missing image
    python manage.py seed_wardrobe_images --user 42     # one user
    python manage.py seed_wardrobe_images --limit 20    # cap per run
    python manage.py seed_wardrobe_images --reseed      # overwrite existing
"""
from __future__ import annotations

import io
import logging

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from wardrobe.models import ClothingItem

logger = logging.getLogger(__name__)

PICSUM_URL = 'https://picsum.photos/seed/{seed}/224/224'


class Command(BaseCommand):
    help = 'Seed dev ClothingItem rows with placeholder images.'

    def add_arguments(self, parser):
        parser.add_argument('--user',   type=int, default=None)
        parser.add_argument('--limit',  type=int, default=None)
        parser.add_argument('--reseed', action='store_true',
                            help='Replace any existing image with a fresh one.')

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError(
                'seed_wardrobe_images is dev-only — refusing to run with DEBUG=False.'
            )

        qs = ClothingItem.objects.filter(is_active=True)
        if opts['user']:
            qs = qs.filter(user_id=opts['user'])
        if not opts['reseed']:
            qs = qs.filter(image='')
        if opts['limit']:
            qs = qs[:opts['limit']]

        total = qs.count()
        if total == 0:
            self.stdout.write('Nothing to do.')
            return

        self.stdout.write(f'Seeding {total} item(s) with placeholder images…')
        ok = 0
        failed = 0
        for item in qs.iterator():
            url = PICSUM_URL.format(seed=f'ritha-{item.id}')
            try:
                r = requests.get(url, timeout=15, allow_redirects=True)
                r.raise_for_status()
            except Exception as exc:
                logger.warning('item %s: download failed (%s)', item.id, exc)
                failed += 1
                continue

            try:
                item.image.save(f'dev_{item.id}.jpg', ContentFile(r.content), save=True)
                ok += 1
            except Exception as exc:
                logger.warning('item %s: save failed (%s)', item.id, exc)
                failed += 1

        self.stdout.write(f'Done. ok={ok} failed={failed}')
