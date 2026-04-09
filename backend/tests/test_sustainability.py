import pytest
from .factories import UserFactory
from sustainability.models import SustainabilityLog, UserSustainabilityProfile

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestSustainabilityTracker:
    def test_tracker_auto_created(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/sustainability/tracker/', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['total_points'] == 0
        assert float(data['total_co2_saved_kg']) == 0.0

    def test_tracker_unauthenticated(self, client):
        r = client.get('/api/sustainability/tracker/')
        assert r.status_code == 401


class TestSustainabilityLogs:
    def test_create_log(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/sustainability/logs/', {
            'action': 'wear_again',
            'co2_saved_kg': '0.250',
            'points': 10,
            'notes': 'Wore the navy blazer again',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['action'] == 'wear_again'
        assert r.json()['points'] == 10

    def test_logs_isolated_per_user(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        SustainabilityLog.objects.create(user=user_b, action='wear_again', points=50)
        h = auth_header(client, user_a)
        r = client.get('/api/sustainability/logs/', **h)
        assert r.json()['count'] == 0

    def test_invalid_action_rejected(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/sustainability/logs/', {
            'action': 'buy_fast_fashion',
            'points': 0,
        }, content_type='application/json', **h)
        assert r.status_code == 400
