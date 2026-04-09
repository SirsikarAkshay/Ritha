"""Tests for management commands."""
import pytest
import json
from io import StringIO
from django.core.management import call_command
from .factories import UserFactory, ClothingItemFactory

pytestmark = pytest.mark.django_db


class TestExportUserData:
    def test_exports_json(self, tmp_path):
        user = UserFactory(email='export@arokah.com', first_name='Test')
        ClothingItemFactory(user=user, name='Blue Jacket')
        output_path = str(tmp_path / 'export.json')
        call_command('export_user_data', email='export@arokah.com', output=output_path)
        with open(output_path) as f:
            data = json.load(f)
        assert data['user']['email'] == 'export@arokah.com'
        assert data['user']['first_name'] == 'Test'
        assert len(data['wardrobe']) == 1
        assert data['wardrobe'][0]['name'] == 'Blue Jacket'

    def test_exports_all_sections(self, tmp_path):
        user = UserFactory(email='full@arokah.com')
        output_path = str(tmp_path / 'full.json')
        call_command('export_user_data', email='full@arokah.com', output=output_path)
        with open(output_path) as f:
            data = json.load(f)
        for key in ['user', 'wardrobe', 'calendar_events', 'trips',
                    'outfit_recommendations', 'sustainability_logs', 'agent_jobs']:
            assert key in data, f'Missing key: {key}'

    def test_unknown_email_raises(self):
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            call_command('export_user_data', email='nobody@arokah.com', output='/tmp/x.json')


class TestGenerateDailyLooks:
    def test_dry_run_no_records_created(self):
        from outfits.models import OutfitRecommendation
        user = UserFactory()
        ClothingItemFactory(user=user)
        before = OutfitRecommendation.objects.count()
        out = StringIO()
        call_command('generate_daily_looks', dry_run=True, stdout=out)
        after = OutfitRecommendation.objects.count()
        assert before == after
        assert 'dry run' in out.getvalue()

    def test_generates_for_user_with_wardrobe(self):
        from outfits.models import OutfitRecommendation
        user = UserFactory()
        ClothingItemFactory(user=user)
        call_command('generate_daily_looks', verbosity=0)
        assert OutfitRecommendation.objects.filter(user=user).exists()

    def test_skips_user_without_wardrobe(self):
        from outfits.models import OutfitRecommendation
        user = UserFactory()  # no wardrobe items
        call_command('generate_daily_looks', verbosity=0)
        assert not OutfitRecommendation.objects.filter(user=user).exists()

    def test_limit_by_user_email(self):
        from outfits.models import OutfitRecommendation
        user_a = UserFactory()
        user_b = UserFactory()
        ClothingItemFactory(user=user_a)
        ClothingItemFactory(user=user_b)
        call_command('generate_daily_looks', user=user_a.email, verbosity=0)
        assert     OutfitRecommendation.objects.filter(user=user_a).exists()
        assert not OutfitRecommendation.objects.filter(user=user_b).exists()


class TestSeedCulturalData:
    def test_seeds_rules_and_events(self):
        from cultural.models import CulturalRule, LocalEvent
        CulturalRule.objects.all().delete()
        LocalEvent.objects.all().delete()
        call_command('seed_cultural_data', verbosity=0)
        assert CulturalRule.objects.count() > 0
        assert LocalEvent.objects.count() > 0

    def test_idempotent_no_duplicates(self):
        from cultural.models import CulturalRule
        call_command('seed_cultural_data', verbosity=0)
        count1 = CulturalRule.objects.count()
        call_command('seed_cultural_data', verbosity=0)
        count2 = CulturalRule.objects.count()
        assert count1 == count2

    def test_flush_option_clears_data(self):
        from cultural.models import CulturalRule
        call_command('seed_cultural_data', verbosity=0)
        assert CulturalRule.objects.count() > 0
        call_command('seed_cultural_data', flush=True, verbosity=0)
        assert CulturalRule.objects.count() > 0  # re-seeded after flush


class TestGenerateDailyLooksDateFlag:
    def test_generates_for_specific_date(self):
        import datetime
        from outfits.models import OutfitRecommendation
        user = UserFactory()
        ClothingItemFactory(user=user)
        target = '2026-04-15'
        call_command('generate_daily_looks', date=target, verbosity=0)
        assert OutfitRecommendation.objects.filter(
            user=user, date=datetime.date(2026, 4, 15)
        ).exists()

    def test_invalid_date_does_not_crash(self):
        out = StringIO()
        err = StringIO()
        # Should print error and return gracefully
        call_command('generate_daily_looks', date='not-a-date',
                     stdout=out, stderr=err, verbosity=0)
        assert 'Invalid' in err.getvalue()


class TestExportUserDataStdout:
    def test_exports_to_stdout_when_no_output_flag(self):
        """When --output not given, data goes to stdout as JSON."""
        user = UserFactory(email='stdout@arokah.com')
        out = StringIO()
        call_command('export_user_data', email='stdout@arokah.com', stdout=out)
        data = json.loads(out.getvalue())
        assert data['user']['email'] == 'stdout@arokah.com'


class TestGenerateDailyLooksVerbosity:
    def test_verbosity_2_shows_per_user_output(self):
        user = UserFactory()
        ClothingItemFactory(user=user)
        out = StringIO()
        call_command('generate_daily_looks', verbosity=2, stdout=out)
        # Should include per-user output line
        assert user.email in out.getvalue() or 'Generated' in out.getvalue()

    def test_skipped_user_counted(self):
        UserFactory()  # no wardrobe
        out = StringIO()
        call_command('generate_daily_looks', verbosity=0, stdout=out)
        assert 'Skipped' in out.getvalue()


class TestGenerateDailyLooksNotificationFailure:
    def test_notification_failure_doesnt_abort_command(self, monkeypatch):
        """A broken notification should not prevent the daily look from being saved."""
        from outfits import notifications
        from outfits.models import OutfitRecommendation

        user = UserFactory()
        ClothingItemFactory(user=user)

        # Make notifications always raise
        monkeypatch.setattr(
            notifications, 'send_daily_look_notification',
            lambda u, r: (_ for _ in ()).throw(Exception("FCM down"))
        )

        out = StringIO()
        call_command('generate_daily_looks', verbosity=0, stdout=out)

        # The recommendation must still have been created despite notification failure
        assert OutfitRecommendation.objects.filter(user=user).exists()


class TestGenerateDailyLooksFailedAgent:
    def test_agent_exception_counted_as_failed(self, monkeypatch):
        from agents import services

        user = UserFactory()
        ClothingItemFactory(user=user)

        monkeypatch.setattr(
            services, 'run_daily_look',
            lambda u, d: (_ for _ in ()).throw(RuntimeError("service down"))
        )

        out = StringIO()
        call_command('generate_daily_looks', verbosity=0, stdout=out)
        assert 'Failed: 1' in out.getvalue()
