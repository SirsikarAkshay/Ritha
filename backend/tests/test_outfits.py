import pytest
import datetime
from .factories import UserFactory, ClothingItemFactory, CalendarEventFactory
from outfits.models import OutfitRecommendation, OutfitItem

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestDailyRecommendationEndpoint:
    def test_no_recommendation_returns_404(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/outfits/recommendations/daily/', **h)
        assert r.status_code == 404

    def test_recommendation_returned_after_agent_run(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='White Shirt', category='top', formality='smart')
        ClothingItemFactory(user=user, name='Dark Chinos', category='bottom', formality='smart')
        h = auth_header(client, user)

        # Generate via agent
        client.post('/api/agents/daily-look/',
                    {'weather': {'temp_c': 17, 'is_cold': False, 'is_hot': False,
                                 'is_raining': False, 'precipitation_probability': 10}},
                    content_type='application/json', **h)

        r = client.get('/api/outfits/recommendations/daily/', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['source'] == 'daily'
        assert data['date'] == datetime.date.today().isoformat()

    def test_recommendation_idempotent(self, client):
        """Running the agent twice on the same day updates, not duplicates."""
        user = UserFactory()
        ClothingItemFactory(user=user, category='top')
        h = auth_header(client, user)
        weather_payload = {'weather': {'temp_c': 18, 'is_cold': False, 'is_hot': False,
                                       'is_raining': False, 'precipitation_probability': 5}}
        client.post('/api/agents/daily-look/', weather_payload,
                    content_type='application/json', **h)
        client.post('/api/agents/daily-look/', weather_payload,
                    content_type='application/json', **h)
        today = datetime.date.today()
        count = OutfitRecommendation.objects.filter(user=user, date=today, source='daily').count()
        assert count == 1

    def test_daily_endpoint_invalid_date(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.get('/api/outfits/recommendations/daily/?date=not-a-date', **h)
        assert r.status_code == 400


class TestOutfitFeedback:
    def _make_recommendation(self, user):
        return OutfitRecommendation.objects.create(
            user=user,
            date=datetime.date.today(),
            source='daily',
        )

    def test_accept_recommendation(self, client):
        user = UserFactory()
        rec  = self._make_recommendation(user)
        h = auth_header(client, user)
        r = client.patch(f'/api/outfits/recommendations/{rec.id}/feedback/',
                         {'accepted': True}, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['accepted'] is True
        rec.refresh_from_db()
        assert rec.accepted is True

    def test_reject_recommendation(self, client):
        user = UserFactory()
        rec  = self._make_recommendation(user)
        h = auth_header(client, user)
        r = client.patch(f'/api/outfits/recommendations/{rec.id}/feedback/',
                         {'accepted': False}, content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['accepted'] is False

    def test_feedback_missing_field(self, client):
        user = UserFactory()
        rec  = self._make_recommendation(user)
        h = auth_header(client, user)
        r = client.patch(f'/api/outfits/recommendations/{rec.id}/feedback/',
                         {}, content_type='application/json', **h)
        assert r.status_code == 400

    def test_cannot_give_feedback_on_other_users_outfit(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        rec = self._make_recommendation(user_b)
        h = auth_header(client, user_a)
        r = client.patch(f'/api/outfits/recommendations/{rec.id}/feedback/',
                         {'accepted': True}, content_type='application/json', **h)
        assert r.status_code == 404


class TestOutfitItems:
    def test_agent_attaches_wardrobe_items(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user, category='top')
        h = auth_header(client, user)
        client.post('/api/agents/daily-look/',
                    {'weather': {'temp_c': 18, 'is_cold': False, 'is_hot': False,
                                 'is_raining': False, 'precipitation_probability': 0}},
                    content_type='application/json', **h)
        today = datetime.date.today()
        rec = OutfitRecommendation.objects.get(user=user, date=today)
        assert OutfitItem.objects.filter(outfit=rec).count() >= 1
