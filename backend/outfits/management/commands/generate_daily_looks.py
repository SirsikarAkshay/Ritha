"""
Batch generate daily outfit recommendations for all active users.
Designed to be run as a daily cron job / scheduled task.

Usage:
  python manage.py generate_daily_looks
  python manage.py generate_daily_looks --date 2026-04-01
  python manage.py generate_daily_looks --user user@example.com
  python manage.py generate_daily_looks --dry-run
"""
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Batch-generate daily outfit recommendations for all active users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date', default=None,
            help='Target date YYYY-MM-DD (defaults to today)'
        )
        parser.add_argument(
            '--user', default=None,
            help='Limit to a single user email'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would happen without creating records'
        )

    def handle(self, *args, **options):
        from agents.services import run_daily_look
        from wardrobe.models import ClothingItem

        date_str = options['date'] or datetime.date.today().isoformat()
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            self.stderr.write(f'Invalid date: {date_str}')
            return

        users = User.objects.filter(is_active=True)
        if options['user']:
            users = users.filter(email=options['user'])

        total = users.count()
        self.stdout.write(f'Generating daily looks for {total} user(s) on {target_date}...')

        ok = skipped = failed = 0

        for user in users:
            has_wardrobe = ClothingItem.objects.filter(user=user, is_active=True).exists()
            if not has_wardrobe:
                skipped += 1
                if options['verbosity'] >= 2:
                    self.stdout.write(f'  ⚪ {user.email} — no wardrobe items, skipped')
                continue

            if options['dry_run']:
                self.stdout.write(f'  🔍 {user.email} — would generate (dry run)')
                ok += 1
                continue

            try:
                result = run_daily_look(user, {'_target_date': target_date.isoformat()})
                if result.get('status') in ('stub', 'ai', 'no_wardrobe'):
                    ok += 1
                    rec_id = result.get('recommendation_id')
                    if options['verbosity'] >= 2:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ {user.email} — rec #{rec_id}')
                        )
                    # Send push notification
                    if rec_id:
                        from outfits.models import OutfitRecommendation
                        from outfits.notifications import send_daily_look_notification
                        try:
                            rec = OutfitRecommendation.objects.get(pk=rec_id)
                            send_daily_look_notification(user, rec)
                        except Exception as notif_exc:
                            if options['verbosity'] >= 2:
                                self.stderr.write(f'  ⚠️  Notification failed: {notif_exc}')
                else:
                    failed += 1
                    self.stderr.write(f'  ❌ {user.email} — unexpected status: {result}')
            except Exception as exc:
                failed += 1
                self.stderr.write(f'  ❌ {user.email} — error: {exc}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Generated: {ok}  |  Skipped (empty wardrobe): {skipped}  |  Failed: {failed}'
            )
        )
