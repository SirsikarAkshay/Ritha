"""
Fashion model inference — classify images and score outfit compatibility.

Loads trained artefacts from ml/artifacts/ and exposes:
  - classify_image(image_path) → predicted category + confidence
  - get_embedding(image_path)  → 1280-d feature vector
  - compatibility_score(cat_a, cat_b) → float 0..1
  - suggest_compatible(category, top_k) → list of compatible categories
  - score_outfit(categories) → overall outfit compatibility score
  - weather_filter(categories, weather) → filtered + scored list
"""

import logging
from pathlib import Path

import joblib
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from ml.categories import (
    CATEGORY_TO_IDX,
    DATASET_CATEGORIES,
    DATASET_TO_WARDROBE,
    IDX_TO_CATEGORY,
    NUM_CATEGORIES,
    WEATHER_CATEGORY_RULES,
)

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"


# ── Lazy loaders ─────────────────────────────────────────────────────────────

_model_cache = {}
_compat_cache = {}


def _load_model():
    if "model" in _model_cache:
        return _model_cache["model"], _model_cache["device"]

    from ml.train import build_model

    ckpt_path = ARTIFACTS_DIR / "fashion_classifier.pth"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"No trained model at {ckpt_path}. Run: python -m ml.train")

    device = torch.device(
        "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    )
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model = build_model(num_classes=ckpt.get("num_classes", NUM_CATEGORIES), pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()

    _model_cache["model"] = model
    _model_cache["device"] = device
    return model, device


def _load_compatibility():
    if "matrix" in _compat_cache:
        return _compat_cache["matrix"]

    pkl_path = ARTIFACTS_DIR / "compatibility.pkl"
    if not pkl_path.exists():
        # No trained matrix (e.g. CI, or a fresh deploy without ML artifacts).
        # Degrade gracefully — callers treat None as neutral compatibility —
        # rather than raising and 500-ing every recommendation. Cached so we
        # don't stat the missing file on every call.
        _compat_cache["matrix"] = None
        return None

    data = joblib.load(pkl_path)
    _compat_cache["matrix"] = data["matrix"]
    return data["matrix"]


_val_transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


# ── Public API ───────────────────────────────────────────────────────────────


def classify_image(image_path: str) -> dict:
    """Classify a clothing image → {category, confidence, top3}."""
    model, device = _load_model()
    img = Image.open(image_path).convert("RGB")
    tensor = _val_transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]

    top3_idx = probs.argsort(descending=True)[:3]
    return {
        "category": IDX_TO_CATEGORY[top3_idx[0].item()],
        "confidence": round(probs[top3_idx[0]].item(), 4),
        "top3": [{"category": IDX_TO_CATEGORY[i.item()], "confidence": round(probs[i].item(), 4)} for i in top3_idx],
    }


def get_embedding(image_path: str) -> np.ndarray:
    """Extract a 1280-d feature vector from the penultimate layer."""
    model, device = _load_model()
    img = Image.open(image_path).convert("RGB")
    tensor = _val_transform(img).unsqueeze(0).to(device)

    features = None

    def hook(module, inp, out):
        nonlocal features
        features = out.detach().cpu()

    # Register hook on the pooling layer (before classifier)
    handle = model.classifier[0].register_forward_hook(hook)
    with torch.no_grad():
        model(tensor)
    handle.remove()

    # features shape: (1, 1280) after dropout
    return features.squeeze().numpy()


def compatibility_score(cat_a: str, cat_b: str) -> float:
    """Return co-occurrence compatibility score between two categories (0..1)."""
    matrix = _load_compatibility()
    if matrix is None:
        return 0.5  # neutral when no trained matrix is available
    idx_a = CATEGORY_TO_IDX.get(cat_a)
    idx_b = CATEGORY_TO_IDX.get(cat_b)
    if idx_a is None or idx_b is None:
        return 0.0
    return float(matrix[idx_a][idx_b])


def suggest_compatible(category: str, top_k: int = 5) -> list[dict]:
    """Return top-K categories most compatible with the given category."""
    matrix = _load_compatibility()
    idx = CATEGORY_TO_IDX.get(category)
    if matrix is None or idx is None:
        return []

    scores = matrix[idx].copy()
    scores[idx] = -1  # exclude self
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [
        {
            "category": IDX_TO_CATEGORY[int(i)],
            "wardrobe_category": DATASET_TO_WARDROBE.get(IDX_TO_CATEGORY[int(i)], "other"),
            "score": round(float(scores[i]), 4),
        }
        for i in top_indices
        if scores[i] > 0
    ]


def score_outfit(categories: list[str]) -> float:
    """Score an outfit (list of categories) by average pairwise compatibility."""
    if len(categories) < 2:
        return 1.0
    matrix = _load_compatibility()
    if matrix is None:
        return 0.5  # neutral when no trained matrix is available
    scores = []
    for i, cat_a in enumerate(categories):
        for cat_b in categories[i + 1 :]:
            idx_a = CATEGORY_TO_IDX.get(cat_a)
            idx_b = CATEGORY_TO_IDX.get(cat_b)
            if idx_a is not None and idx_b is not None:
                scores.append((matrix[idx_a][idx_b] + matrix[idx_b][idx_a]) / 2)
    return float(np.mean(scores)) if scores else 0.0


def score_outfit_by_embeddings(item_ids: list[int]) -> float | None:
    """Score outfit by pairwise compatibility from stored item embeddings.

    Returns a value in [0, 1] when every item has a stored embedding,
    or None when any are missing — callers should fall back to the
    category-pair scorer.

    Compatibility is mapped from cosine similarity via a sweet-spot
    function:
        sim ≈ 1.0   →  near-duplicates (same item / two black tees)  → ~0.4
        sim ≈ 0.5   →  pleasing variety (related but distinct)       → ~1.0
        sim ≈ 0.0   →  unrelated items (different category & style)  → ~0.7

    The peak at 0.5 reflects the embedding distribution observed for
    well-rated outfits in the dataset: they pair items that share *some*
    visual signal (color/material/silhouette) but aren't redundant.
    """
    if len(item_ids) < 2:
        return 1.0

    from wardrobe.models import ClothingItem

    rows = list(ClothingItem.objects.filter(id__in=item_ids).values("id", "embedding"))
    by_id = {r["id"]: r["embedding"] for r in rows}

    embeddings = []
    for iid in item_ids:
        blob = by_id.get(iid)
        if not blob:
            return None  # missing embedding — caller falls back
        emb = np.frombuffer(blob, dtype=np.float32)
        n = np.linalg.norm(emb)
        if n == 0:
            return None
        embeddings.append(emb / n)

    embeddings = np.stack(embeddings)
    sims = embeddings @ embeddings.T  # cosine, since rows are unit-normalized

    n = len(embeddings)
    pair_scores = []
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sims[i, j])
            # Triangular peak at 0.5; floor at 0.4 for both extremes.
            score = 1.0 - 2.0 * abs(s - 0.5)
            if s < 0.5:  # bias low-similarity pairs upward —
                score = 0.7 + 0.3 * score  # different items aren't a problem
            pair_scores.append(max(0.0, min(1.0, score)))

    return float(np.mean(pair_scores)) if pair_scores else 1.0


def weather_appropriate_categories(weather: dict) -> dict:
    """Given a weather snapshot, return preferred/avoided categories with scores."""
    temp = weather.get("temp_c", 20)
    wind = weather.get("wind_kmh", 0) or 0
    humidity = weather.get("humidity", 60) or 60
    is_raining = weather.get("is_raining", False)

    # Feels-like temperature (wind chill + heat index approximation)
    feels_like = temp
    if temp <= 10 and wind > 5:
        feels_like = 13.12 + 0.6215 * temp - 11.37 * (wind**0.16) + 0.3965 * temp * (wind**0.16)
    elif temp > 26 and humidity > 40:
        feels_like = temp + 0.33 * (humidity / 100 * 6.105 * 2.7183 ** (17.27 * temp / (237.7 + temp))) - 4.0

    if feels_like < 0:
        bucket = "freezing"
    elif feels_like < 8:
        bucket = "cold"
    elif feels_like < 15:
        bucket = "cool"
    elif feels_like < 22:
        bucket = "mild"
    elif feels_like < 28:
        bucket = "warm"
    else:
        bucket = "hot"

    rules = WEATHER_CATEGORY_RULES[bucket].copy()
    if is_raining:
        rainy = WEATHER_CATEGORY_RULES["rainy"]
        rules["prefer"] = list(set(rules["prefer"] + rainy["prefer"]))
        rules["avoid"] = list(set(rules["avoid"] + rainy["avoid"]))
    if wind > 30:
        windy = WEATHER_CATEGORY_RULES["windy"]
        rules["prefer"] = list(set(rules["prefer"] + windy["prefer"]))
        rules["avoid"] = list(set(rules["avoid"] + windy["avoid"]))

    scores = {}
    for cat in DATASET_CATEGORIES:
        if cat in rules.get("prefer", []):
            scores[cat] = 1.0
        elif cat in rules.get("avoid", []):
            scores[cat] = 0.1
        else:
            scores[cat] = 0.5

    return {
        "weather_bucket": bucket,
        "feels_like_c": round(feels_like, 1),
        "is_raining": is_raining,
        "category_scores": scores,
        "preferred": rules.get("prefer", []),
        "avoided": rules.get("avoid", []),
    }
