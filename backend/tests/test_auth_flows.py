"""
Tests for the fixed auth flows:
  - Login returns clear 401 (not 500) on wrong password / unknown user
  - Login returns 403 (not 500) for unverified accounts
  - Register returns structured field errors (not 500)
  - Forgot password flow (request + consume)
  - Reset password flow (validation, expiry, success)
"""
import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from .factories import UserFactory

pytestmark = pytest.mark.django_db


# ── Login error cases ─────────────────────────────────────────────────────

class TestLoginErrors:
    def test_wrong_password_returns_401_not_500(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/login/',
                        {'email': user.email, 'password': 'completely-wrong'},
                        content_type='application/json')
        assert r.status_code == 401
        assert 'error' in r.json() or 'detail' in r.json()

    def test_unknown_email_returns_401_not_500(self, client):
        r = client.post('/api/auth/login/',
                        {'email': 'nobody@nowhere.com', 'password': 'anything'},
                        content_type='application/json')
        assert r.status_code == 401

    def test_unverified_user_returns_403_not_500(self, client):
        user = UserFactory(is_email_verified=False)
        r = client.post('/api/auth/login/',
                        {'email': user.email, 'password': 'testpass99'},
                        content_type='application/json')
        assert r.status_code == 403
        data = r.json()
        assert data['error']['code'] == 'email_not_verified'
        assert data['error']['email'] == user.email  # for resend UX

    def test_verified_user_gets_tokens(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/login/',
                        {'email': user.email, 'password': 'testpass99'},
                        content_type='application/json')
        assert r.status_code == 200
        assert 'access' in r.json()
        assert 'refresh' in r.json()

    def test_empty_body_returns_400_not_500(self, client):
        r = client.post('/api/auth/login/', {}, content_type='application/json')
        assert r.status_code in (400, 401)  # not 500


# ── Register error cases ───────────────────────────────────────────────────

class TestRegisterErrors:
    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_duplicate_email_returns_400_not_500(self, mock_send, client):
        user = UserFactory()
        r = client.post('/api/auth/register/',
                        {'email': user.email, 'password': 'newpassword99'},
                        content_type='application/json')
        assert r.status_code == 400
        data = r.json()
        assert data['error']['code'] == 'validation_error'
        # Should have field-level errors
        assert 'detail' in data['error']

    def test_short_password_returns_400_with_message(self, client):
        r = client.post('/api/auth/register/',
                        {'email': 'new@test.com', 'password': 'short'},
                        content_type='application/json')
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'validation_error'

    def test_missing_email_returns_400(self, client):
        r = client.post('/api/auth/register/',
                        {'password': 'testpass99'},
                        content_type='application/json')
        assert r.status_code == 400

    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_valid_register_returns_201(self, mock_send, client):
        r = client.post('/api/auth/register/',
                        {'email': 'brand@new.com', 'password': 'goodpass99'},
                        content_type='application/json')
        assert r.status_code == 201
        assert r.json()['email'] == 'brand@new.com'

    def test_invalid_email_format_returns_400(self, client):
        r = client.post('/api/auth/register/',
                        {'email': 'not-an-email', 'password': 'testpass99'},
                        content_type='application/json')
        assert r.status_code == 400


# ── Forgot password ────────────────────────────────────────────────────────

class TestForgotPassword:
    @patch('auth_app.views.send_password_reset_email', return_value=True)
    def test_sends_reset_email_for_known_address(self, mock_send, client):
        user = UserFactory()
        r = client.post('/api/auth/forgot-password/',
                        {'email': user.email},
                        content_type='application/json')
        assert r.status_code == 200
        assert mock_send.called

    def test_unknown_email_returns_200_anyway(self, client):
        """Never reveal whether an email is registered."""
        r = client.post('/api/auth/forgot-password/',
                        {'email': 'ghost@nowhere.com'},
                        content_type='application/json')
        assert r.status_code == 200
        assert 'reset link' in r.json()['message'].lower()

    def test_missing_email_returns_400(self, client):
        r = client.post('/api/auth/forgot-password/', {}, content_type='application/json')
        assert r.status_code == 400

    @patch('auth_app.views.send_password_reset_email', return_value=True)
    def test_inactive_user_silently_ignored(self, mock_send, client):
        user = UserFactory(is_active=False)
        client.post('/api/auth/forgot-password/',
                    {'email': user.email},
                    content_type='application/json')
        assert not mock_send.called

    @patch('auth_app.email.send_mail')
    def test_reset_email_contains_token_and_link(self, mock_mail, client):
        mock_mail.return_value = 1
        user = UserFactory()
        from auth_app.email import send_password_reset_email
        send_password_reset_email(user)
        user.refresh_from_db()
        assert len(user.password_reset_token) == 48
        assert user.password_reset_created_at is not None
        # Check email content
        html = mock_mail.call_args[1]['html_message']
        assert user.password_reset_token in html
        assert 'reset-password' in html


# ── Reset password ─────────────────────────────────────────────────────────

class TestResetPassword:
    def _setup_user_with_token(self, token='resettoken123'):
        user = UserFactory()
        user.password_reset_token      = token
        user.password_reset_created_at = timezone.now()
        user.save()
        return user

    def test_valid_token_resets_password(self, client):
        user  = self._setup_user_with_token()
        token = user.password_reset_token
        r = client.post('/api/auth/reset-password/', {
            'token': token, 'email': user.email, 'new_password': 'BrandNew99!',
        }, content_type='application/json')
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.check_password('BrandNew99!')

    def test_can_login_after_reset(self, client):
        user  = self._setup_user_with_token()
        token = user.password_reset_token
        client.post('/api/auth/reset-password/', {
            'token': token, 'email': user.email, 'new_password': 'BrandNew99!',
        }, content_type='application/json')
        r = client.post('/api/auth/login/',
                        {'email': user.email, 'password': 'BrandNew99!'},
                        content_type='application/json')
        assert r.status_code == 200

    def test_token_cleared_after_use(self, client):
        user  = self._setup_user_with_token('clearmetoken')
        client.post('/api/auth/reset-password/', {
            'token': 'clearmetoken', 'email': user.email, 'new_password': 'NewPass99!',
        }, content_type='application/json')
        user.refresh_from_db()
        assert user.password_reset_token == ''
        assert user.password_reset_created_at is None

    def test_expired_token_returns_400(self, client):
        user = UserFactory()
        user.password_reset_token      = 'expiredtoken'
        user.password_reset_created_at = timezone.now() - timedelta(hours=2)
        user.save()
        r = client.post('/api/auth/reset-password/', {
            'token': 'expiredtoken', 'email': user.email, 'new_password': 'NewPass99!',
        }, content_type='application/json')
        assert r.status_code == 400
        assert 'expired' in r.json()['error']['message'].lower()

    def test_wrong_token_returns_400(self, client):
        user = self._setup_user_with_token()
        r = client.post('/api/auth/reset-password/', {
            'token': 'completely-wrong-token', 'email': user.email, 'new_password': 'NewPass99!',
        }, content_type='application/json')
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'invalid_token'

    def test_short_password_rejected(self, client):
        user = self._setup_user_with_token()
        r = client.post('/api/auth/reset-password/', {
            'token': user.password_reset_token, 'email': user.email, 'new_password': 'short',
        }, content_type='application/json')
        assert r.status_code == 400
        assert 'short' in r.json()['error']['message'].lower() or 'characters' in r.json()['error']['message'].lower()

    def test_missing_fields_returns_400(self, client):
        r = client.post('/api/auth/reset-password/', {}, content_type='application/json')
        assert r.status_code == 400

    def test_unknown_email_returns_404(self, client):
        r = client.post('/api/auth/reset-password/', {
            'token': 'anytoken', 'email': 'ghost@nowhere.com', 'new_password': 'NewPass99!',
        }, content_type='application/json')
        assert r.status_code == 404
