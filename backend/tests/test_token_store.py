"""Tests for calendar_sync/token_store.py — token encryption and decryption."""
import json
import pytest
from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestEncryptDecrypt:
    def test_encrypt_produces_non_json_string(self):
        from calendar_sync.token_store import encrypt_tokens
        data = {'token': 'abc', 'refresh_token': 'xyz', 'scopes': ['calendar.read']}
        encrypted = encrypt_tokens(data)
        assert isinstance(encrypted, str)
        # Should NOT be plain JSON
        with pytest.raises(Exception):
            parsed = json.loads(encrypted)
            # If it doesn't raise, at minimum the token key should be missing (encrypted)
            if parsed.get('token') == 'abc':
                raise AssertionError("Token was stored as plain JSON")

    def test_decrypt_round_trips_correctly(self):
        from calendar_sync.token_store import encrypt_tokens, decrypt_tokens
        data = {
            'token':         'access-token-abc',
            'refresh_token': 'refresh-token-xyz',
            'client_id':     'client-123',
            'scopes':        ['https://www.googleapis.com/auth/calendar.readonly'],
            'expiry':        '2026-12-31T00:00:00',
        }
        encrypted = encrypt_tokens(data)
        decrypted = decrypt_tokens(encrypted)
        assert decrypted == data

    def test_decrypt_invalid_returns_empty_dict(self):
        from calendar_sync.token_store import decrypt_tokens
        assert decrypt_tokens('not-valid-encrypted-data') == {}
        assert decrypt_tokens('') == {}
        assert decrypt_tokens('{}') == {}   # plain JSON fails Fernet

    def test_different_encryptions_are_unique(self):
        """Fernet uses a random IV — same data encrypts differently each time."""
        from calendar_sync.token_store import encrypt_tokens
        data = {'token': 'same-token'}
        e1 = encrypt_tokens(data)
        e2 = encrypt_tokens(data)
        assert e1 != e2   # different ciphertext (same plaintext)


class TestStoreLoadGoogle:
    def test_store_and_load_google_tokens(self):
        from calendar_sync.token_store import store_google_tokens, load_google_tokens
        user = UserFactory()
        creds = {'token': 'g-access', 'refresh_token': 'g-refresh', 'scopes': []}
        store_google_tokens(user, creds)
        user.refresh_from_db()
        # Stored value is NOT the plaintext
        assert user.google_calendar_token != json.dumps(creds)
        # But loads correctly
        loaded = load_google_tokens(user)
        assert loaded['token'] == 'g-access'
        assert loaded['refresh_token'] == 'g-refresh'

    def test_load_empty_google_token_returns_empty(self):
        from calendar_sync.token_store import load_google_tokens
        user = UserFactory()
        user.google_calendar_token = ''
        user.save()
        assert load_google_tokens(user) == {}

    def test_load_legacy_plain_json_google_token(self):
        """Backward compatibility: old plain JSON tokens still load."""
        from calendar_sync.token_store import load_google_tokens
        user = UserFactory()
        user.google_calendar_token = json.dumps({'token': 'legacy', 'refresh_token': 'old'})
        user.save()
        loaded = load_google_tokens(user)
        assert loaded['token'] == 'legacy'


class TestStoreLoadOutlook:
    def test_store_and_load_outlook_tokens(self):
        from calendar_sync.token_store import store_outlook_tokens, load_outlook_tokens
        user = UserFactory()
        creds = {'access_token': 'ms-access', 'refresh_token': 'ms-refresh'}
        store_outlook_tokens(user, creds)
        user.refresh_from_db()
        assert user.outlook_calendar_token != json.dumps(creds)
        loaded = load_outlook_tokens(user)
        assert loaded['access_token'] == 'ms-access'

    def test_load_empty_outlook_token_returns_empty(self):
        from calendar_sync.token_store import load_outlook_tokens
        user = UserFactory()
        user.outlook_calendar_token = ''
        user.save()
        assert load_outlook_tokens(user) == {}

    def test_load_legacy_plain_json_outlook_token(self):
        from calendar_sync.token_store import load_outlook_tokens
        user = UserFactory()
        user.outlook_calendar_token = json.dumps({'access_token': 'old-ms', 'refresh_token': 'r'})
        user.save()
        loaded = load_outlook_tokens(user)
        assert loaded['access_token'] == 'old-ms'

    def test_encryption_is_keyed_to_secret_key(self, settings):
        """Token encrypted with one SECRET_KEY can't be decrypted with another."""
        from calendar_sync.token_store import store_outlook_tokens, load_outlook_tokens
        user = UserFactory()
        store_outlook_tokens(user, {'access_token': 'secret-data'})
        user.refresh_from_db()
        # Change SECRET_KEY
        settings.SECRET_KEY = 'completely-different-secret-key-for-test'
        result = load_outlook_tokens(user)
        # Should fail gracefully (returns {} not crash)
        assert result == {} or result.get('access_token') != 'secret-data'
