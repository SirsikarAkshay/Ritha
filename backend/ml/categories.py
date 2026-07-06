"""
Canonical category mappings shared across training and inference.

DATASET_CATEGORIES: the 13 labels in the Kaggle deep-fashion dataset.
CATEGORY_TO_IDX / IDX_TO_CATEGORY: integer ↔ label lookups.
WARDROBE_TO_DATASET: maps Ritha wardrobe categories to dataset categories.
DATASET_TO_WARDROBE: reverse mapping.
"""

DATASET_CATEGORIES = [
    "long sleeve dress",
    "long sleeve outwear",
    "long sleeve top",
    "short sleeve dress",
    "short sleeve outwear",
    "short sleeve top",
    "shorts",
    "skirt",
    "sling",
    "sling dress",
    "trousers",
    "vest",
    "vest dress",
]

CATEGORY_TO_IDX = {c: i for i, c in enumerate(DATASET_CATEGORIES)}
IDX_TO_CATEGORY = {i: c for i, c in enumerate(DATASET_CATEGORIES)}
NUM_CATEGORIES = len(DATASET_CATEGORIES)

# Map Ritha wardrobe categories → closest dataset categories
WARDROBE_TO_DATASET = {
    "top": ["short sleeve top", "long sleeve top"],
    "bottom": ["trousers", "shorts", "skirt"],
    "dress": ["short sleeve dress", "long sleeve dress", "vest dress", "sling dress"],
    "outerwear": ["long sleeve outwear", "short sleeve outwear"],
    "footwear": [],  # not in dataset
    "accessory": ["sling"],
    "activewear": ["vest", "shorts"],
    "formal": ["long sleeve dress", "long sleeve top", "trousers"],
    "other": [],
}

DATASET_TO_WARDROBE = {
    "long sleeve dress": "dress",
    "long sleeve outwear": "outerwear",
    "long sleeve top": "top",
    "short sleeve dress": "dress",
    "short sleeve outwear": "outerwear",
    "short sleeve top": "top",
    "shorts": "bottom",
    "skirt": "bottom",
    "sling": "accessory",
    "sling dress": "dress",
    "trousers": "bottom",
    "vest": "top",
    "vest dress": "dress",
}

# Weather-appropriate categories — finer-grained buckets
WEATHER_CATEGORY_RULES = {
    "freezing": {
        "prefer": ["long sleeve top", "long sleeve outwear", "long sleeve dress", "trousers"],
        "avoid": ["shorts", "vest", "sling", "sling dress", "short sleeve top", "short sleeve dress", "skirt"],
    },
    "cold": {
        "prefer": ["long sleeve top", "long sleeve outwear", "long sleeve dress", "trousers"],
        "avoid": ["shorts", "vest", "sling", "sling dress", "short sleeve top"],
    },
    "cool": {
        "prefer": ["long sleeve top", "trousers", "long sleeve dress", "skirt"],
        "avoid": ["shorts", "sling", "sling dress", "vest"],
    },
    "mild": {
        "prefer": ["short sleeve top", "long sleeve top", "trousers", "skirt", "short sleeve dress"],
        "avoid": [],
    },
    "warm": {
        "prefer": ["short sleeve top", "shorts", "skirt", "short sleeve dress", "sling dress"],
        "avoid": ["long sleeve outwear", "long sleeve top"],
    },
    "hot": {
        "prefer": ["short sleeve top", "shorts", "vest", "sling dress", "skirt", "short sleeve dress"],
        "avoid": ["long sleeve outwear", "long sleeve top", "long sleeve dress", "trousers"],
    },
    "rainy": {
        "prefer": ["long sleeve outwear", "trousers"],
        "avoid": ["sling", "sling dress"],
    },
    "windy": {
        "prefer": ["long sleeve outwear", "trousers", "long sleeve top"],
        "avoid": ["sling", "vest", "sling dress"],
    },
}

# Occasion-to-formality mapping
OCCASION_FORMALITY = {
    "casual": ["casual"],
    "smart_casual": ["casual_smart"],
    "business": ["smart", "formal"],
    "formal": ["formal"],
    "activewear": ["activewear"],
    "travel": ["casual", "casual_smart"],
    "cultural_visit": ["smart", "casual_smart"],
    "date": ["casual_smart", "smart"],
    "wedding": ["formal"],
    "interview": ["formal", "smart"],
}

# ── Packed-volume model (bag-capacity-aware packing) ──────────────────────────
# We have no per-item volume field, so we estimate how much space a garment takes
# once rolled/packed, from its category and (bulky) material. Values are rough
# liters of packed volume — good enough to rank items and fit them to a bag size.
CATEGORY_PACKED_VOLUME_LITERS = {
    "top": 1.2,
    "bottom": 1.8,
    "dress": 1.6,
    "outerwear": 3.5,
    "footwear": 3.0,
    "accessory": 0.4,
    "activewear": 1.0,
    "formal": 2.2,
    "other": 1.2,
}

# Multiplier applied when a bulky (or notably compact) fabric is detected in the
# item's free-text material. First matching key wins the largest factor.
MATERIAL_BULK_FACTOR = {
    "down": 1.7,
    "puffer": 1.7,
    "fleece": 1.5,
    "wool": 1.4,
    "cashmere": 1.4,
    "sweater": 1.35,
    "knit": 1.35,
    "denim": 1.3,
    "corduroy": 1.3,
    "leather": 1.3,
    "cotton": 1.0,
    "polyester": 0.95,
    "nylon": 0.9,
    "linen": 0.9,
    "silk": 0.8,
}


def estimate_packed_volume_liters(category: str, material: str = "") -> float:
    """Approximate packed volume (liters) of a garment from category + material."""
    base = CATEGORY_PACKED_VOLUME_LITERS.get(category, CATEGORY_PACKED_VOLUME_LITERS["other"])
    factor = 1.0
    m = (material or "").lower()
    for key, mult in MATERIAL_BULK_FACTOR.items():
        if key in m:
            factor = max(factor, mult)
    return round(base * factor, 2)
