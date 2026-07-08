"""Curated place-to-visit recommendations, used as the rule-based fallback when
Mistral is unavailable (e.g. the demo runs in stub mode) and to enrich the AI
list. Each place matches the highlight shape the UI already renders:

    {"name", "type", "description", "clothing_tip", "formality"}

`type` ∈ landmark | museum | market | nature | restaurant | religious
`formality` ∈ casual | casual_smart | smart | formal
"""

# Keyed by lowercase city (and some countries). Matched by substring against the
# destination string, so "Rome, Italy" hits both "rome" and "italy".
CURATED_PLACES: dict[str, list[dict]] = {
    "lisbon": [
        {
            "name": "Belém Tower & Jerónimos Monastery",
            "type": "landmark",
            "description": "Manueline riverfront icons; the monastery has a modest-dress expectation.",
            "clothing_tip": "Cover shoulders for the monastery; comfy shoes for the cobbles.",
            "formality": "casual_smart",
        },
        {
            "name": "Alfama & São Jorge Castle",
            "type": "landmark",
            "description": "Steep medieval lanes, viewpoints and Fado bars.",
            "clothing_tip": "Grippy shoes for hills; a layer for breezy miradouros.",
            "formality": "casual",
        },
        {
            "name": "Time Out Market",
            "type": "market",
            "description": "Lisbon's best food hall under one roof.",
            "clothing_tip": "Smart-casual works day or night.",
            "formality": "casual_smart",
        },
        {
            "name": "LX Factory",
            "type": "market",
            "description": "Converted industrial complex of shops, cafés and street art.",
            "clothing_tip": "Relaxed, creative — anything goes.",
            "formality": "casual",
        },
        {
            "name": "Sintra — Pena Palace",
            "type": "nature",
            "description": "Fairytale palace in misty hills, a short train away.",
            "clothing_tip": "Layers and a light rain shell; it's cooler and damp up top.",
            "formality": "casual",
        },
        {
            "name": "Cais do Sodré nightlife",
            "type": "restaurant",
            "description": "Pink Street bars and riverside dinner spots.",
            "clothing_tip": "Smart-casual; skip shorts for the nicer rooms.",
            "formality": "smart",
        },
    ],
    "rome": [
        {
            "name": "Colosseum & Roman Forum",
            "type": "landmark",
            "description": "The ancient heart of Rome.",
            "clothing_tip": "Sun hat and cushioned shoes; little shade on the Forum.",
            "formality": "casual",
        },
        {
            "name": "Vatican & St. Peter's Basilica",
            "type": "religious",
            "description": "Sistine Chapel and the basilica — strict dress code.",
            "clothing_tip": "Cover shoulders AND knees or you're turned away.",
            "formality": "smart",
        },
        {
            "name": "Pantheon & Piazza Navona",
            "type": "landmark",
            "description": "Best-preserved ancient temple and a baroque square.",
            "clothing_tip": "Smart-casual; you'll be photographed a lot.",
            "formality": "casual_smart",
        },
        {
            "name": "Trastevere",
            "type": "restaurant",
            "description": "Cobbled dinner district, trattorias and wine bars.",
            "clothing_tip": "Italians dress up for dinner — leave the gym wear.",
            "formality": "smart",
        },
        {
            "name": "Borghese Gallery & Gardens",
            "type": "museum",
            "description": "Bernini sculpture and a leafy park above the city.",
            "clothing_tip": "Comfortable smart-casual for gallery and garden.",
            "formality": "casual_smart",
        },
        {
            "name": "Campo de' Fiori Market",
            "type": "market",
            "description": "Morning produce and flower market.",
            "clothing_tip": "Light and breathable; it gets warm by mid-morning.",
            "formality": "casual",
        },
    ],
    "paris": [
        {
            "name": "Louvre",
            "type": "museum",
            "description": "The world's largest art museum.",
            "clothing_tip": "Layers; galleries are cool, queues are outside.",
            "formality": "casual_smart",
        },
        {
            "name": "Notre-Dame & Île de la Cité",
            "type": "religious",
            "description": "Gothic landmark and the Seine's historic island.",
            "clothing_tip": "Modest, tidy layers for the cathedral surrounds.",
            "formality": "casual_smart",
        },
        {
            "name": "Montmartre & Sacré-Cœur",
            "type": "landmark",
            "description": "Hilltop basilica, artists' square and city views.",
            "clothing_tip": "Good shoes for the steps; a scarf for the wind.",
            "formality": "casual",
        },
        {
            "name": "Le Marais",
            "type": "market",
            "description": "Boutiques, galleries and falafel lanes.",
            "clothing_tip": "Parisian smart-casual; neutral and tailored.",
            "formality": "smart",
        },
        {
            "name": "Musée d'Orsay",
            "type": "museum",
            "description": "Impressionists in a former railway station.",
            "clothing_tip": "Smart-casual; a light layer for the halls.",
            "formality": "casual_smart",
        },
        {
            "name": "Seine dinner cruise",
            "type": "restaurant",
            "description": "Evening cruise past the lit-up monuments.",
            "clothing_tip": "Dress up — smart shoes, a jacket, a wrap for the deck.",
            "formality": "formal",
        },
    ],
    "istanbul": [
        {
            "name": "Blue Mosque (Sultan Ahmed)",
            "type": "religious",
            "description": "Working mosque with six minarets.",
            "clothing_tip": "Cover shoulders & knees, women cover hair, shoes off.",
            "formality": "smart",
        },
        {
            "name": "Hagia Sophia",
            "type": "religious",
            "description": "Byzantine wonder turned mosque.",
            "clothing_tip": "Modest dress and a scarf; shoes come off.",
            "formality": "smart",
        },
        {
            "name": "Grand Bazaar",
            "type": "market",
            "description": "4,000 shops of textiles, lamps and gold.",
            "clothing_tip": "Comfortable and closed-toe; you'll walk for hours.",
            "formality": "casual",
        },
        {
            "name": "Topkapı Palace",
            "type": "landmark",
            "description": "Ottoman sultans' palace and harem.",
            "clothing_tip": "Smart-casual; a scarf is handy for the holy relics room.",
            "formality": "casual_smart",
        },
        {
            "name": "Bosphorus ferry",
            "type": "nature",
            "description": "Cruise between two continents.",
            "clothing_tip": "A windproof layer — it's breezy on the water.",
            "formality": "casual",
        },
        {
            "name": "Galata Tower & Karaköy",
            "type": "landmark",
            "description": "Panoramic tower over hip café streets.",
            "clothing_tip": "Casual-smart; good shoes for the steep lanes.",
            "formality": "casual_smart",
        },
    ],
    "tokyo": [
        {
            "name": "Sensō-ji Temple, Asakusa",
            "type": "religious",
            "description": "Tokyo's oldest temple and Nakamise market street.",
            "clothing_tip": "Neat and modest; slip-on shoes help at shrines.",
            "formality": "casual_smart",
        },
        {
            "name": "Meiji Shrine",
            "type": "religious",
            "description": "Forested shrine beside Harajuku.",
            "clothing_tip": "Understated and tidy; quiet, respectful dress.",
            "formality": "casual_smart",
        },
        {
            "name": "Shibuya Crossing & Sky",
            "type": "landmark",
            "description": "The world's busiest scramble and a rooftop view.",
            "clothing_tip": "Sharp casual; you'll be on camera constantly.",
            "formality": "casual_smart",
        },
        {
            "name": "teamLab Planets",
            "type": "museum",
            "description": "Immersive digital-art you walk through barefoot.",
            "clothing_tip": "Roll-up trousers or shorts — you wade through water.",
            "formality": "casual",
        },
        {
            "name": "Tsukiji Outer Market",
            "type": "market",
            "description": "Street food and knife shops.",
            "clothing_tip": "Comfortable and washable; it's crowded and busy.",
            "formality": "casual",
        },
        {
            "name": "Shinjuku Gyoen",
            "type": "nature",
            "description": "Grand landscaped gardens.",
            "clothing_tip": "Layers; mornings and evenings run cool.",
            "formality": "casual",
        },
    ],
    "singapore": [
        {
            "name": "Gardens by the Bay",
            "type": "nature",
            "description": "Supertree Grove and cooled conservatories.",
            "clothing_tip": "Breathable fabrics; the domes are chilly, outside is 31°C.",
            "formality": "casual",
        },
        {
            "name": "Marina Bay Sands SkyPark",
            "type": "landmark",
            "description": "Rooftop infinity views over the bay.",
            "clothing_tip": "Smart-casual — bars refuse shorts and flip-flops.",
            "formality": "smart",
        },
        {
            "name": "Sri Mariamman Temple",
            "type": "religious",
            "description": "Singapore's oldest Hindu temple, in Chinatown.",
            "clothing_tip": "Cover shoulders & knees; remove shoes at the door.",
            "formality": "casual_smart",
        },
        {
            "name": "Sultan Mosque, Kampong Glam",
            "type": "religious",
            "description": "Golden-domed mosque and Arab Street shops.",
            "clothing_tip": "Modest dress; robes are lent if you're underdressed.",
            "formality": "casual_smart",
        },
        {
            "name": "Lau Pa Sat Hawker Centre",
            "type": "market",
            "description": "Historic food hall and satay street.",
            "clothing_tip": "Light and quick-drying; it's hot and humid.",
            "formality": "casual",
        },
        {
            "name": "Sentosa & the beaches",
            "type": "nature",
            "description": "Island of beaches, cable cars and resorts.",
            "clothing_tip": "Swimwear plus a cover-up for the ferry and eateries.",
            "formality": "casual",
        },
    ],
    "bangkok": [
        {
            "name": "Grand Palace & Wat Phra Kaew",
            "type": "religious",
            "description": "Royal complex and the Emerald Buddha.",
            "clothing_tip": "Strict: cover shoulders and knees, closed shoes.",
            "formality": "smart",
        },
        {
            "name": "Wat Arun",
            "type": "religious",
            "description": "Riverside 'Temple of Dawn'.",
            "clothing_tip": "Modest, breathable clothing; sarongs available.",
            "formality": "casual_smart",
        },
        {
            "name": "Chatuchak Weekend Market",
            "type": "market",
            "description": "15,000 stalls of everything.",
            "clothing_tip": "Coolest, lightest clothes you own; it's sweltering.",
            "formality": "casual",
        },
        {
            "name": "Chao Phraya river boat",
            "type": "nature",
            "description": "Longtail and ferry hops between temples.",
            "clothing_tip": "Sun protection and a hat; open water, strong sun.",
            "formality": "casual",
        },
        {
            "name": "Rooftop bars (Sky Bar)",
            "type": "restaurant",
            "description": "Skyline cocktails after dark.",
            "clothing_tip": "Smart dress code — collared shirts, proper shoes.",
            "formality": "smart",
        },
        {
            "name": "Jim Thompson House",
            "type": "museum",
            "description": "Teak house and Thai silk story.",
            "clothing_tip": "Neat casual; you'll go shoeless indoors.",
            "formality": "casual_smart",
        },
    ],
    "dubai": [
        {
            "name": "Burj Khalifa & Downtown",
            "type": "landmark",
            "description": "The world's tallest tower and the fountains.",
            "clothing_tip": "Smart-casual; malls are heavily air-conditioned — bring a layer.",
            "formality": "casual_smart",
        },
        {
            "name": "Sheikh Zayed Grand Mosque area",
            "type": "religious",
            "description": "Grand mosques expect conservative dress.",
            "clothing_tip": "Cover shoulders, arms and knees; women cover hair.",
            "formality": "smart",
        },
        {
            "name": "Old Dubai & Gold Souk",
            "type": "market",
            "description": "Creek abras and the historic souks.",
            "clothing_tip": "Modest and breathable; respect the traditional quarter.",
            "formality": "casual_smart",
        },
        {
            "name": "Desert safari",
            "type": "nature",
            "description": "Dune drives, camels and a camp dinner.",
            "clothing_tip": "Light layers plus something warm — nights get cold.",
            "formality": "casual",
        },
        {
            "name": "Jumeirah Beach",
            "type": "nature",
            "description": "Beaches under the Burj Al Arab.",
            "clothing_tip": "Beachwear on the sand only; cover up leaving it.",
            "formality": "casual",
        },
        {
            "name": "Fine dining, DIFC",
            "type": "restaurant",
            "description": "Michelin-tier restaurants downtown.",
            "clothing_tip": "Dress up — elegant, covered, smart shoes.",
            "formality": "formal",
        },
    ],
}

# Generic fallback for any unlisted destination.
_GENERIC = [
    {
        "name": "Old town & main square",
        "type": "landmark",
        "description": "The historic core — start here to get your bearings.",
        "clothing_tip": "Comfortable walking shoes and a light layer.",
        "formality": "casual",
    },
    {
        "name": "Principal museum or gallery",
        "type": "museum",
        "description": "The city's flagship collection.",
        "clothing_tip": "Smart-casual; galleries are cool inside.",
        "formality": "casual_smart",
    },
    {
        "name": "Central market",
        "type": "market",
        "description": "Local produce, street food and crafts.",
        "clothing_tip": "Light, washable clothing; it gets busy and warm.",
        "formality": "casual",
    },
    {
        "name": "Main place of worship",
        "type": "religious",
        "description": "The cathedral, mosque or temple locals point you to.",
        "clothing_tip": "Cover shoulders and knees; a scarf is useful.",
        "formality": "casual_smart",
    },
    {
        "name": "Riverside or park",
        "type": "nature",
        "description": "Green space or waterfront for a slower afternoon.",
        "clothing_tip": "Layers for changeable weather; sun cover.",
        "formality": "casual",
    },
    {
        "name": "Dinner district",
        "type": "restaurant",
        "description": "Where locals eat out in the evening.",
        "clothing_tip": "Smart-casual; a notch up from daytime.",
        "formality": "smart",
    },
]


def fallback_highlights(destination: str, limit: int = 8) -> list[dict]:
    """Curated places for a destination (case-insensitive substring match)."""
    dest = (destination or "").lower()
    for key, places in CURATED_PLACES.items():
        if key in dest:
            return [dict(p) for p in places][:limit]
    return [dict(p) for p in _GENERIC][:limit]


def merge_highlights(ai_highlights, destination: str, target: int = 8) -> list[dict]:
    """Combine AI highlights with curated ones (dedup by name) up to `target`."""
    out = [h for h in (ai_highlights or []) if isinstance(h, dict) and h.get("name")]
    seen = {(h.get("name") or "").strip().lower() for h in out}
    for p in fallback_highlights(destination, limit=len(_GENERIC) if not out else 8):
        if len(out) >= target:
            break
        key = p["name"].strip().lower()
        if key not in seen:
            out.append(p)
            seen.add(key)
    return out
