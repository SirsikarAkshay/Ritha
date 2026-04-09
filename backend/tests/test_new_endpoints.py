"""Tests for push token, outfit history, and location preference features."""
import pytest
from django.utils import timezone
import datetime
from .factories import UserFactory, ClothingItemFactory

pytestmark = pytest.mark.django_db


def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


# ── Push token registration ────────────────────────────────────────────────

class TestPushToken:
    def test_register_token(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.post('/api/auth/push-token/', {
            'token': 'fcm-device-token-abc123',
        }, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'registered'
        user.refresh_from_db()
        assert user.device_push_token == 'fcm-device-token-abc123'
        assert user.push_notifications is True

    def test_unregister_token(self, client):
        user = UserFactory()
        user.device_push_token = 'existing-token'
        user.save()
        h = auth(client, user)
        r = client.post('/api/auth/push-token/', {
            'token': None, 'enabled': False,
        }, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'unregistered'
        user.refresh_from_db()
        assert user.device_push_token == ''
        assert user.push_notifications is False

    def test_update_token(self, client):
        user = UserFactory()
        h = auth(client, user)
        client.post('/api/auth/push-token/', {'token': 'old-token'},
                    content_type='application/json', **h)
        client.post('/api/auth/push-token/', {'token': 'new-token'},
                    content_type='application/json', **h)
        user.refresh_from_db()
        assert user.device_push_token == 'new-token'

    def test_requires_authentication(self, client):
        r = client.post('/api/auth/push-token/', {'token': 'x'},
                        content_type='application/json')
        assert r.status_code == 401


# ── Outfit history endpoint ────────────────────────────────────────────────

class TestOutfitHistory:
    def _make_recommendation(self, user, days_ago, accepted=True):
        from outfits.models import OutfitRecommendation
        return OutfitRecommendation.objects.create(
            user=user,
            date=(timezone.now() - datetime.timedelta(days=days_ago)).date(),
            source='daily',
            accepted=accepted,
            notes=f'Outfit from {days_ago} days ago',
        )

    def test_returns_past_recommendations(self, client):
        user = UserFactory()
        self._make_recommendation(user, 1)
        self._make_recommendation(user, 3)
        self._make_recommendation(user, 5)
        h = auth(client, user)
        r = client.get('/api/outfits/history/', **h)
        assert r.status_code == 200
        assert r.json()['count'] == 3

    def test_days_filter(self, client):
        user = UserFactory()
        self._make_recommendation(user, 2)
        self._make_recommendation(user, 10)   # outside 7-day window
        h = auth(client, user)
        r = client.get('/api/outfits/history/?days=7', **h)
        assert r.json()['count'] == 1

    def test_ordered_newest_first(self, client):
        user = UserFactory()
        self._make_recommendation(user, 5)
        self._make_recommendation(user, 1)
        h = auth(client, user)
        r = client.get('/api/outfits/history/', **h)
        dates = [item['date'] for item in r.json()['results']]
        assert dates == sorted(dates, reverse=True)

    def test_source_filter(self, client):
        from outfits.models import OutfitRecommendation
        user = UserFactory()
        self._make_recommendation(user, 1)   # source='daily'
        OutfitRecommendation.objects.create(
            user=user,
            date=(timezone.now() - datetime.timedelta(days=2)).date(),
            source='trip', accepted=True, notes='Trip outfit',
        )
        h = auth(client, user)
        r = client.get('/api/outfits/history/?source=trip', **h)
        assert r.json()['count'] == 1
        assert r.json()['results'][0]['source'] == 'trip'

    def test_only_own_recommendations(self, client):
        user1 = UserFactory()
        user2 = UserFactory()
        self._make_recommendation(user1, 1)
        self._make_recommendation(user2, 1)
        h = auth(client, user1)
        r = client.get('/api/outfits/history/', **h)
        assert r.json()['count'] == 1

    def test_requires_authentication(self, client):
        r = client.get('/api/outfits/history/')
        assert r.status_code == 401


# ── User location preference ───────────────────────────────────────────────

class TestLocationPreference:
    def test_can_save_location_name(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.patch('/api/auth/me/', {
            'location_name': 'Berlin',
        }, content_type='application/json', **h)
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.location_name == 'Berlin'

    def test_can_save_coordinates(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.patch('/api/auth/me/', {
            'location_lat': 47.3769, 'location_lon': 8.5417,
        }, content_type='application/json', **h)
        assert r.status_code == 200
        user.refresh_from_db()
        assert abs(user.location_lat - 47.3769) < 0.001

    def test_location_returned_in_me_endpoint(self, client):
        user = UserFactory()
        user.location_name = 'Zurich'
        user.save()
        h = auth(client, user)
        r = client.get('/api/auth/me/', **h)
        assert r.json()['location_name'] == 'Zurich'

    def test_daily_look_uses_user_location(self, client):
        """When location_name is set, daily look passes it to weather service."""
        from unittest.mock import patch
        user = UserFactory()
        user.location_name = 'Tokyo'
        user.save()
        ClothingItemFactory(user=user)
        h = auth(client, user)

        captured_location = []

        def mock_get_weather(input_data):
            captured_location.append(input_data.get('location', ''))
            return {'temp_c': 18, 'condition': 'Cloudy', 'precipitation_probability': 10,
                    'wind_kmh': 12, 'is_cold': False, 'is_hot': False, 'is_raining': False,
                    'temp_min_c': 14, 'temp_max_c': 22}

        with patch('agents.services._get_weather', side_effect=mock_get_weather):
            client.post('/api/agents/daily-look/', {}, content_type='application/json', **h)

        assert any('Tokyo' in loc for loc in captured_location), \
            f"Expected Tokyo in weather call, got: {captured_location}"


# ── UserSerializer completeness ────────────────────────────────────────────

class TestUserSerializerFields:
    def test_me_returns_all_expected_fields(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/auth/me/', **h)
        data = r.json()
        expected = [
            'id', 'email', 'first_name', 'last_name', 'timezone',
            'location_name', 'location_lat', 'location_lon',
            'push_notifications',
            'google_calendar_connected', 'apple_calendar_connected', 'outlook_calendar_connected',
            'is_email_verified', 'created_at',
        ]
        for field in expected:
            assert field in data, f"Missing field: {field}"
