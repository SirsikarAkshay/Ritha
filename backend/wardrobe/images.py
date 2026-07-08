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

from django.core.files.storage import default_storage


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
