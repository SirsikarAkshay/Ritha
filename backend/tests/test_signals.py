"""Tests for Django signals: sustainability profile auto-creation and outfit feedback loop."""
import pytest
import datetime
from .factories import UserFactory, ClothingItemFactory
from sustainability.models import UserSustainabilityProfile, SustainabilityLog
from outfits.models import OutfitRecommendation, OutfitItem

pytestmark = pytest.mark.django_db


class TestSustainabilityProfileSignal:
    def test_profile_created_on_user_register(self, client):
        """Registering a user automatically creates a sustainability profile."""
        client.post('/api/auth/register/', {
            'email': 'signal@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(email='signal@arokah.com')
        assert UserSustainabilityProfile.objects.filter(user=user).exists()

    def test_profile_not_duplicated(self):
        """Creating profile twice via get_or_create stays idempotent."""
        user = UserFactory()
        p1, _ = UserSustainabilityProfile.objects.get_or_create(user=user)
        p2, _ = UserSustainabilityProfile.objects.get_or_create(user=user)
        assert p1.id == p2.id


class TestOutfitFeedbackSignal:
    def _setup(self):
        user = UserFactory()
        item = ClothingItemFactory(user=user, name='Test Shirt', times_worn=0)
        rec  = OutfitRecommendation.objects.create(
            user=user, date=datetime.date.today(), source='daily'
        )
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role='main')
        return user, item, rec

    def test_accepting_outfit_increments_times_worn(self):
        user, item, rec = self._setup()
        rec.accepted = True
        rec.save()
        item.refresh_from_db()
        assert item.times_worn == 1

    def test_accepting_outfit_creates_sustainability_log(self):
        user, item, rec = self._setup()
        rec.accepted = True
        rec.save()
        logs = SustainabilityLog.objects.filter(user=user, action='wear_again')
        assert logs.count() == 1
        assert logs.first().points == 10

    def test_accepting_updates_profile_totals(self):
        user, item, rec = self._setup()
        rec.accepted = True
        rec.save()
        profile = UserSustainabilityProfile.objects.get(user=user)
        assert profile.total_points == 10
        assert float(profile.total_co2_saved_kg) > 0

    def test_rejecting_outfit_does_not_increment_worn(self):
        user, item, rec = self._setup()
        rec.accepted = False
        rec.save()
        item.refresh_from_db()
        assert item.times_worn == 0

    def test_sets_last_worn_date(self):
        user, item, rec = self._setup()
        rec.accepted = True
        rec.save()
        item.refresh_from_db()
        assert item.last_worn == datetime.date.today()
