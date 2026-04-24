"""
Rule-based calendar event type classifier.
Infers event_type and formality from a free-text event title + description.
No AI key required — runs entirely offline.
"""
import re

# (pattern, event_type, formality)
_RULES = [
    # Fitness / sport
    (r'\b(gym|workout|spin|yoga|pilates|crossfit|run|running|swim|swimming|hike|hiking|cycle|cycling|fitness|bootcamp|tennis|football|basketball|golf)\b',
     'workout', 'activewear'),

    # Travel
    (r'\b(flight|fly|airport|train|depart|arrive|layover|check.?in|check.?out|hotel|airbnb)\b',
     'travel', 'casual'),

    # Weddings / ceremonies
    (r'\b(wedding|ceremony|reception|engagement|gala|ball|black.?tie|white.?tie|prom)\b',
     'wedding', 'formal'),

    # Interviews
    (r'\b(interview|job interview|hiring|recruitment)\b',
     'interview', 'smart'),

    # External / client meetings
    (r'\b(client|customer|pitch|presentation|board|exec|ceo|stakeholder|investor|demo|proposal|external)\b',
     'external_meeting', 'smart'),

    # Internal meetings / standups
    (r'(?<!\w)(1:1|1on1|standup|stand.?up|sync|1.?on.?1|one.?on.?one|team meeting|sprint|retro|retrospective|planning|all.?hands|townhall|town.?hall)(?!\w)',
     'internal_meeting', 'casual_smart'),

    # Social / dining
    (r'\b(dinner|lunch|brunch|breakfast|drinks|date|birthday|party|celebration|restaurant|cafe|bar|happy hour)\b',
     'social', 'casual_smart'),

    # Dates
    (r'\b(date night|date with|romantic)\b',
     'date', 'smart'),

    # Catch-alls for meetings
    (r'\b(meeting|call|zoom|teams|google meet|webex|conference)\b',
     'internal_meeting', 'casual_smart'),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), etype, formality) for pat, etype, formality in _RULES]


def classify_event(title: str, description: str = '') -> dict:
    """
    Returns {'event_type': str, 'formality': str, 'confidence': str}
    confidence: 'high' | 'medium' | 'low'
    """
    text = f'{title} {description}'.strip()

    for pattern, event_type, formality in _COMPILED:
        if pattern.search(text):
            return {
                'event_type': event_type,
                'formality':  formality,
                'confidence': 'high',
            }

    # No match
    return {
        'event_type': 'other',
        'formality':  'casual',
        'confidence': 'low',
    }


def formality_rank(formality: str) -> int:
    """Higher = more formal. Used to pick the dominant outfit for multi-event days."""
    return {
        'activewear':   0,
        'casual':       1,
        'casual_smart': 2,
        'smart':        3,
        'formal':       4,
    }.get(formality, 1)


def dominant_formality(events: list) -> str:
    """Given a list of CalendarEvent objects, return the highest formality needed."""
    if not events:
        return 'casual'
    ranks = [formality_rank(e.formality or classify_event(e.title)['formality']) for e in events]
    best  = max(ranks)
    return {v: k for k, v in {
        'activewear': 0, 'casual': 1, 'casual_smart': 2, 'smart': 3, 'formal': 4
    }.items()}.get(best, 'casual')
