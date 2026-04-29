"""
Seed RegionCluster + StarterPackItem rows from wardrobe/data/starter_packs.yaml.

Usage:
    python manage.py seed_starter_packs            # idempotent upsert
    python manage.py seed_starter_packs --reset    # wipe and re-seed (preserves apps)

The YAML file is the single source of truth. Re-run this command after editing
the YAML; existing rows are upserted by (region_cluster, gender, subcategory).
"""
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand
from django.db import transaction

from wardrobe.models import RegionCluster, StarterPackItem


DATA_PATH = Path(__file__).resolve().parents[2] / 'data' / 'starter_packs.yaml'

# ClothingItem.CATEGORY_CHOICES values that have a matching default SVG bundled
# at frontend/public/wardrobe-defaults/<category>.svg. Categories outside this
# set fall back to 'other.svg'.
_CATEGORY_SVG_AVAILABLE = {
    'top', 'bottom', 'dress', 'outerwear', 'footwear',
    'accessory', 'activewear', 'formal', 'other',
}


def category_default_image(category: str) -> str:
    """Return the path to the bundled default SVG for a given category.

    The SVGs live under frontend/public/wardrobe-defaults/ and are served from
    the SPA origin, so the URL is path-relative (no scheme/host). This avoids
    any external CDN dependency.
    """
    cat = category if category in _CATEGORY_SVG_AVAILABLE else 'other'
    return f'/wardrobe-defaults/{cat}.svg'


class Command(BaseCommand):
    help = 'Load starter pack regions and items from starter_packs.yaml'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete all StarterPackItem rows before seeding (RegionClusters preserved)',
        )

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if not DATA_PATH.exists():
            self.stderr.write(f'Data file not found: {DATA_PATH}')
            return

        data = yaml.safe_load(DATA_PATH.read_text())
        regions = data.get('regions', [])
        items = data.get('items', [])

        self.stdout.write(f'▸ Loading {len(regions)} regions, {len(items)} items')

        # ── Regions ──────────────────────────────────────────────────────────
        region_map = {}
        for r in regions:
            obj, created = RegionCluster.objects.update_or_create(
                code=r['code'],
                defaults={
                    'display_name':     r['display_name'],
                    'climate_zone':     r['climate_zone'],
                    'cultural_cluster': r['cultural_cluster'],
                    'country_codes':    r.get('country_codes', []),
                    'notes':            r.get('notes', ''),
                },
            )
            region_map[r['code']] = obj
            self.stdout.write(f'  {"+" if created else "·"} region {r["code"]}')

        # ── Items ────────────────────────────────────────────────────────────
        if reset:
            n = StarterPackItem.objects.count()
            StarterPackItem.objects.all().delete()
            self.stdout.write(f'  · cleared {n} existing items')

        created_count = 0
        updated_count = 0
        for it in items:
            region = region_map.get(it['region'])
            if region is None:
                self.stderr.write(f'  ! unknown region "{it["region"]}" — skipping')
                continue

            defaults = {
                'category':         it['category'],
                'display_name':     it['display_name'],
                'default_colors':   it.get('default_colors', []),
                'seasonality':      it.get('seasonality', 'all'),
                'formality':        it.get('formality', 'casual'),
                'prevalence_pct':   it.get('prevalence_pct'),
                'source_label':     it.get('source_label', ''),
                'source_year':      it.get('source_year'),
                'source_url':       it.get('source_url', ''),
                'confidence':       it.get('confidence', 'medium'),
                'is_default':       it.get('is_default', True),
                'is_opt_in':        it.get('is_opt_in', False),
                'opt_in_group':     it.get('opt_in_group', ''),
                'preview_image_url': category_default_image(it['category']),
                'sort_order':       it.get('sort_order', 0),
            }

            obj, created = StarterPackItem.objects.update_or_create(
                region_cluster=region,
                gender=it['gender'],
                subcategory=it['subcategory'],
                defaults=defaults,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Seeded {len(regions)} regions, '
            f'{created_count} new items, {updated_count} updated.'
        ))

        # Coverage summary
        for region in region_map.values():
            for gender, _ in StarterPackItem.GENDER_CHOICES:
                n = StarterPackItem.objects.filter(
                    region_cluster=region, gender=gender, is_default=True
                ).count()
                opt = StarterPackItem.objects.filter(
                    region_cluster=region, gender=gender, is_opt_in=True
                ).count()
                if n or opt:
                    self.stdout.write(
                        f'  {region.code:>22} / {gender:<10} → '
                        f'{n} default, {opt} opt-in'
                    )
