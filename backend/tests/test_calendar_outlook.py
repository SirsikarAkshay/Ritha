"""Tests for Outlook / Microsoft 365 Calendar integration."""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from .factories import UserFactory

pytestmark = pytest.mark.django_db


def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


def make_outlook_user():
    u = UserFactory()
    u.outlook_calendar_connected = True
    u.outlook_calendar_email     = 'user@outlook.com'
    u.outlook_calendar_token     = json.dumps({
        'access_token': 'fake-ms-token', 'refresh_token': 'fake-ms-refresh',
        'expires_in': 3600, 'token_type': 'Bearer',
    })
    u.save()
    return u


class TestOutlookConnect:
    def test_connect_without_credentials_returns_503(self, client, settings):
        settings.MICROSOFT_CLIENT_ID     = ''
        settings.MICROSOFT_CLIENT_SECRET = ''
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/calendar/outlook/connect/', **h)
        assert r.status_code == 503
        assert r.json()['error']['code'] == 'not_configured'

    @patch('calendar_sync.outlook_calendar.get_authorization_url',
           return_value=('https://login.microsoftonline.com/auth?...', 'state123'))
    def test_connect_returns_auth_url(self, mock_auth, client, settings):
        settings.MICROSOFT_CLIENT_ID     = 'fake-ms-client-id'
        settings.MICROSOFT_CLIENT_SECRET = 'fake-ms-secret'
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/calendar/outlook/connect/', **h)
        assert r.status_code == 200
        assert 'auth_url' in r.json()
        assert 'microsoftonline.com' in r.json()['auth_url']


class TestOutlookCallback:
    def test_callback_denied_redirects(self, client, settings):
        settings.FRONTEND_URL = 'http://localhost:3000'
        r = client.get('/api/calendar/outlook/callback/?error=access_denied')
        assert r.status_code == 302
        assert 'denied' in r['Location']

    @patch('calendar_sync.outlook_calendar.exchange_code')
    @patch('calendar_sync.outlook_calendar.get_outlook_email', return_value='user@outlook.com')
    @patch('calendar_sync.outlook_calendar.sync_events', return_value={'created': 3, 'updated': 0, 'errors': []})
    def test_successful_callback_connects_user(self, mock_sync, mock_email, mock_exchange, client, settings):
        settings.FRONTEND_URL = 'http://localhost:3000'
        mock_exchange.return_value = {
            'access_token': 'at', 'refresh_token': 'rt', 'expires_in': 3600, 'token_type': 'Bearer',
        }
        user = UserFactory()
        r = client.get(f'/api/calendar/outlook/callback/?code=msauthcode&state={user.id}:abc')
        assert r.status_code == 302
        assert 'connected' in r['Location']
        user.refresh_from_db()
        assert user.outlook_calendar_connected is True
        assert user.outlook_calendar_email == 'user@outlook.com'


class TestOutlookSync:
    def test_sync_not_connected_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/calendar/outlook/sync/', **h)
        assert r.status_code == 400

    @patch('calendar_sync.outlook_calendar.sync_events',
           return_value={'created': 4, 'updated': 2, 'errors': []})
    def test_sync_returns_counts(self, mock_sync, client):
        user = make_outlook_user()
        h = auth(client, user)
        r = client.post('/api/calendar/outlook/sync/', **h)
        assert r.status_code == 200
        assert r.json()['created'] == 4
        assert r.json()['updated'] == 2


class TestOutlookDisconnect:
    def test_disconnect_clears_fields(self, client):
        user = make_outlook_user()
        h = auth(client, user)
        r = client.post('/api/calendar/outlook/disconnect/', **h)
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.outlook_calendar_connected is False
        assert user.outlook_calendar_email == ''
        assert user.outlook_calendar_token == ''


class TestOutlookStatusInStatusEndpoint:
    def test_status_includes_outlook(self, client):
        user = make_outlook_user()
        h = auth(client, user)
        r = client.get('/api/calendar/status/', **h)
        assert r.status_code == 200
        data = r.json()
        assert 'outlook' in data
        assert data['outlook']['connected'] is True
        assert data['outlook']['email'] == 'user@outlook.com'


class TestOutlookEventUpsert:
    def test_upserts_graph_event(self):
        from calendar_sync.outlook_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'outlook-event-aaa',
            'subject': 'Board review',
            'bodyPreview': 'Quarterly board meeting',
            'location': {'displayName': 'Conference Room A'},
            'isAllDay': False,
            'isCancelled': False,
            'start': {'dateTime': '2026-04-10T10:00:00', 'timeZone': 'UTC'},
            'end':   {'dateTime': '2026-04-10T11:00:00', 'timeZone': 'UTC'},
        }
        c, u = _upsert_event(user, raw, 'Work')
        assert c == 1
        ev = CalendarEvent.objects.get(user=user, external_id='outlook-event-aaa')
        assert ev.source == 'outlook'
        assert ev.formality in ('formal', 'smart')   # board review → formal/smart

    def test_cancelled_event_deleted(self):
        from calendar_sync.outlook_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'outlook-cancel-bbb',
            'subject': 'Meeting', 'bodyPreview': '', 'location': {'displayName': ''},
            'isAllDay': False, 'isCancelled': False,
            'start': {'dateTime': '2026-04-10T09:00:00', 'timeZone': 'UTC'},
            'end':   {'dateTime': '2026-04-10T10:00:00', 'timeZone': 'UTC'},
        }
        _upsert_event(user, raw, 'Work')
        raw['isCancelled'] = True
        _upsert_event(user, raw, 'Work')
        assert not CalendarEvent.objects.filter(user=user, external_id='outlook-cancel-bbb').exists()

    def test_all_day_event_parsed(self):
        from calendar_sync.outlook_calendar import _upsert_event
        from itinerary.models import CalendarEvent
        user = UserFactory()
        raw = {
            'id': 'outlook-allday-ccc',
            'subject': 'Company Day Off', 'bodyPreview': '', 'location': {'displayName': ''},
            'isAllDay': True, 'isCancelled': False,
            'start': {'date': '2026-04-15'}, 'end': {'date': '2026-04-16'},
        }
        _upsert_event(user, raw, 'Company')
        ev = CalendarEvent.objects.get(user=user, external_id='outlook-allday-ccc')
        assert ev.all_day is True
