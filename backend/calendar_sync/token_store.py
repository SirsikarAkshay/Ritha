"""
Encrypted token storage for calendar OAuth credentials.
Uses Fernet symmetric encryption derived from Django SECRET_KEY.
Same approach as apple_calendar.py password encryption.
"""
import base64, hashlib, json
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
    return Fernet(key)


def encrypt_tokens(data: dict) -> str:
    """Encrypt a token dict to a string for storage."""
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_tokens(encrypted: str) -> dict:
    """Decrypt and parse a stored token string. Returns {} on failure."""
    try:
        return json.loads(_fernet().decrypt(encrypted.encode()))
    except (InvalidToken, Exception):
        return {}


def store_google_tokens(user, creds_dict: dict) -> None:
    user.google_calendar_token = encrypt_tokens(creds_dict)
    user.save(update_fields=["google_calendar_token"])


def load_google_tokens(user) -> dict:
    if not user.google_calendar_token:
        return {}
    # Try Fernet decryption first (new tokens)
    result = decrypt_tokens(user.google_calendar_token)
    if result:
        return result
    # Fall back to plain JSON for legacy tokens
    try:
        return json.loads(user.google_calendar_token)
    except Exception:
        return {}


def store_outlook_tokens(user, creds_dict: dict) -> None:
    user.outlook_calendar_token = encrypt_tokens(creds_dict)
    user.save(update_fields=["outlook_calendar_token"])


def load_outlook_tokens(user) -> dict:
    if not user.outlook_calendar_token:
        return {}
    result = decrypt_tokens(user.outlook_calendar_token)
    if result:
        return result
    try:
        return json.loads(user.outlook_calendar_token)
    except Exception:
        return {}
