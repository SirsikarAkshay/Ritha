"""
Mistral AI client for Ritha agents.

All AI calls go through this module. Switch models by changing DEFAULT_MODEL
or pass `model=` explicitly to any function.

Available models (fastest → most capable):
  mistral-small-latest   — structured tasks, JSON generation   ← default
  mistral-medium-latest  — balanced quality/speed
  mistral-large-latest   — complex multi-step reasoning

Usage:
    from ritha.services.mistral_client import chat_json, _has_mistral

    if _has_mistral():
        result = chat_json("Recommend an outfit. Return JSON: {item_ids: [...]}")
"""
import json
import logging
import time
from django.conf import settings

logger = logging.getLogger('ritha.mistral')

DEFAULT_MODEL = 'mistral-small-latest'
DEFAULT_VISION_MODEL = 'pixtral-12b-latest'

# Models to try in order when the primary model returns 429 capacity errors.
# Pick models with different capacity pools so a fallback is likely to succeed.
TEXT_FALLBACK_MODELS = [
    'mistral-small-latest',
    'mistral-medium-latest',
    'mistral-large-latest',
]
VISION_FALLBACK_MODELS = [
    'pixtral-12b-latest',
    'pixtral-large-latest',
]

# Retry policy for transient 429s. Total worst case: ~0.5 + 1 + 2 + 4 = 7.5 s
# before moving on to the next fallback model.
RETRY_DELAYS_SECONDS = [0.5, 1.0, 2.0, 4.0]


def _is_capacity_error(exc: Exception) -> bool:
    """Return True if this exception represents a Mistral 429 / capacity error."""
    text = str(exc).lower()
    return (
        'status 429' in text
        or 'service_tier_capacity_exceeded' in text
        or 'rate limit' in text
        or 'capacity exceeded' in text
    )


def _call_with_retries(invoke, models: list[str]):
    """Run `invoke(model)` with retry + model-fallback on 429.

    Returns the raw assistant content string on success.
    Raises the last exception if every (model, retry) combination fails.
    """
    last_exc = None
    for model in models:
        for attempt, delay in enumerate([0.0] + RETRY_DELAYS_SECONDS):
            if delay:
                time.sleep(delay)
            try:
                return invoke(model), model
            except Exception as exc:
                last_exc = exc
                if _is_capacity_error(exc):
                    logger.warning(
                        'Mistral capacity error on %s (attempt %d/%d): %s',
                        model, attempt + 1, len(RETRY_DELAYS_SECONDS) + 1, exc,
                    )
                    continue  # retry same model, then move to next model
                # Non-capacity error — don't waste retries, just re-raise
                raise
        logger.warning('Mistral model %s exhausted retries; trying fallback', model)
    # All models / all retries failed
    raise last_exc  # pragma: no cover


def _has_mistral() -> bool:
    """Return True if a usable Mistral API key is configured."""
    key = getattr(settings, 'MISTRAL_API_KEY', '')
    return bool(key) and key not in ('your_mistral_key_here', '', 'your_key')


def _get_client():
    """Return an authenticated Mistral client."""
    from mistralai import Mistral
    return Mistral(api_key=settings.MISTRAL_API_KEY)


def chat(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Send a single user prompt and return the raw text response.

    On a 429 capacity error, retries with exponential backoff and then falls
    back to larger models in TEXT_FALLBACK_MODELS before giving up.

    Args:
        prompt: The user message to send.
        model:  Preferred model name (defaults to DEFAULT_MODEL).

    Returns:
        The assistant's reply as a plain string.
    """
    client = _get_client()

    def invoke(m):
        response = client.chat.complete(
            model=m,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return response.choices[0].message.content

    # Try the requested model first, then remaining fallbacks in order.
    models = [model] + [m for m in TEXT_FALLBACK_MODELS if m != model]
    content, used = _call_with_retries(invoke, models)
    logger.debug('Mistral %s → %d chars', used, len(content))
    return content


def chat_json(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Send a prompt that expects a JSON response and return the parsed dict.

    Automatically:
    - Appends a JSON-only instruction to the prompt
    - Strips markdown code fences (```json ... ```) from the response
    - Parses and returns the result as a Python dict

    Args:
        prompt: The user message. Should describe expected JSON shape.
        model:  Mistral model name (defaults to DEFAULT_MODEL).

    Returns:
        Parsed dict from the model's response.

    Raises:
        ValueError: if the model returns non-JSON content.
        MistralAPIException: on auth or network errors.
    """
    full_prompt = (
        prompt
        + '\n\nIMPORTANT: Respond ONLY with valid JSON. '
        + 'No markdown fences, no explanation, no preamble.'
    )
    raw = chat(full_prompt, model)

    # Strip ```json ... ``` or ``` ... ``` fences
    clean = raw.strip()
    if clean.startswith('```'):
        # Remove opening fence line
        clean = clean.split('\n', 1)[-1]
        # Remove closing fence
        if clean.endswith('```'):
            clean = clean[: clean.rfind('```')]

    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.warning(
            'Mistral returned non-JSON (%s). Raw response (first 300 chars): %.300s',
            exc, raw
        )
        raise ValueError(
            f'Mistral did not return valid JSON: {exc}\n'
            f'Raw response: {raw[:300]}'
        ) from exc


def _strip_json_fences(raw: str) -> str:
    clean = raw.strip()
    if clean.startswith('```'):
        clean = clean.split('\n', 1)[-1]
        if clean.endswith('```'):
            clean = clean[: clean.rfind('```')]
    return clean.strip()


def chat_image_json(prompt: str, image_bytes: bytes, mime_type: str = 'image/jpeg',
                    model: str = DEFAULT_VISION_MODEL) -> dict:
    """
    Send a vision prompt (text + one image) that expects a JSON response.

    Uses Pixtral by default. The image is sent inline as a base64 data URL.

    Args:
        prompt: Instructions describing the expected JSON shape.
        image_bytes: Raw image bytes (read from the uploaded file).
        mime_type: Image MIME type, e.g. 'image/jpeg', 'image/png'.
        model: Mistral vision model name.

    Returns:
        Parsed dict from the model's response.

    Raises:
        ValueError: if the model returns non-JSON content.
    """
    import base64
    client = _get_client()
    b64 = base64.b64encode(image_bytes).decode('ascii')
    data_url = f'data:{mime_type};base64,{b64}'

    full_prompt = (
        prompt
        + '\n\nIMPORTANT: Respond ONLY with valid JSON. '
        + 'No markdown fences, no explanation, no preamble.'
    )

    def invoke(m):
        response = client.chat.complete(
            model=m,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text',      'text': full_prompt},
                    {'type': 'image_url', 'image_url': data_url},
                ],
            }],
        )
        return response.choices[0].message.content

    models = [model] + [m for m in VISION_FALLBACK_MODELS if m != model]
    raw, used = _call_with_retries(invoke, models)
    logger.debug('Pixtral %s → %d chars', used, len(raw))

    clean = _strip_json_fences(raw)
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.warning(
            'Pixtral returned non-JSON (%s). Raw response (first 300 chars): %.300s',
            exc, raw,
        )
        raise ValueError(
            f'Pixtral did not return valid JSON: {exc}\nRaw response: {raw[:300]}'
        ) from exc
