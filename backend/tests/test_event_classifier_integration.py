"""Integration test: CalendarEvent.save() auto-classifies event_type."""
import pytest
import datetime
from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAutoClassification:
    def _auth(self, client, user):
        r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                        content_type='application/json')
        return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}

    def test_standup_classified_as_internal(self, client):
        user = UserFactory()
        h = self._auth(client, user)
        r = client.post('/api/itinerary/events/', {
            'title': 'Daily standup',
            'start_time': '2026-03-14T09:00:00Z',
            'end_time':   '2026-03-14T09:15:00Z',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['event_type'] == 'internal_meeting'

    def test_gym_classified_as_workout(self, client):
        user = UserFactory()
        h = self._auth(client, user)
        r = client.post('/api/itinerary/events/', {
            'title': 'Gym at 6am',
            'start_time': '2026-03-14T06:00:00Z',
            'end_time':   '2026-03-14T07:00:00Z',
        }, content_type='application/json', **h)
        assert r.json()['event_type'] == 'workout'
        assert r.json()['formality'] == 'activewear'

    def test_client_lunch_classified_as_external(self, client):
        user = UserFactory()
        h = self._auth(client, user)
        r = client.post('/api/itinerary/events/', {
            'title': 'Lunch with client',
            'start_time': '2026-03-14T12:00:00Z',
            'end_time':   '2026-03-14T13:30:00Z',
        }, content_type='application/json', **h)
        assert r.json()['event_type'] == 'external_meeting'

    def test_explicit_event_type_not_overridden(self, client):
        """If event_type is provided explicitly, classifier should not override it."""
        user = UserFactory()
        h = self._auth(client, user)
        r = client.post('/api/itinerary/events/', {
            'title':      'Team lunch',          # would normally be 'social'
            'event_type': 'internal_meeting',    # explicit override
            'start_time': '2026-03-14T12:00:00Z',
            'end_time':   '2026-03-14T13:00:00Z',
        }, content_type='application/json', **h)
        assert r.json()['event_type'] == 'internal_meeting'
