"""Fetch CC0 / public-domain flat-lay images for starter-pack items from Openverse.

Populates wardrobe/seed_images/<region>/<gender>/<subcategory>.jpg from the
`image_keywords` in starter_packs.yaml. `seed_starter_packs` and the onboarding
apply flow then use these cached files for real photos; anything without one
falls back to the bundled category illustration.

Only CC0 and Public-Domain-Mark results are requested, so no attribution is
legally required — but provenance is still recorded in seed_images/CREDITS.json.

Usage:
    python manage.py fetch_starter_images                          # all items, skip cached
    python manage.py fetch_starter_images --region south_asian_north --gender women
    python manage.py fetch_starter_images --refresh                # re-fetch even if cached
    python manage.py fetch_starter_images --dry-run                # print the plan only

Run it on a machine with internet access, review the images under
wardrobe/seed_images/, swap any poor matches, then commit them.
"""

import json
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from wardrobe.images import _SEED_EXTS, SEED_IMAGES_DIR, _seed_slug

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "starter_packs.yaml"
OPENVERSE_URL = "https://api.openverse.org/v1/images/"
CREDITS_PATH = SEED_IMAGES_DIR / "CREDITS.json"
_UA = {"User-Agent": "Ritha-StarterSeed/1.0 (+https://getritha.com)"}


class Command(BaseCommand):
    help = "Fetch CC0/public-domain flat-lay images for starter-pack items from Openverse."

    def add_arguments(self, parser):
        parser.add_argument("--region", help="Only this region code")
        parser.add_argument("--gender", help="Only this gender bucket")
        parser.add_argument("--refresh", action="store_true", help="Re-fetch even if a cached image exists")
        parser.add_argument("--limit", type=int, default=0, help="Cap the number of items processed")
        parser.add_argument("--sleep", type=float, default=0.6, help="Delay between requests (be polite)")
        parser.add_argument("--dry-run", action="store_true", help="Print what would be fetched, do nothing")

    def handle(self, *args, region=None, gender=None, refresh=False, limit=0, sleep=0.6, dry_run=False, **options):
        if not DATA_PATH.exists():
            self.stderr.write(f"Data file not found: {DATA_PATH}")
            return

        items = [it for it in yaml.safe_load(DATA_PATH.read_text()).get("items", []) if it.get("image_keywords")]
        if region:
            items = [it for it in items if it["region"] == region]
        if gender:
            items = [it for it in items if it["gender"] == gender]
        if limit:
            items = items[:limit]

        self.stdout.write(f"▸ {len(items)} items with keywords" + (" (dry-run)" if dry_run else ""))
        credits = self._load_credits()
        fetched = skipped = failed = 0

        for it in items:
            slug = _seed_slug(it["subcategory"])
            dest_dir = SEED_IMAGES_DIR / it["region"] / it["gender"]
            rel = f"{it['region']}/{it['gender']}/{slug}"
            query = it["image_keywords"]

            if self._cached(dest_dir, slug) and not refresh:
                skipped += 1
                continue
            if dry_run:
                self.stdout.write(f'  · would fetch {rel}  ← "{query}"')
                continue

            try:
                import time

                hit = self._search(query)
                if not hit or not hit.get("url"):
                    self.stderr.write(f'  ! no CC0 result for "{query}" ({rel})')
                    failed += 1
                    time.sleep(sleep)
                    continue
                raw = self._download(hit["url"])
                dest_dir.mkdir(parents=True, exist_ok=True)
                self._save_jpg(raw, dest_dir / f"{slug}.jpg")
                credits[rel] = {
                    "query": query,
                    "title": hit.get("title"),
                    "creator": hit.get("creator"),
                    "license": hit.get("license"),
                    "license_url": hit.get("license_url"),
                    "source": hit.get("source"),
                    "foreign_landing_url": hit.get("foreign_landing_url"),
                }
                fetched += 1
                self.stdout.write(f"  ✓ {rel}  ({hit.get('license', '?')})")
                time.sleep(sleep)
            except Exception as e:  # network / decode / any single-item failure — keep going
                self.stderr.write(f"  ! failed {rel}: {e}")
                failed += 1

        if not dry_run:
            self._save_credits(credits)
        self.stdout.write(self.style.SUCCESS(f"\n✓ fetched {fetched}, skipped {skipped} (cached), failed {failed}"))

    # ── seams (overridden in tests to avoid the network) ────────────────────
    def _search(self, query: str):
        """Return the first CC0/PDM Openverse image result for `query`, or None."""
        url = (
            OPENVERSE_URL
            + "?"
            + urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "mature": "false", "page_size": 6})
        )
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (trusted host)
            results = json.loads(resp.read()).get("results", [])
        return next((r for r in results if r.get("url")), None)

    def _download(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.read()

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _save_jpg(raw: bytes, dest: Path):
        from PIL import Image

        img = Image.open(BytesIO(raw)).convert("RGB")
        img.thumbnail((640, 640))
        img.save(dest, "JPEG", quality=85)

    @staticmethod
    def _cached(dest_dir: Path, slug: str):
        return any((dest_dir / f"{slug}.{ext}").exists() for ext in _SEED_EXTS)

    @staticmethod
    def _load_credits() -> dict:
        if CREDITS_PATH.exists():
            try:
                return json.loads(CREDITS_PATH.read_text())
            except Exception:
                return {}
        return {}

    @staticmethod
    def _save_credits(credits: dict):
        SEED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        CREDITS_PATH.write_text(json.dumps(credits, indent=2, sort_keys=True) + "\n")
