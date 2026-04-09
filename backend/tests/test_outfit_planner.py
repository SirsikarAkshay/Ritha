"""Tests for the trip outfit planner agent."""
import pytest
import datetime
from .factories import UserFactory, ClothingItemFactory, TripFactory

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestOutfitPlannerAgent:
    def _wardrobe(self, user):
        ClothingItemFactory(user=user, category='top',      name='White Tee')
        ClothingItemFactory(user=user, category='bottom',   name='Blue Jeans')
        ClothingItemFactory(user=user, category='footwear', name='Sneakers')
        ClothingItemFactory(user=user, category='outerwear',name='Rain Jacket')

    def test_plan_by_dates(self, client):
        user = UserFactory()
        self._wardrobe(user)
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/', {
            'start_date':  '2026-04-01',
            'end_date':    '2026-04-03',
            'destination': 'Barcelona',
        }, content_type='application/json', **h)
        assert r.status_code == 200
        output = r.json()['output']
        assert output['days'] == 3
        assert len(output['day_plans']) == 3
        assert output['start_date'] == '2026-04-01'

    def test_plan_by_trip_id(self, client):
        user = UserFactory()
        self._wardrobe(user)
        trip = TripFactory(user=user, destination='Lisbon',
                           start_date=datetime.date(2026, 5, 1),
                           end_date=datetime.date(2026, 5, 4))
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/',
                        {'trip_id': trip.id},
                        content_type='application/json', **h)
        assert r.status_code == 200
        output = r.json()['output']
        assert output['days'] == 4
        assert output['destination'] == 'Lisbon'

    def test_invalid_trip_id_returns_error(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/',
                        {'trip_id': 99999},
                        content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['output']['status'] == 'error'

    def test_missing_dates_returns_400(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/', {},
                        content_type='application/json', **h)
        # Input serializer now catches this before the service layer
        assert r.status_code == 400
        assert r.json()['error']['code'] == 'validation_error'

    def test_no_wardrobe_returns_warning(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/', {
            'start_date': '2026-04-01', 'end_date': '2026-04-03', 'destination': 'Rome',
        }, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['output']['status'] == 'no_wardrobe'

    def test_packing_list_deduplicates_items(self, client):
        user = UserFactory()
        self._wardrobe(user)
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/', {
            'start_date': '2026-04-01', 'end_date': '2026-04-07',
            'destination': 'Paris',
        }, content_type='application/json', **h)
        output = r.json()['output']
        # packing_list_ids should contain no duplicates
        ids = output['packing_list_ids']
        assert len(ids) == len(set(ids))

    def test_weight_estimate_included(self, client):
        user = UserFactory()
        self._wardrobe(user)
        h = auth_header(client, user)
        r = client.post('/api/agents/outfit-planner/', {
            'start_date': '2026-04-01', 'end_date': '2026-04-03', 'destination': 'Milan',
        }, content_type='application/json', **h)
        assert 'estimated_weight_grams' in r.json()['output']
