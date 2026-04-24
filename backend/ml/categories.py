"""
Canonical category mappings shared across training and inference.

DATASET_CATEGORIES: the 13 labels in the Kaggle deep-fashion dataset.
CATEGORY_TO_IDX / IDX_TO_CATEGORY: integer ↔ label lookups.
WARDROBE_TO_DATASET: maps Ritha wardrobe categories to dataset categories.
DATASET_TO_WARDROBE: reverse mapping.
"""

DATASET_CATEGORIES = [
    'long sleeve dress',
    'long sleeve outwear',
    'long sleeve top',
    'short sleeve dress',
    'short sleeve outwear',
    'short sleeve top',
    'shorts',
    'skirt',
    'sling',
    'sling dress',
    'trousers',
    'vest',
    'vest dress',
]

CATEGORY_TO_IDX = {c: i for i, c in enumerate(DATASET_CATEGORIES)}
IDX_TO_CATEGORY = {i: c for i, c in enumerate(DATASET_CATEGORIES)}
NUM_CATEGORIES = len(DATASET_CATEGORIES)

# Map Ritha wardrobe categories → closest dataset categories
WARDROBE_TO_DATASET = {
    'top':        ['short sleeve top', 'long sleeve top'],
    'bottom':     ['trousers', 'shorts', 'skirt'],
    'dress':      ['short sleeve dress', 'long sleeve dress', 'vest dress', 'sling dress'],
    'outerwear':  ['long sleeve outwear', 'short sleeve outwear'],
    'footwear':   [],   # not in dataset
    'accessory':  ['sling'],
    'activewear': ['vest', 'shorts'],
    'formal':     ['long sleeve dress', 'long sleeve top', 'trousers'],
    'other':      [],
}

DATASET_TO_WARDROBE = {
    'long sleeve dress':   'dress',
    'long sleeve outwear': 'outerwear',
    'long sleeve top':     'top',
    'short sleeve dress':  'dress',
    'short sleeve outwear':'outerwear',
    'short sleeve top':    'top',
    'shorts':              'bottom',
    'skirt':               'bottom',
    'sling':               'accessory',
    'sling dress':         'dress',
    'trousers':            'bottom',
    'vest':                'top',
    'vest dress':          'dress',
}

# Weather-appropriate categories — finer-grained buckets
WEATHER_CATEGORY_RULES = {
    'freezing': {
        'prefer':  ['long sleeve top', 'long sleeve outwear', 'long sleeve dress', 'trousers'],
        'avoid':   ['shorts', 'vest', 'sling', 'sling dress', 'short sleeve top', 'short sleeve dress', 'skirt'],
    },
    'cold': {
        'prefer':  ['long sleeve top', 'long sleeve outwear', 'long sleeve dress', 'trousers'],
        'avoid':   ['shorts', 'vest', 'sling', 'sling dress', 'short sleeve top'],
    },
    'cool': {
        'prefer':  ['long sleeve top', 'trousers', 'long sleeve dress', 'skirt'],
        'avoid':   ['shorts', 'sling', 'sling dress', 'vest'],
    },
    'mild': {
        'prefer':  ['short sleeve top', 'long sleeve top', 'trousers', 'skirt', 'short sleeve dress'],
        'avoid':   [],
    },
    'warm': {
        'prefer':  ['short sleeve top', 'shorts', 'skirt', 'short sleeve dress', 'sling dress'],
        'avoid':   ['long sleeve outwear', 'long sleeve top'],
    },
    'hot': {
        'prefer':  ['short sleeve top', 'shorts', 'vest', 'sling dress', 'skirt', 'short sleeve dress'],
        'avoid':   ['long sleeve outwear', 'long sleeve top', 'long sleeve dress', 'trousers'],
    },
    'rainy': {
        'prefer':  ['long sleeve outwear', 'trousers'],
        'avoid':   ['sling', 'sling dress'],
    },
    'windy': {
        'prefer':  ['long sleeve outwear', 'trousers', 'long sleeve top'],
        'avoid':   ['sling', 'vest', 'sling dress'],
    },
}

# Occasion-to-formality mapping
OCCASION_FORMALITY = {
    'casual':          ['casual'],
    'smart_casual':    ['casual_smart'],
    'business':        ['smart', 'formal'],
    'formal':          ['formal'],
    'activewear':      ['activewear'],
    'travel':          ['casual', 'casual_smart'],
    'cultural_visit':  ['smart', 'casual_smart'],
    'date':            ['casual_smart', 'smart'],
    'wedding':         ['formal'],
    'interview':       ['formal', 'smart'],
}
