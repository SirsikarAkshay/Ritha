"""Google social sign-in — verify ID token, find-or-create user, mint JWT."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from .factories import UserFactory

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/auth/social/google/"
VERIFY = "google.oauth2.id_token.verify_oauth2_token"


def _payload(email="new@ritha.com", sub="google-123", verified=True, aud="test-client-id", **extra):
    p = {
        "email": email,
        "email_verified": verified,
        "sub": sub,
        "aud": aud,
        "given_name": "Sam",
        "family_name": "Lee",
    }
    p.update(extra)
    return p


class TestGoogleLogin:
    @pytest.fixture(autouse=True)
    def _configure(self, settings):
        settings.GOOGLE_CLIENT_ID = "test-client-id"

    def test_new_user_created_and_tokens_returned(self, client):
        with patch(VERIFY, return_value=_payload()):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 200
        body = r.json()
        assert body["access"] and body["refresh"] and body["created"] is True
        u = User.objects.get(email="new@ritha.com")
        assert u.is_email_verified is True
        assert u.auth_provider == "google"
        assert u.google_sub == "google-123"
        assert u.first_name == "Sam"
        assert not u.has_usable_password()  # social-only account

    def test_links_existing_email_account(self, client):
        existing = UserFactory(email="me@ritha.com")  # email/password account
        with patch(VERIFY, return_value=_payload(email="me@ritha.com", sub="g-9")):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 200
        assert r.json()["created"] is False
        assert User.objects.filter(email="me@ritha.com").count() == 1  # no duplicate
        existing.refresh_from_db()
        assert existing.google_sub == "g-9"
        assert existing.is_email_verified is True

    def test_case_insensitive_email_link(self, client):
        UserFactory(email="mixed@ritha.com")
        with patch(VERIFY, return_value=_payload(email="MIXED@ritha.com", sub="g-1")):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 200
        assert User.objects.filter(email__iexact="mixed@ritha.com").count() == 1

    def test_missing_token_400(self, client):
        r = client.post(URL, {}, content_type="application/json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "missing_token"

    def test_unverified_email_rejected(self, client):
        with patch(VERIFY, return_value=_payload(verified=False)):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "email_unverified"

    def test_invalid_token_401(self, client):
        with patch(VERIFY, side_effect=ValueError("bad token")):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "invalid_token"

    def test_audience_not_in_allowlist_rejected(self, client):
        with patch(VERIFY, return_value=_payload(aud="some-other-app")):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 401

    def test_native_client_audience_accepted(self, client, settings):
        # Mobile ID tokens carry a native client id as aud — accepted via the
        # comma-separated allowlist.
        settings.GOOGLE_CLIENT_ID = "web-client,android-client.apps.googleusercontent.com"
        with patch(VERIFY, return_value=_payload(aud="android-client.apps.googleusercontent.com")):
            r = client.post(URL, {"credential": "tok"}, content_type="application/json")
        assert r.status_code == 200


@pytest.mark.django_db
def test_google_not_configured_503(client, settings):
    settings.GOOGLE_CLIENT_ID = ""
    r = client.post(URL, {"credential": "tok"}, content_type="application/json")
    assert r.status_code == 503


# ── Apple ──────────────────────────────────────────────────────────────────
APPLE_URL = "/api/auth/social/apple/"
APPLE_VERIFY = "auth_app.views._verify_apple_token"


def _apple_payload(email="apple@ritha.com", sub="apple-abc", **extra):
    p = {"email": email, "email_verified": "true", "sub": sub}
    p.update(extra)
    return p


class TestAppleLogin:
    @pytest.fixture(autouse=True)
    def _configure(self, settings):
        settings.APPLE_CLIENT_ID = "com.ritha.web"

    def test_new_user_with_name_from_body(self, client):
        with patch(APPLE_VERIFY, return_value=_apple_payload()):
            r = client.post(
                APPLE_URL,
                {"id_token": "tok", "first_name": "Ada", "last_name": "Lovelace"},
                content_type="application/json",
            )
        assert r.status_code == 200
        assert r.json()["created"] is True
        u = User.objects.get(email="apple@ritha.com")
        assert u.auth_provider == "apple"
        assert u.apple_sub == "apple-abc"
        assert u.first_name == "Ada" and u.last_name == "Lovelace"
        assert u.is_email_verified is True
        assert not u.has_usable_password()

    def test_links_existing_email_account(self, client):
        existing = UserFactory(email="dup@ritha.com")
        with patch(APPLE_VERIFY, return_value=_apple_payload(email="dup@ritha.com", sub="a-2")):
            r = client.post(APPLE_URL, {"id_token": "tok"}, content_type="application/json")
        assert r.status_code == 200
        assert r.json()["created"] is False
        assert User.objects.filter(email="dup@ritha.com").count() == 1
        existing.refresh_from_db()
        assert existing.apple_sub == "a-2"

    def test_returning_hide_my_email_matches_by_sub(self, client):
        # First sign-in shares an email and creates the account.
        with patch(APPLE_VERIFY, return_value=_apple_payload(email="hide@ritha.com", sub="a-9")):
            client.post(APPLE_URL, {"id_token": "t1"}, content_type="application/json")
        # A later sign-in with no email must still resolve to the same user via sub.
        with patch(APPLE_VERIFY, return_value=_apple_payload(email="", sub="a-9")):
            r = client.post(APPLE_URL, {"id_token": "t2"}, content_type="application/json")
        assert r.status_code == 200
        assert r.json()["created"] is False
        assert User.objects.filter(apple_sub="a-9").count() == 1

    def test_new_user_without_email_400(self, client):
        with patch(APPLE_VERIFY, return_value=_apple_payload(email="", sub="a-new")):
            r = client.post(APPLE_URL, {"id_token": "tok"}, content_type="application/json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "no_email"

    def test_missing_token_400(self, client):
        r = client.post(APPLE_URL, {}, content_type="application/json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "missing_token"

    def test_invalid_token_401(self, client):
        with patch(APPLE_VERIFY, side_effect=ValueError("bad")):
            r = client.post(APPLE_URL, {"id_token": "tok"}, content_type="application/json")
        assert r.status_code == 401


@pytest.mark.django_db
def test_apple_not_configured_503(client, settings):
    settings.APPLE_CLIENT_ID = ""
    r = client.post(APPLE_URL, {"id_token": "tok"}, content_type="application/json")
    assert r.status_code == 503
