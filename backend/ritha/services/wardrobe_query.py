"""
Shared wardrobe-fetch helper.

Both the destination recommender (`recommendation_engine`) and the agent
services (`agents.services`) load a user's active wardrobe as a list of plain
dicts with `image_url` attached. They previously each reimplemented the same
`ClothingItem.objects.filter(...).values(...)` + `attach_image_urls()` query,
differing only in which columns they selected. This is the single source of
that query; callers pass the exact field set they need so the returned dicts
stay identical to what each caller produced before.
"""

# The columns each caller selects. Kept as named constants so the two call
# sites are self-documenting and any future field change is made in one place.
ENGINE_FIELDS = (
    "id",
    "name",
    "category",
    "formality",
    "season",
    "colors",
    "tags",
    "weight_grams",
    "material",
    "brand",
    "image",
    "embedding",
)

AGENT_FIELDS = (
    "id",
    "name",
    "category",
    "formality",
    "season",
    "colors",
    "material",
    "image",
    "tags",
    "weight_grams",
    "times_worn",
    "last_worn",
)


def fetch_wardrobe(user, fields):
    """Return the user's active wardrobe as dicts with `image_url` attached.

    `fields` is the tuple of model columns to select — callers pass their own
    set (see ENGINE_FIELDS / AGENT_FIELDS) so the shape of the returned dicts is
    unchanged from the hand-rolled queries this replaces.
    """
    from wardrobe.images import attach_image_urls
    from wardrobe.models import ClothingItem

    items = list(ClothingItem.objects.filter(user=user, is_active=True).values(*fields))
    # Turn the raw storage path into an `image_url` so recommendations can render
    # the real garment photo (frontends fall back to a category default when empty).
    return attach_image_urls(items)
