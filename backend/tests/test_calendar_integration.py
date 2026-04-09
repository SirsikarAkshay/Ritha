"""
Tests for Google and Apple Calendar integrations.
All external API calls (Google OAuth, CalDAV) are mocked.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.utils import timezone
from .factories import UserFactory

pytestmark = pytest.mark.django_db


# ── Helpers ────────────────────────────────────────────────────────────────

def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


def make_google_user():
    u = UserFactory()
    u.google_calendar_connected = True
    u.google_calendar_email     = 'test@gmail.com'
    u.google_calendar_token     = json.dumps({
        'token': 'fake-access-token', 'refresh_token': 'fake-refresh',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'fake-client-id', 'client_secret': 'fake-secret',
        'scopes': ['https://www.googleapis.com/auth/calendar.readonly'],
        'expiry': None,
    })
    u.save()
    return u


def make_apple_user():
    from calendar_sync.apple_calendar import save_credentials
    u = UserFactory()
    save_credentials(u, 'test@icloud.com', 'abcd-efgh-ijkl-mnop')
    return u


# ── Calendar status ────────────────────────────────────────────────────────

class TestCalendarStatus:
    def test_status_unauthenticated(self, client):
        r = client.get('/api/calendar/status/')
        assert r.status_code == 401

    def test_status_no_connections(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/calendar/status/', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['google']['connected'] is False
        assert data['apple']['connected'] is False

    def test_status_after_google_connect(self, client):
        user = make_google_user()
        h = auth(client, user)
        r = client.get('/api/calendar/status/', **h)
        assert r.json()['google']['connected'] is True
        assert r.json()['google']['email'] == 'test@gmail.com'

    def test_status_after_apple_connect(self, client):
        user = make_apple_user()
        h = auth(client, user)
        r = client.get('/api/calendar/status/', **h)
        assert r.json()['apple']['connected'] is True
        assert r.json()['apple']['username'] == 'test@icloud.com'


# ── Google Calendar ────────────────────────────────────────────────────────

class TestGoogleConnect:
    def test_connect_without_credentials_returns_503(self, client, settings):
        settings.GOOGLE_CLIENT_ID     = ''
        settings.GOOGLE_CLIENT_SECRET = ''
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/calendar/google/connect/', **h)
        assert r.status_code == 503
        assert r.json()['error']['code'] == 'not_configured'

    @patch('calendar_sync.google_calendar.get_authorization_url',
           return_value=('https://accounts.google.com/auth?...', 'state123'))
    def test_connect_returns_auth_url(self, mock_auth, client, settings):
        settings.GOOGLE_CLIENT_ID     = 'fake-client-id'
        settings.GOOGLE_CLIENT_SECRET = 'fake-secret'
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/calendar/google/connect/', **h)
        assert r.status_code == 200
        assert 'auth_url' in r.json()
        assert 'accounts.google.com' in r.json()['auth_url']


class TestGoogleCallback:
    def test_callback_without_code_redirects_to_error(self, client):
        r = client.get('/api/calendar/google/callback/?error=access_denied')
        assert r.status_code == 302
        assert 'denied' in r['Location']

    @patch('calendar_sync.google_calendar.exchange_code')
    @patch('calendar_sync.google_calendar.get_google_email', return_value='user@gmail.com')
    @patch('calendar_sync.google_calendar.sync_events', return_value={'created': 5, 'updated': 0, 'errors': []})
    def test_successful_callback_connects_user(self, mock_sync, mock_email, mock_exchange, client, settings):
        settings.FRONTEND_URL = 'http://localhost:3000'
        mock_exchange.return_value = {
            'token': 'access', 'refresh_token': 'refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'cid', 'client_secret': 'csec', 'scopes': [], 'expiry': None,
        }
        user = UserFactory()
        state = f"{user.id}:abc123"
        r = client.get(f'/api/calendar/google/callback/?code=authcode&state={state}')
        assert r.status_code == 302
        assert 'connected' in r['Location']
        user.refresh_from_db()
        assert user.google_calendar_connected is True
        assert user.google_calendar_email == 'user@gmail.com'

    def test_callback_invalid_state_redirects_to_error(self, client, settings):
        settings.FRONTEND_URL = 'http://localhost:3000'
        r = client.get('/api/calendar/google/callback/?code=x&state=badstate')
        assert r.status_code == 302
        assert 'invalid_state' in r['Location']


class TestGoogleSync:
    def test_sync_without_connection_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/google/sync/', **h)
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'not_connected'

    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'created': 3, 'updated': 1, 'deleted': 0, 'errors': []})
    def test_sync_returns_counts(self, mock_sync, client):
        user = make_google_user()
        h = auth(client, user)
        r = client.post('/api/calendar/google/sync/', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['status']  == 'synced'
        assert data['created'] == 3
        assert data['updated'] == 1

    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'error': 'Token expired'})
    def test_sync_error_returns_500(self, mock_sync, client):
        user = make_google_user()
        h = auth(client, user)
        r = client.post('/api/calendar/google/sync/', **h)
        assert r.status_code == 500


class TestGoogleDisconnect:
    @patch('calendar_sync.google_calendar.revoke_access', return_value=True)
    def test_disconnect_clears_connection(self, mock_revoke, client):
        user = make_google_user()
        h = auth(client, user)
        r = client.post('/api/calendar/google/disconnect/', **h)
        assert r.status_code == 200
        assert mock_revoke.called


# ── Apple Calendar ─────────────────────────────────────────────────────────

class TestAppleConnect:
    def test_missing_fields_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/connect/', {}, content_type='application/json', **h)
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'missing_fields'

    @patch('calendar_sync.apple_calendar.test_connection',
           return_value=(True, 'Connected — 3 calendars found.'))
    def test_valid_credentials_connects(self, mock_test, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/connect/', {
            'username': 'test@icloud.com',
            'password': 'abcd-efgh-ijkl-mnop',
        }, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'connected'
        user.refresh_from_db()
        assert user.apple_calendar_connected is True
        assert user.apple_calendar_username == 'test@icloud.com'

    @patch('calendar_sync.apple_calendar.test_connection',
           return_value=(False, 'Authentication failed.'))
    def test_invalid_credentials_rejected(self, mock_test, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/connect/', {
            'username': 'test@icloud.com',
            'password': 'wrongpassword',
        }, content_type='application/json', **h)
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'connection_failed'


class TestAppleSync:
    def test_sync_without_connection_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/sync/', **h)
        assert r.status_code == 400

    @patch('calendar_sync.apple_calendar.sync_events',
           return_value={'created': 8, 'updated': 2, 'errors': []})
    def test_sync_returns_counts(self, mock_sync, client):
        user = make_apple_user()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/sync/', **h)
        assert r.status_code == 200
        assert r.json()['created'] == 8


class TestAppleDisconnect:
    def test_disconnect_clears_credentials(self, client):
        user = make_apple_user()
        h = auth(client, user)
        r = client.post('/api/calendar/apple/disconnect/', **h)
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.apple_calendar_connected is False
        assert user.apple_calendar_username == ''
        assert user.apple_calendar_password == ''


# ── Encryption ─────────────────────────────────────────────────────────────

class TestPasswordEncryption:
    def test_password_encrypted_at_rest(self):
        from calendar_sync.apple_calendar import save_credentials, _decrypt_password
        user = UserFactory()
        raw_password = 'abcd-efgh-ijkl-mnop'
        save_credentials(user, 'me@icloud.com', raw_password)
        user.refresh_from_db()
        # Stored value is NOT the plaintext
        assert user.apple_calendar_password != raw_password
        # But decrypts correctly
        assert _decrypt_password(user.apple_calendar_password) == raw_password

    def test_credentials_retrievable(self):
        from calendar_sync.apple_calendar import save_credentials, get_credentials
        user = UserFactory()
        save_credentials(user, 'me@icloud.com', 'super-secret-pw')
        username, password = get_credentials(user)
        assert username == 'me@icloud.com'
        assert password == 'super-secret-pw'


# ── Event upsert ───────────────────────────────────────────────────────────

class TestGoogleEventUpsert:
    def test_google_event_creates_calendar_event(self):
        from calendar_sync.google_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'google_event_123',
            'summary': 'Team standup',
            'description': '',
            'location': 'Zoom',
            'status': 'confirmed',
            'start': {'dateTime': '2026-04-01T09:00:00+00:00'},
            'end':   {'dateTime': '2026-04-01T09:30:00+00:00'},
            'htmlLink': 'https://calendar.google.com/...',
            'attendees': [],
        }
        c, u = _upsert_event(user, raw, 'primary')
        assert c == 1
        assert CalendarEvent.objects.filter(user=user, external_id='google_event_123').exists()
        ev = CalendarEvent.objects.get(user=user, external_id='google_event_123')
        assert ev.source == 'google'
        assert ev.event_type == 'internal_meeting'   # classifier picks this up

    def test_google_event_upserts_on_second_call(self):
        from calendar_sync.google_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'upsert_test_456',
            'summary': 'Client call',
            'description': '',
            'location': '',
            'status': 'confirmed',
            'start': {'dateTime': '2026-04-01T14:00:00+00:00'},
            'end':   {'dateTime': '2026-04-01T15:00:00+00:00'},
            'attendees': [],
        }
        c1, u1 = _upsert_event(user, raw, 'primary')
        # Second call with updated title
        raw['summary'] = 'Client call (updated)'
        c2, u2 = _upsert_event(user, raw, 'primary')
        assert c1 == 1 and c2 == 0
        assert u1 == 0 and u2 == 1
        assert CalendarEvent.objects.filter(user=user, external_id='upsert_test_456').count() == 1

    def test_cancelled_google_event_deleted(self):
        from calendar_sync.google_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'cancel_test_789', 'summary': 'Meeting', 'description': '',
            'location': '', 'status': 'confirmed',
            'start': {'dateTime': '2026-04-01T10:00:00+00:00'},
            'end':   {'dateTime': '2026-04-01T11:00:00+00:00'},
            'attendees': [],
        }
        _upsert_event(user, raw, 'primary')
        assert CalendarEvent.objects.filter(user=user, external_id='cancel_test_789').exists()
        raw['status'] = 'cancelled'
        _upsert_event(user, raw, 'primary')
        assert not CalendarEvent.objects.filter(user=user, external_id='cancel_test_789').exists()

    def test_all_day_event_parsed(self):
        from calendar_sync.google_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'allday_101', 'summary': 'Public holiday',
            'description': '', 'location': '', 'status': 'confirmed',
            'start': {'date': '2026-04-01'},
            'end':   {'date': '2026-04-02'},
            'attendees': [],
        }
        _upsert_event(user, raw, 'primary')
        ev = CalendarEvent.objects.get(user=user, external_id='allday_101')
        assert ev.all_day is True


# ── Management command ─────────────────────────────────────────────────────

class TestSyncCalendarsCommand:
    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'created': 5, 'updated': 1, 'errors': []})
    def test_command_syncs_google_users(self, mock_sync):
        from io import StringIO
        from django.core.management import call_command
        user = make_google_user()
        out = StringIO()
        call_command('sync_calendars', provider='google', verbosity=2, stdout=out)
        assert mock_sync.called

    def test_command_skips_unconnected_users(self):
        from io import StringIO
        from django.core.management import call_command
        UserFactory()   # no calendar connected
        with patch('calendar_sync.google_calendar.sync_events') as mock_g, \
             patch('calendar_sync.apple_calendar.sync_events')  as mock_a:
            out = StringIO()
            call_command('sync_calendars', verbosity=0, stdout=out)
            assert not mock_g.called
            assert not mock_a.called

    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'created': 0, 'updated': 0, 'errors': []})
    def test_dry_run_does_not_call_sync(self, mock_sync):
        from io import StringIO
        from django.core.management import call_command
        make_google_user()
        out = StringIO()
        call_command('sync_calendars', dry_run=True, verbosity=0, stdout=out)
        assert not mock_sync.called


# ── Itinerary sync with connected calendars (mocked) ──────────────────────

class TestItinerarySyncWithCalendars:
    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'created': 5, 'updated': 1, 'errors': []})
    def test_sync_routes_to_google(self, mock_sync, client):
        from tests.factories import UserFactory
        user = UserFactory()
        user.google_calendar_connected = True
        user.google_calendar_token     = '{"token":"t","refresh_token":"r","token_uri":"u","client_id":"c","client_secret":"s","scopes":[],"expiry":null}'
        user.save()
        h = auth(client, user)
        r = client.post('/api/itinerary/events/sync/', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'synced'
        assert data['created'] == 5
        assert 'google' in data['providers']

    @patch('calendar_sync.apple_calendar.sync_events',
           return_value={'created': 3, 'updated': 0, 'errors': []})
    def test_sync_routes_to_apple(self, mock_sync, client):
        from calendar_sync.apple_calendar import save_credentials
        user = UserFactory()
        save_credentials(user, 'me@icloud.com', 'test-pass')
        h = auth(client, user)
        r = client.post('/api/itinerary/events/sync/', **h)
        assert r.status_code == 200
        assert r.json()['providers']['apple']['created'] == 3

    def test_sync_no_connections_returns_informative_message(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/itinerary/events/sync/', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'no_calendars_connected'


# ── Google webhook endpoint ───────────────────────────────────────────────

class TestGoogleWebhook:
    def test_sync_handshake_returns_200(self, client):
        """Google sends a sync event on channel registration — must return 200."""
        r = client.post(
            '/api/calendar/google/webhook/',
            content_type='application/json',
            HTTP_X_GOOG_CHANNEL_ID='channel-abc',
            HTTP_X_GOOG_RESOURCE_STATE='sync',
        )
        assert r.status_code == 200

    def test_unknown_state_returns_200(self, client):
        """Unknown resource states should be silently acknowledged."""
        r = client.post(
            '/api/calendar/google/webhook/',
            content_type='application/json',
            HTTP_X_GOOG_RESOURCE_STATE='unknown_state',
        )
        assert r.status_code == 200

    @patch('calendar_sync.google_calendar.sync_events',
           return_value={'created': 2, 'updated': 0, 'errors': []})
    def test_exists_event_triggers_sync(self, mock_sync, client):
        """resource_state=exists with a valid channel token should trigger sync."""
        user = make_google_user()
        r = client.post(
            '/api/calendar/google/webhook/',
            content_type='application/json',
            HTTP_X_GOOG_CHANNEL_ID='channel-xyz',
            HTTP_X_GOOG_RESOURCE_STATE='exists',
            HTTP_X_GOOG_CHANNEL_TOKEN=str(user.id),
        )
        assert r.status_code == 200
        assert mock_sync.called

    def test_webhook_no_auth_required(self, client):
        """Google webhooks are unauthenticated — no JWT needed."""
        r = client.post(
            '/api/calendar/google/webhook/',
            content_type='application/json',
            HTTP_X_GOOG_RESOURCE_STATE='sync',
        )
        assert r.status_code == 200   # not 401


# ── Token encryption integration ──────────────────────────────────────────

class TestTokenEncryptionInFlow:
    @patch('calendar_sync.google_calendar.exchange_code')
    @patch('calendar_sync.google_calendar.get_google_email', return_value='enc@gmail.com')
    @patch('calendar_sync.google_calendar.sync_events', return_value={'created': 0, 'updated': 0, 'errors': []})
    def test_google_token_stored_encrypted(self, mock_sync, mock_email, mock_exchange, client, settings):
        """After OAuth callback, the stored token must not be plain JSON."""
        import json
        settings.FRONTEND_URL = 'http://localhost:3000'
        mock_exchange.return_value = {
            'token': 'access', 'refresh_token': 'refresh',
            'token_uri': 'u', 'client_id': 'c', 'client_secret': 's',
            'scopes': [], 'expiry': None,
        }
        user = UserFactory()
        client.get(f'/api/calendar/google/callback/?code=code&state={user.id}:abc')
        user.refresh_from_db()
        # Token stored — but NOT as plain JSON
        assert user.google_calendar_token != ''
        try:
            parsed = json.loads(user.google_calendar_token)
            # If JSON parsed, it should not have the original token value
            assert parsed.get('token') != 'access', "Token was stored as plain JSON — encryption failed"
        except json.JSONDecodeError:
            pass  # Good — it's encrypted binary data, not valid JSON
