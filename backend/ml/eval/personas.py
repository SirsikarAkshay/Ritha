"""Hand-crafted personas for evaluating the recommendation engine.

Each persona = (wardrobe items, calendar events, weather snapshot, expected
traits). Personas cover the dimensions the recommender must handle correctly:
  - Weather extremes (cold, hot, rain)
  - Formality range (casual, smart, formal)
  - Multi-context days (workout → office → dinner)
  - Cultural constraints (modest dress required)

These are intentionally small (~10-20 items per wardrobe). The point is to
catch regressions, not exhaustively model real wardrobes.

Add personas here as you discover failure modes in production.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class Persona:
    name:        str
    description: str
    wardrobe:    list[dict]
    events:      list[dict]
    weather:     dict
    expected:    dict   # rubric — see harness.py for fields


# ── Item factory ──────────────────────────────────────────────────────────────
# Compact constructor so personas stay readable.

def _item(id_, name, category, formality='casual', season='all', colors=None,
          times_worn=0, last_worn=None, tags=None, weight_grams=200):
    return {
        'id': id_,
        'name': name,
        'category': category,
        'formality': formality,
        'season': season,
        'colors': colors or [],
        'times_worn': times_worn,
        'last_worn': last_worn,
        'tags': tags or [],
        'weight_grams': weight_grams,
    }


# ── Personas ──────────────────────────────────────────────────────────────────

def cold_business_day() -> Persona:
    """User has a 10am board meeting. Outside is 2°C, dry."""
    wardrobe = [
        _item(1, 'White Oxford shirt', 'top',     formality='smart',  season='all',    colors=['white'],  times_worn=8),
        _item(2, 'Navy blazer',        'outerwear', formality='formal', season='all',  colors=['navy'],  times_worn=4),
        _item(3, 'Grey wool trousers', 'bottom',  formality='smart',  season='winter', colors=['grey'],  times_worn=6),
        _item(4, 'Black leather oxfords', 'footwear', formality='formal', season='all', colors=['black'], times_worn=10),
        _item(5, 'Cotton T-shirt',     'top',     formality='casual', season='all',    colors=['white'], times_worn=20),
        _item(6, 'Indigo jeans',       'bottom',  formality='casual', season='all',    colors=['indigo']),
        _item(7, 'White sneakers',     'footwear', formality='casual', season='all',   colors=['white']),
        _item(8, 'Knit sweater',       'top',     formality='casual_smart', season='winter', colors=['cream']),
        _item(9, 'Beige chinos',       'bottom',  formality='casual_smart', season='all',    colors=['beige']),
    ]
    return Persona(
        name='cold_business_day',
        description='2°C, 10am board meeting',
        wardrobe=wardrobe,
        events=[{
            'title': 'Board meeting',
            'event_type': 'meeting',
            'formality': 'formal',
            'start_time': '2026-04-29T10:00:00',
            'location': 'Office',
        }],
        weather={'temperature_c': 2, 'is_cold': True, 'is_hot': False, 'is_raining': False, 'condition': 'clear'},
        expected={
            'must_include_category': ['top', 'bottom'],
            'must_include_formality_at_least': 'smart',
            'must_avoid_categories': [],   # outerwear strongly preferred but not strictly required if no jacket exists
            'must_match_season_or_all': True,
            'should_include_warm_layer': True,   # outerwear OR a knit/wool item
            'forbid_categories': ['activewear'],
        },
    )


def hot_beach_day() -> Persona:
    """User in Bali. 32°C, no calendar events. Casual day."""
    wardrobe = [
        _item(1, 'Cotton T-shirt', 'top',      formality='casual', season='summer', colors=['white']),
        _item(2, 'Linen shirt',    'top',      formality='casual_smart', season='summer', colors=['beige']),
        _item(3, 'Casual shorts',  'bottom',   formality='casual', season='summer', colors=['khaki']),
        _item(4, 'Indigo jeans',   'bottom',   formality='casual', season='all',    colors=['indigo'], weight_grams=600),
        _item(5, 'Flat sandals',   'footwear', formality='casual', season='summer', colors=['tan']),
        _item(6, 'White sneakers', 'footwear', formality='casual', season='all',    colors=['white']),
        _item(7, 'Wool sweater',   'top',      formality='casual', season='winter', colors=['grey']),
        _item(8, 'Linen sundress', 'dress',    formality='casual', season='summer', colors=['white']),
    ]
    return Persona(
        name='hot_beach_day',
        description='32°C in Bali, no events',
        wardrobe=wardrobe,
        events=[],
        weather={'temperature_c': 32, 'is_cold': False, 'is_hot': True, 'is_raining': False, 'condition': 'sunny'},
        expected={
            'must_include_category': ['top', 'bottom'],   # OR a dress
            'must_avoid_categories': [],
            'forbid_seasonal': ['winter'],   # wool sweater MUST NOT be picked
            'forbid_formality_above': 'casual_smart',
            'should_prefer_summer': True,
        },
    )


def rainy_commute() -> Persona:
    """User commutes to office. 12°C, raining."""
    wardrobe = [
        _item(1, 'Light jacket',   'outerwear', formality='casual_smart', season='spring', colors=['olive']),
        _item(2, 'Waterproof shell','outerwear', formality='casual',     season='all',     colors=['black'], tags=['waterproof']),
        _item(3, 'Knit sweater',   'top',      formality='casual_smart', season='all',     colors=['navy']),
        _item(4, 'Oxford shirt',   'top',      formality='smart',  season='all',     colors=['light-blue']),
        _item(5, 'Grey trousers',  'bottom',   formality='smart',  season='all',     colors=['grey']),
        _item(6, 'Indigo jeans',   'bottom',   formality='casual', season='all',     colors=['indigo']),
        _item(7, 'Black leather boots', 'footwear', formality='smart', season='all', colors=['black']),
        _item(8, 'White sneakers', 'footwear', formality='casual', season='all',     colors=['white']),
    ]
    return Persona(
        name='rainy_commute',
        description='12°C, raining, smart-casual office day',
        wardrobe=wardrobe,
        events=[{
            'title': 'Team standup',
            'event_type': 'meeting',
            'formality': 'casual_smart',
            'start_time': '2026-04-29T09:30:00',
            'location': 'Office',
        }],
        weather={'temperature_c': 12, 'is_cold': False, 'is_hot': False, 'is_raining': True, 'condition': 'rain'},
        expected={
            'must_include_category': ['top', 'bottom'],
            'should_include_outerwear': True,
            'must_include_formality_at_least': 'casual_smart',
            'forbid_categories': ['activewear'],
        },
    )


def formal_wedding() -> Persona:
    """Saturday, 4pm wedding. 18°C, dry."""
    wardrobe = [
        _item(1, 'Navy suit jacket', 'outerwear', formality='formal', season='all', colors=['navy']),
        _item(2, 'Suit trousers',    'bottom',   formality='formal', season='all', colors=['navy']),
        _item(3, 'White dress shirt','top',      formality='formal', season='all', colors=['white']),
        _item(4, 'Black derby shoes','footwear', formality='formal', season='all', colors=['black']),
        _item(5, 'Cotton T-shirt',   'top',      formality='casual', season='all', colors=['grey']),
        _item(6, 'Indigo jeans',     'bottom',   formality='casual', season='all', colors=['indigo']),
        _item(7, 'White sneakers',   'footwear', formality='casual', season='all', colors=['white']),
    ]
    return Persona(
        name='formal_wedding',
        description='4pm wedding, 18°C dry',
        wardrobe=wardrobe,
        events=[{
            'title': 'Sarah & James wedding',
            'event_type': 'wedding',
            'formality': 'formal',
            'start_time': '2026-04-29T16:00:00',
            'location': 'Hotel',
        }],
        weather={'temperature_c': 18, 'is_cold': False, 'is_hot': False, 'is_raining': False, 'condition': 'clear'},
        expected={
            'must_include_category': ['top', 'bottom', 'footwear'],
            'must_include_formality_at_least': 'formal',
            'forbid_categories': ['activewear'],
            'forbid_formality_below': 'casual_smart',
        },
    )


def mixed_context_day() -> Persona:
    """6am gym → 10am office → 7pm dinner. Tests multi-context handling."""
    wardrobe = [
        _item(1, 'Athletic shorts', 'activewear', formality='activewear', season='all', colors=['black']),
        _item(2, 'Workout top',     'activewear', formality='activewear', season='all', colors=['grey']),
        _item(3, 'Running shoes',   'footwear',   formality='activewear', season='all', colors=['neon']),
        _item(4, 'Oxford shirt',    'top',        formality='smart',  season='all', colors=['white']),
        _item(5, 'Grey trousers',   'bottom',     formality='smart',  season='all', colors=['grey']),
        _item(6, 'Brown derby',     'footwear',   formality='formal', season='all', colors=['brown']),
        _item(7, 'Navy blazer',     'outerwear',  formality='formal', season='all', colors=['navy']),
    ]
    return Persona(
        name='mixed_context_day',
        description='Gym + office + dinner across one day',
        wardrobe=wardrobe,
        events=[
            {'title': 'Morning workout', 'event_type': 'workout', 'formality': 'activewear',
             'start_time': '2026-04-29T06:00:00', 'location': 'Gym'},
            {'title': 'Client call',     'event_type': 'meeting', 'formality': 'smart',
             'start_time': '2026-04-29T10:00:00', 'location': 'Office'},
            {'title': 'Anniversary dinner', 'event_type': 'social', 'formality': 'casual_smart',
             'start_time': '2026-04-29T19:00:00', 'location': 'Restaurant'},
        ],
        weather={'temperature_c': 16, 'is_cold': False, 'is_hot': False, 'is_raining': False, 'condition': 'clear'},
        expected={
            'must_have_transitions': True,         # tier 1.5 — multi-context day
            'transition_count_at_least': 1,
            'must_cover_formalities': ['activewear', 'smart'],
        },
    )


def modest_dress_required() -> Persona:
    """User in a destination with required modest-dress rules.

    The persona's wardrobe contains both compliant (long-sleeve, trousers)
    and non-compliant (sleeveless, shorts) items. The recommender must
    surface only compliant choices when cultural severity == 'required'.
    Tier §3.3.
    """
    wardrobe = [
        _item(1, 'Sleeveless tank',  'top',     formality='casual', season='summer', colors=['white'],   tags=['sleeveless', 'tank']),
        _item(2, 'Long-sleeve linen','top',     formality='casual_smart', season='summer', colors=['beige']),
        _item(3, 'Cotton shorts',    'bottom',  formality='casual', season='summer', colors=['khaki'],  tags=['shorts']),
        _item(4, 'Linen trousers',   'bottom',  formality='casual_smart', season='summer', colors=['cream']),
        _item(5, 'Flat sandals',     'footwear', formality='casual', season='summer', colors=['tan']),
        _item(6, 'Closed-toe loafers','footwear', formality='casual_smart', season='all', colors=['brown']),
    ]
    # Cultural rules consumed by the recommender directly (bypasses Mistral).
    cultural_rules = [{
        'type': 'modest_dress',
        'severity': 'required',
        'description': 'Local custom requires shoulders and knees to be covered.',
    }]
    return Persona(
        name='modest_dress_required',
        description='Destination requires modest dress; wardrobe has both compliant and non-compliant items',
        wardrobe=wardrobe,
        events=[],
        weather={'temperature_c': 28, 'is_cold': False, 'is_hot': True, 'is_raining': False, 'condition': 'sunny'},
        expected={
            'must_include_category': ['top', 'bottom'],
            'forbid_categories': [],
            # The wardrobe items themselves carry forbidden tags — assert
            # the recommender doesn't pick them.
            'forbid_tagged_items': ['sleeveless', 'tank', 'shorts'],
            '__cultural_rules': cultural_rules,
        },
    )


def trip_day_overrides_daily() -> Persona:
    """User is mid-trip; saved trip plan must override the wardrobe-based daily look.

    The persona's wardrobe contains items the daily-look stub would naturally
    pick (sneakers + jeans + tee) AND items the trip plan saved (linen shirt
    + chinos + loafers). The expected outcome: the trip's items appear, not
    the wardrobe-default ones.
    """
    wardrobe = [
        # Items that would win the wardrobe-only path
        _item(1, 'Cotton T-shirt',  'top',     formality='casual', season='all', colors=['white'],   times_worn=10),
        _item(2, 'Indigo jeans',    'bottom',  formality='casual', season='all', colors=['indigo'],  times_worn=8),
        _item(3, 'White sneakers',  'footwear', formality='casual', season='all', colors=['white'],  times_worn=15),
        # Items the trip plan picked
        _item(4, 'Linen shirt',     'top',     formality='casual_smart', season='summer', colors=['cream']),
        _item(5, 'Beige chinos',    'bottom',  formality='casual_smart', season='all',    colors=['beige']),
        _item(6, 'Brown loafers',   'footwear', formality='smart',  season='all',    colors=['brown']),
    ]
    return Persona(
        name='trip_day_overrides_daily',
        description='Mid-trip — saved plan items must surface, not generic daily-look picks',
        wardrobe=wardrobe,
        events=[],
        weather={'temperature_c': 24, 'is_cold': False, 'is_hot': False, 'is_raining': False, 'condition': 'clear'},
        expected={
            # Items 4, 5, 6 must appear; 1, 2, 3 must NOT.
            'must_include_item_ids': [4, 5, 6],
            'must_exclude_item_ids': [1, 2, 3],
            # Synthetic trip plan consumed by the test runner.
            '__trip_day_plan': {
                'destination': 'Lisbon',
                'day':         2,
                'item_ids':    [4, 5, 6],
                'notes':       'Day 2: city walk + dinner.',
            },
        },
    )


def all_personas() -> list[Persona]:
    return [
        cold_business_day(),
        hot_beach_day(),
        rainy_commute(),
        formal_wedding(),
        mixed_context_day(),
        modest_dress_required(),
        trip_day_overrides_daily(),
    ]
