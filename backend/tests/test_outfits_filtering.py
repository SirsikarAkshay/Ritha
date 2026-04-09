"""Tests for outfit recommendation filtering and serializer privacy."""
import pytest
import datetime
from .factories import UserFactory, ClothingItemFactory, TripFactory
from outfits.models import OutfitRecommendation, OutfitItem

pytestmark = pytest.mark.django_db


def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


def make_rec(user, source='daily', date=None, trip=None):
    return OutfitRecommendation.objects.create(
        user=user,
        date=date or datetime.date.today(),
        source=source,
        trip=trip,
    )


class TestOutfitFiltering:
    def test_filter_by_source(self, client):
        user = UserFactory()
        make_rec(user, source='daily')
        make_rec(user, source='trip')
        h = auth(client, user)
        r = client.get('/api/outfits/recommendations/?source=trip', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert results[0]['source'] == 'trip'

    def test_filter_by_date(self, client):
        user = UserFactory()
        make_rec(user, date=datetime.date(2026, 3, 14))
        make_rec(user, date=datetime.date(2026, 4, 1))
        h = auth(client, user)
        r = client.get('/api/outfits/recommendations/?date=2026-03-14', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert results[0]['date'] == '2026-03-14'

    def test_filter_by_trip_id(self, client):
        user  = UserFactory()
        trip  = TripFactory(user=user)
        make_rec(user, source='trip', trip=trip)
        make_rec(user, source='daily')
        h = auth(client, user)
        r = client.get(f'/api/outfits/recommendations/?trip_id={trip.id}', **h)
        assert r.json()['count'] == 1

    def test_user_field_not_in_response(self, client):
        """user FK must not appear in any outfit response (privacy)."""
        user = UserFactory()
        make_rec(user)
        h = auth(client, user)
        r = client.get('/api/outfits/recommendations/', **h)
        for rec in r.json()['results']:
            assert 'user' not in rec

    def test_daily_endpoint_no_user_field(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user)
        h = auth(client, user)
        client.post('/api/agents/daily-look/',
                    {'weather': {'temp_c': 18, 'is_cold': False, 'is_hot': False,
                                 'is_raining': False, 'precipitation_probability': 5}},
                    content_type='application/json', **h)
        r = client.get('/api/outfits/recommendations/daily/', **h)
        assert r.status_code == 200
        assert 'user' not in r.json()

    def test_outfit_items_nested_in_response(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        rec  = make_rec(user)
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role='main')
        h = auth(client, user)
        r = client.get(f'/api/outfits/recommendations/{rec.id}/', **h)
        assert 'outfit_items' in r.json()
        assert r.json()['outfit_items'][0]['role'] == 'main'


class TestSignalIdempotency:
    def test_accepting_twice_awards_points_once(self):
        """The points_awarded flag prevents double-awarding."""
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        rec  = OutfitRecommendation.objects.create(
            user=user, date=datetime.date.today(), source='daily'
        )
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role='main')

        # First acceptance — should award points
        rec.accepted = True
        rec.save()

        from sustainability.models import SustainabilityLog
        count_after_first = SustainabilityLog.objects.filter(user=user).count()

        # Save again without changing accepted (e.g. weather_snapshot update)
        rec.notes = 'Updated notes'
        rec.save()

        count_after_second = SustainabilityLog.objects.filter(user=user).count()
        assert count_after_first == count_after_second, "Points awarded twice!"

    def test_rejecting_then_accepting_awards_points(self):
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        rec  = OutfitRecommendation.objects.create(
            user=user, date=datetime.date.today(), source='daily'
        )
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role='main')
        # Reject first
        rec.accepted = False
        rec.save()
        from sustainability.models import SustainabilityLog
        assert SustainabilityLog.objects.filter(user=user).count() == 0
        # Then accept
        rec.accepted = True
        rec.save()
        assert SustainabilityLog.objects.filter(user=user).count() == 1
