"""Helpers for exposing ClothingItem image URLs in recommendation output.

Recommendation/agent responses build item dicts from `.values(...)`, which yields
the raw `image` storage path (e.g. "wardrobe/dev_5.jpg"), not a URL. These helpers
turn that path into a usable URL:

- S3/R2 storage  → an absolute URL (from the storage backend).
- local storage  → a root-relative "/media/..." URL; frontends resolve it against
  the API origin.

Empty string when the item has no image; the frontends fall back to a
category-default illustration in that case.
"""

from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.utils.text import slugify

# Cached starter-pack images live here, populated by `manage.py fetch_starter_images`
# (CC0/public-domain flat-lays from Openverse), keyed by region/gender/subcategory.
SEED_IMAGES_DIR = Path(__file__).resolve().parent / "seed_images"
_SEED_EXTS = ("jpg", "jpeg", "png", "webp")


def _seed_slug(subcategory) -> str:
    return slugify(str(subcategory)) or "item"


def seed_image_path(region_code, gender, subcategory):
    """Local cached starter image for (region, gender, subcategory), or None.

    Any common image extension is accepted; the first match wins.
    """
    base = SEED_IMAGES_DIR / str(region_code) / str(gender)
    if not base.is_dir():
        return None
    slug = _seed_slug(subcategory)
    for ext in _SEED_EXTS:
        p = base / f"{slug}.{ext}"
        if p.exists():
            return p
    return None


def publish_starter_preview(region_code, gender, subcategory) -> str:
    """Copy the cached starter image into default_storage once; return its URL.

    Gives StarterPackItem.preview_image_url a real, servable photo. Returns ''
    when nothing is cached (caller falls back to the category illustration).
    """
    src = seed_image_path(region_code, gender, subcategory)
    if src is None:
        return ""
    dest = f"starter/{region_code}/{gender}/{_seed_slug(subcategory)}{src.suffix.lower()}"
    try:
        if not default_storage.exists(dest):
            with src.open("rb") as fh:
                default_storage.save(dest, File(fh))
        return default_storage.url(dest)
    except Exception:
        return ""


def attach_seed_image(clothing_item, region_code, gender, subcategory) -> bool:
    """Attach the cached starter image to a ClothingItem.image (per-user copy).

    Returns True when an image was attached, False when none was cached.
    """
    src = seed_image_path(region_code, gender, subcategory)
    if src is None:
        return False
    try:
        with src.open("rb") as fh:
            clothing_item.image.save(f"{_seed_slug(subcategory)}{src.suffix.lower()}", File(fh), save=True)
        return True
    except Exception:
        return False


def item_image_url(image_path) -> str:
    """URL for a ClothingItem.image path (or '' when absent)."""
    if not image_path:
        return ""
    try:
        return default_storage.url(str(image_path))
    except Exception:
        return ""


def attach_image_urls(items):
    """Set `image_url` on each item dict (from its `image` path). Mutates + returns."""
    for it in items:
        if isinstance(it, dict) and not it.get("image_url"):
            it["image_url"] = item_image_url(it.get("image"))
    return items
