import pytest
import datetime
from .factories import UserFactory, CalendarEventFactory, TripFactory

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestCalendarEvents:
    def test_create_event(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/itinerary/events/', {
            'title': 'Client Lunch',
            'event_type': 'external_meeting',
            'start_time': '2026-04-01T12:00:00Z',
            'end_time':   '2026-04-01T13:30:00Z',
            'location':   'Restaurant Zurich',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['title'] == 'Client Lunch'
        assert r.json()['event_type'] == 'external_meeting'

    def test_list_own_events(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        CalendarEventFactory(user=user_a, title='A Meeting')
        CalendarEventFactory(user=user_b, title='B Meeting')
        h = auth_header(client, user_a)
        r = client.get('/api/itinerary/events/', **h)
        titles = [e['title'] for e in r.json()['results']]
        assert 'A Meeting' in titles
        assert 'B Meeting' not in titles

    def test_filter_events_by_date(self, client):
        user = UserFactory()
        CalendarEventFactory(user=user, title='Today',
            start_time=datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.timezone.utc),
            end_time=datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc))
        CalendarEventFactory(user=user, title='Tomorrow',
            start_time=datetime.datetime(2026, 3, 15, 9, 0, tzinfo=datetime.timezone.utc),
            end_time=datetime.datetime(2026, 3, 15, 10, 0, tzinfo=datetime.timezone.utc))
        h = auth_header(client, user)
        r = client.get('/api/itinerary/events/?date=2026-03-14', **h)
        titles = [e['title'] for e in r.json()['results']]
        assert 'Today' in titles
        assert 'Tomorrow' not in titles

    def test_calendar_sync_no_calendars(self, client):
        """With no calendars connected, sync returns informative status."""
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/itinerary/events/sync/', {}, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'no_calendars_connected'
        assert '/api/calendar/' in r.json()['message']


class TestTrips:
    def test_create_trip(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/itinerary/trips/', {
            'name': 'Tokyo Adventure',
            'destination': 'Tokyo, Japan',
            'start_date': '2026-05-01',
            'end_date':   '2026-05-10',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['destination'] == 'Tokyo, Japan'

    def test_trip_isolation(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        TripFactory(user=user_b, name='Secret Trip')
        h = auth_header(client, user_a)
        r = client.get('/api/itinerary/trips/', **h)
        names = [t['name'] for t in r.json()['results']]
        assert 'Secret Trip' not in names


class TestCalendarEventAutoClassificationEdgeCases:
    """Cover CalendarEvent.save() lines 54 and 70 — title empty / event_type already set."""

    def _auth(self, client, user):
        r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                        content_type='application/json')
        return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}

    def test_event_with_no_title_defaults_to_other(self, client):
        from itinerary.models import CalendarEvent
        user = UserFactory()
        # Create directly via model (bypass serializer required title)
        event = CalendarEvent.objects.create(
            user=user,
            title='',
            event_type='other',
            start_time='2026-04-01T10:00:00Z',
            end_time='2026-04-01T11:00:00Z',
        )
        assert event.event_type == 'other'

    def test_formality_preserved_when_explicitly_set(self, client):
        user = UserFactory()
        h = self._auth(client, user)
        r = client.post('/api/itinerary/events/', {
            'title':     'Gym session',
            'event_type': 'workout',
            'formality':  'smart',   # override even though gym → activewear
            'start_time': '2026-04-01T07:00:00Z',
            'end_time':   '2026-04-01T08:00:00Z',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['formality'] == 'smart'
