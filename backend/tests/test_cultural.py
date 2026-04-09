import pytest
from .factories import UserFactory, CulturalRuleFactory, LocalEventFactory
from cultural.models import CulturalRule

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestCulturalRules:
    def test_list_rules(self, client):
        CulturalRuleFactory(country='Turkey', city='Istanbul')
        CulturalRuleFactory(country='Italy', city='Rome', rule_type='cover_shoulders',
                            description='Shoulders covered in Vatican')
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/cultural/rules/', **h)
        assert r.status_code == 200
        assert r.json()['count'] == 2

    def test_filter_by_country(self, client):
        CulturalRuleFactory(country='Turkey')
        CulturalRuleFactory(country='Italy')
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/cultural/rules/?country=Turkey', **h)
        results = r.json()['results']
        assert all(rule['country'] == 'Turkey' for rule in results)

    def test_filter_by_city(self, client):
        CulturalRuleFactory(country='Italy', city='Rome')
        CulturalRuleFactory(country='Italy', city='Venice')
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/cultural/rules/?city=Rome', **h)
        results = r.json()['results']
        assert all(r['city'] == 'Rome' for r in results)

    def test_rules_read_only(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/cultural/rules/', {
            'country': 'France', 'rule_type': 'general', 'description': 'test',
        }, content_type='application/json', **h)
        assert r.status_code == 405  # Method Not Allowed

    def test_unauthenticated_blocked(self, client):
        r = client.get('/api/cultural/rules/')
        assert r.status_code == 401


class TestLocalEvents:
    def test_filter_by_month(self, client):
        LocalEventFactory(country='India', name='Holi', start_month=3, end_month=3)
        LocalEventFactory(country='India', name='Diwali', start_month=10, end_month=11)
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/cultural/events/?country=India&month=3', **h)
        names = [e['name'] for e in r.json()['results']]
        assert 'Holi' in names
        assert 'Diwali' not in names
