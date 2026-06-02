"""Perceptual color harmony scoring for outfit assembly.

Maps named colors to CIELAB coordinates (D65 illuminant) and scores how a
candidate item's color fits with the colors already chosen. Replaces the
prior "same-color = bad, different-color = good" string-equality scoring,
which treated 'navy' and 'blue' as different and 'navy' and 'white' as
equally different from 'navy' and 'midnight blue'.

CIE76 Delta E (Euclidean in Lab) is used. CIE2000 is more perceptually
uniform but at the integer-resolution band edges we score on (15 / 90
Delta E) the difference doesn't change selection.
"""
from __future__ import annotations

import math
from typing import Iterable


# Canonical Lab (D65) for common color names found in user wardrobes.
# Single-token entries; multi-token names resolve via _name_to_lab below.
_LAB: dict[str, tuple[float, float, float]] = {
    'white':     (100.0,   0.0,    0.0),
    'black':     (  0.0,   0.0,    0.0),
    'grey':      ( 53.6,   0.0,    0.0),
    'gray':      ( 53.6,   0.0,    0.0),
    'silver':    ( 79.0,   0.0,    0.0),
    'charcoal':  ( 25.0,   0.0,    0.0),
    'cream':     ( 96.0,  -1.0,   11.0),
    'beige':     ( 92.0,   0.0,   13.0),
    'ivory':     ( 99.0,  -1.0,    8.0),
    'red':       ( 53.0,  80.0,   67.0),
    'crimson':   ( 32.0,  78.0,   53.0),
    'maroon':    ( 25.0,  47.0,   25.0),
    'burgundy':  ( 25.0,  50.0,   25.0),
    'pink':      ( 84.0,  24.0,    3.0),
    'rose':      ( 70.0,  35.0,    7.0),
    'magenta':   ( 60.0,  98.0,  -60.0),
    'orange':    ( 75.0,  23.0,   78.0),
    'rust':      ( 49.0,  39.0,   47.0),
    'coral':     ( 70.0,  43.0,   37.0),
    'salmon':    ( 70.0,  35.0,   20.0),
    'yellow':    ( 97.0, -22.0,   95.0),
    'gold':      ( 86.0,   0.0,   84.0),
    'mustard':   ( 78.0,   2.0,   79.0),
    'green':     ( 88.0, -86.0,   83.0),
    'forest':    ( 35.0, -33.0,   29.0),
    'olive':     ( 51.0, -12.0,   57.0),
    'lime':      ( 88.0, -86.0,   83.0),
    'mint':      ( 87.0, -36.0,   14.0),
    'sage':      ( 73.0, -16.0,   18.0),
    'teal':      ( 48.0, -28.0,   -8.0),
    'turquoise': ( 80.0, -50.0,  -10.0),
    'cyan':      ( 91.0, -50.0,  -15.0),
    'blue':      ( 32.0,  79.0, -108.0),
    'navy':      ( 12.0,  47.0,  -64.0),
    'royal':     ( 36.0,  28.0,  -82.0),
    'sky':       ( 79.0,  -9.0,  -23.0),
    'denim':     ( 35.0,  -3.0,  -32.0),
    'indigo':    ( 20.0,  51.0,  -53.0),
    'purple':    ( 30.0,  60.0,  -36.0),
    'lavender':  ( 79.0,  17.0,  -19.0),
    'violet':    ( 56.0,  76.0,  -52.0),
    'brown':     ( 38.0,  26.0,   36.0),
    'tan':       ( 75.0,   5.0,   25.0),
    'camel':     ( 70.0,   8.0,   27.0),
    'khaki':     ( 79.0,  -4.0,   39.0),
    'taupe':     ( 60.0,   2.0,    9.0),
    'neon':      ( 90.0,  20.0,   90.0),
}

# Patterns / multi-color items skip distance scoring entirely — we have no
# meaningful Lab coordinate for them.
_SKIP = {'multi', 'multicolor', 'rainbow', 'pattern', 'print', 'floral', 'plaid', 'check'}

_LIGHTEN = {'light', 'pale', 'pastel'}
_DARKEN  = {'dark', 'deep', 'midnight'}


def _name_to_lab(name: str) -> tuple[float, float, float] | None:
    """Resolve a free-text color name to Lab. Returns None if unknown or pattern."""
    if not name:
        return None
    tokens = name.lower().strip().split()
    if not tokens:
        return None
    if any(t in _SKIP for t in tokens):
        return None

    full = ' '.join(tokens)
    if full in _LAB:
        return _LAB[full]

    # Walk right-to-left so 'royal blue' resolves to 'blue' (the head noun),
    # and modifiers ('light', 'dark') apply to L*.
    base = None
    base_idx = None
    for i in range(len(tokens) - 1, -1, -1):
        if tokens[i] in _LAB:
            base = _LAB[tokens[i]]
            base_idx = i
            break
    if base is None:
        return None

    L, a, b = base
    for m in tokens[:base_idx]:
        if m in _LIGHTEN:
            L = min(100.0, L + 18.0)
        elif m in _DARKEN:
            L = max(0.0, L - 18.0)
    return (L, a, b)


def delta_e(c1: str, c2: str) -> float | None:
    """CIE76 Delta E between two named colors. None if either is unknown."""
    a = _name_to_lab(c1)
    b = _name_to_lab(c2)
    if a is None or b is None:
        return None
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def candidate_color_score(candidate_colors: Iterable[str],
                          used_colors: Iterable[str]) -> float | None:
    """Score a candidate item against colors already in the outfit.

    Returns one of:
      * +0.25 — pleasing variety (15 ≤ Δe < 130)
      * +0.10 — extreme contrast (Δe ≥ 130), often saturated complementary
                pairs that work in moderation but read busy if multiple
      * -0.30 — too close (Δe < 15), monochromatic
      *  None — at least one color unknown; caller should fall back.

    The 130 ceiling is loose by design: classic harmonic pairs (navy/white,
    black/cream, charcoal/ivory) sit at Δe ≈ 100-130 in CIE76 because they
    span the L* axis. Earlier thresholds put them in the "may clash" band,
    which contradicted observed-good outfits.

    Distance is the *minimum* over all (candidate × used) color pairs —
    matching even one used color is enough to trigger the close penalty,
    since that's how a wearer perceives the outfit.
    """
    cand = [c for c in candidate_colors if c]
    used = [c for c in used_colors if c]
    if not cand or not used:
        return 0.0

    best: float | None = None
    for c1 in cand:
        for c2 in used:
            d = delta_e(c1, c2)
            if d is None:
                continue
            if best is None or d < best:
                best = d
    if best is None:
        return None

    if best < 15.0:
        return -0.30
    if best < 130.0:
        return 0.25
    return 0.10


def extract_colors(item: dict) -> set[str]:
    """Pull a normalized lowercase color set out of a wardrobe item dict.

    Accepts both list and comma-separated-string `colors` (legacy and newer
    schemas have used both). Returns an empty set when neither is present
    or the value is malformed.
    """
    raw = item.get('colors') or item.get('color') or ''
    if isinstance(raw, list):
        return {c.lower().strip() for c in raw if isinstance(c, str) and c.strip()}
    if isinstance(raw, str):
        return {c.strip() for c in raw.lower().split(',') if c.strip()}
    return set()
