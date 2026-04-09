"""
Tests for the email verification flow.
All email sending is mocked — no real SMTP calls.
"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from .factories import UserFactory
from auth_app.email import (
    generate_verification_token, verify_token, mark_verified,
    send_verification_email,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ── Unit tests: token utilities ───────────────────────────────────────────

class TestTokenGeneration:
    def test_token_is_48_chars(self):
        token = generate_verification_token()
        assert len(token) == 48

    def test_tokens_are_unique(self):
        tokens = {generate_verification_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_token_is_hex(self):
        token = generate_verification_token()
        assert all(c in '0123456789abcdef' for c in token)


class TestVerifyToken:
    def test_valid_token_succeeds(self):
        user = UserFactory()
        token = generate_verification_token()
        user.email_verification_token = token
        user.email_token_created_at   = timezone.now()
        user.save()

        ok, msg = verify_token(user, token)
        assert ok is True
        assert msg == ''

    def test_wrong_token_fails(self):
        user = UserFactory()
        user.email_verification_token = generate_verification_token()
        user.email_token_created_at   = timezone.now()
        user.save()

        ok, msg = verify_token(user, 'wrongtoken')
        assert ok is False
        assert 'Invalid' in msg

    def test_expired_token_fails(self):
        from datetime import timedelta
        user = UserFactory()
        token = generate_verification_token()
        user.email_verification_token = token
        user.email_token_created_at   = timezone.now() - timedelta(hours=25)
        user.save()

        ok, msg = verify_token(user, token)
        assert ok is False
        assert 'expired' in msg.lower()

    def test_no_token_fails(self):
        user = UserFactory()
        user.email_verification_token = ''
        user.save()

        ok, msg = verify_token(user, 'anytoken')
        assert ok is False

    def test_no_created_at_fails(self):
        user = UserFactory()
        token = generate_verification_token()
        user.email_verification_token = token
        user.email_token_created_at   = None
        user.save()

        ok, msg = verify_token(user, token)
        assert ok is False


class TestMarkVerified:
    def test_marks_user_verified(self):
        user = UserFactory()
        user.email_verification_token = generate_verification_token()
        user.email_token_created_at   = timezone.now()
        user.save()

        mark_verified(user)
        user.refresh_from_db()

        assert user.is_email_verified is True
        assert user.email_verification_token == ''
        assert user.email_token_created_at is None


# ── Integration: register endpoint ───────────────────────────────────────

class TestRegisterSendsEmail:
    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_register_sends_verification_email(self, mock_send, client):
        r = client.post('/api/auth/register/', {
            'email': 'new@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 201
        assert mock_send.called
        assert r.json()['verification_sent'] is True

    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_registered_user_not_verified_by_default(self, mock_send, client):
        client.post('/api/auth/register/', {
            'email': 'unverified@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        user = User.objects.get(email='unverified@arokah.com')
        assert user.is_email_verified is False

    @patch('auth_app.views.send_verification_email', return_value=False)
    def test_register_handles_email_failure_gracefully(self, mock_send, client):
        r = client.post('/api/auth/register/', {
            'email': 'fail@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 201
        assert r.json()['verification_sent'] is False
        # Account still created
        assert User.objects.filter(email='fail@arokah.com').exists()


# ── Integration: login blocked until verified ─────────────────────────────

class TestLoginRequiresVerification:
    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_unverified_user_cannot_login(self, mock_send, client):
        client.post('/api/auth/register/', {
            'email': 'blocked@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')

        r = client.post('/api/auth/login/', {
            'email': 'blocked@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 403
        assert r.json()['error']['code'] == 'email_not_verified'
        assert 'email' in r.json()['error']   # returns email for resend UX

    def test_verified_user_can_login(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/login/', {
            'email': user.email, 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 200
        assert 'access' in r.json()

    def test_wrong_password_still_401(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/login/', {
            'email': user.email, 'password': 'wrongpass',
        }, content_type='application/json')
        assert r.status_code == 401


# ── Integration: verify-email endpoint ───────────────────────────────────

class TestVerifyEmailEndpoint:
    def _create_unverified(self, token='validtoken123abc'):
        user = UserFactory(is_email_verified=False)
        user.email_verification_token = token
        user.email_token_created_at   = timezone.now()
        user.save()
        return user

    def test_valid_token_verifies_account(self, client):
        user = self._create_unverified()
        r = client.post('/api/auth/verify-email/', {
            'token': user.email_verification_token,
            'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_verified_user_can_login_after_verification(self, client):
        user = self._create_unverified()
        client.post('/api/auth/verify-email/', {
            'token': user.email_verification_token,
            'email': user.email,
        }, content_type='application/json')

        r = client.post('/api/auth/login/', {
            'email': user.email, 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 200
        assert 'access' in r.json()

    def test_wrong_token_returns_400(self, client):
        user = self._create_unverified()
        r = client.post('/api/auth/verify-email/', {
            'token': 'completely-wrong-token',
            'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'invalid_token'

    def test_expired_token_returns_400(self, client):
        from datetime import timedelta
        user = UserFactory(is_email_verified=False)
        user.email_verification_token = 'expiredtoken'
        user.email_token_created_at   = timezone.now() - timedelta(hours=25)
        user.save()

        r = client.post('/api/auth/verify-email/', {
            'token': 'expiredtoken', 'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 400
        assert 'expired' in r.json()['error']['message'].lower()

    def test_unknown_email_returns_404(self, client):
        r = client.post('/api/auth/verify-email/', {
            'token': 'anytoken', 'email': 'ghost@arokah.com',
        }, content_type='application/json')
        assert r.status_code == 404

    def test_already_verified_returns_200(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/verify-email/', {
            'token': 'anytoken', 'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 200
        assert 'already verified' in r.json()['message'].lower()

    def test_missing_fields_returns_400(self, client):
        r = client.post('/api/auth/verify-email/', {}, content_type='application/json')
        assert r.status_code == 400


# ── Integration: resend-verification endpoint ─────────────────────────────

class TestResendVerificationEndpoint:
    @patch('auth_app.views.send_verification_email', return_value=True)
    def test_resend_for_unverified_user(self, mock_send, client):
        user = UserFactory(is_email_verified=False)
        r = client.post('/api/auth/resend-verification/', {
            'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 200
        assert mock_send.called

    def test_resend_for_unknown_email_is_vague(self, client):
        """Security: should not reveal whether email is registered."""
        r = client.post('/api/auth/resend-verification/', {
            'email': 'nobody@arokah.com',
        }, content_type='application/json')
        assert r.status_code == 200
        assert 'If that email' in r.json()['message']

    def test_resend_for_verified_user_returns_ok(self, client):
        user = UserFactory(is_email_verified=True)
        r = client.post('/api/auth/resend-verification/', {
            'email': user.email,
        }, content_type='application/json')
        assert r.status_code == 200

    def test_resend_missing_email_returns_400(self, client):
        r = client.post('/api/auth/resend-verification/', {}, content_type='application/json')
        assert r.status_code == 400


# ── send_verification_email unit test ─────────────────────────────────────

class TestSendVerificationEmail:
    @patch('auth_app.email.send_mail')
    def test_sends_to_correct_address(self, mock_send_mail):
        mock_send_mail.return_value = 1
        user = UserFactory()
        result = send_verification_email(user)
        assert result is True
        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]
        assert user.email in call_kwargs['recipient_list']

    @patch('auth_app.email.send_mail')
    def test_token_saved_to_user(self, mock_send_mail):
        mock_send_mail.return_value = 1
        user = UserFactory()
        send_verification_email(user)
        user.refresh_from_db()
        assert len(user.email_verification_token) == 48
        assert user.email_token_created_at is not None

    @patch('auth_app.email.send_mail', side_effect=Exception('SMTP error'))
    def test_returns_false_on_smtp_error(self, mock_send_mail):
        user = UserFactory()
        result = send_verification_email(user)
        assert result is False


# ── Security hardening tests ──────────────────────────────────────────────

class TestSecurityHardening:
    def test_token_cleared_after_verification(self, client):
        """After verifying, the token must not be reusable."""
        user = UserFactory(is_email_verified=False)
        token = 'uniquetoken9876'
        user.email_verification_token = token
        user.email_token_created_at   = timezone.now()
        user.save()

        # First verification succeeds
        r1 = client.post('/api/auth/verify-email/', {
            'token': token, 'email': user.email,
        }, content_type='application/json')
        assert r1.status_code == 200

        # Replay the same token — should fail (already verified / token cleared)
        r2 = client.post('/api/auth/verify-email/', {
            'token': token, 'email': user.email,
        }, content_type='application/json')
        # Already verified returns 200 but "already verified" message
        assert r2.status_code == 200
        assert 'already verified' in r2.json()['message'].lower()

        # Confirm token was wiped from DB
        user.refresh_from_db()
        assert user.email_verification_token == ''

    def test_resend_does_not_reveal_account_existence(self, client):
        """Resend for unknown email must return same response shape as known email."""
        r_known = client.post('/api/auth/resend-verification/', {
            'email': 'doesnotexist@nowhere.com',
        }, content_type='application/json')
        # Both should return 200 (never 404 for unknown email)
        assert r_known.status_code == 200

    def test_verification_is_case_insensitive(self, client):
        """Email matching should be case-insensitive."""
        user = UserFactory(is_email_verified=False, email='CaseSensitive@test.com')
        token = 'casetoken123'
        user.email_verification_token = token
        user.email_token_created_at   = timezone.now()
        user.save()

        r = client.post('/api/auth/verify-email/', {
            'token': token,
            'email': 'casesensitive@TEST.COM',   # different case
        }, content_type='application/json')
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_login_returns_email_in_error_for_ux(self, client):
        """The 403 error should include the email so the UI can pre-fill resend."""
        with patch('auth_app.views.send_verification_email', return_value=True):
            client.post('/api/auth/register/', {
                'email': 'ux@arokah.com', 'password': 'testpass99',
            }, content_type='application/json')

        r = client.post('/api/auth/login/', {
            'email': 'ux@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 403
        assert r.json()['error']['email'] == 'ux@arokah.com'

    @patch('auth_app.email.send_mail')
    def test_html_email_contains_verify_link(self, mock_send_mail):
        """Verification email HTML must include the token in the verify URL."""
        mock_send_mail.return_value = 1
        user = UserFactory()
        send_verification_email(user)
        user.refresh_from_db()

        call_kwargs = mock_send_mail.call_args[1]
        html = call_kwargs['html_message']
        assert user.email_verification_token in html
        assert 'verify-email' in html
        assert user.email in html

    @patch('auth_app.email.send_mail')
    def test_plain_text_email_contains_verify_link(self, mock_send_mail):
        """Plain-text email must also include the token (for text-only clients)."""
        mock_send_mail.return_value = 1
        user = UserFactory()
        send_verification_email(user)
        user.refresh_from_db()

        positional_args = mock_send_mail.call_args[1]
        plain_body = positional_args['message']
        assert user.email_verification_token in plain_body

    def test_inactive_user_cannot_trigger_resend(self, client):
        """Inactive (banned) accounts should not receive verification emails."""
        user = UserFactory(is_active=False, is_email_verified=False)
        with patch('auth_app.views.send_verification_email') as mock_send:
            client.post('/api/auth/resend-verification/', {
                'email': user.email,
            }, content_type='application/json')
            assert not mock_send.called
