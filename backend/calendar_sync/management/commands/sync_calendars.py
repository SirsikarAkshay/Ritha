"""
Management command: sync all connected calendars for all users.
Run daily via cron alongside generate_daily_looks.

Usage:
  python manage.py sync_calendars
  python manage.py sync_calendars --provider google
  python manage.py sync_calendars --provider apple
  python manage.py sync_calendars --user user@example.com
  python manage.py sync_calendars --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync Google and Apple calendars for all connected users'

    def add_arguments(self, parser):
        parser.add_argument('--provider', choices=['google', 'apple', 'outlook', 'all'], default='all')
        parser.add_argument('--user', default=None, help='Limit to specific user email')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        from calendar_sync import google_calendar, apple_calendar, outlook_calendar

        provider  = options['provider']
        dry_run   = options['dry_run']
        user_email = options['user']

        users = User.objects.filter(is_active=True)
        if user_email:
            users = users.filter(email=user_email)

        g_ok = g_fail = a_ok = a_fail = o_ok = o_fail = 0

        for user in users:
            # ── Google ────────────────────────────────────────────────────
            if provider in ('google', 'all') and user.google_calendar_connected:
                if dry_run:
                    self.stdout.write(f'  🔍 Would sync Google for {user.email}')
                    g_ok += 1
                else:
                    result = google_calendar.sync_events(user)
                    if 'error' in result:
                        g_fail += 1
                        if options['verbosity'] >= 1:
                            self.stderr.write(f'  ❌ Google {user.email}: {result["error"]}')
                    else:
                        g_ok += 1
                        if options['verbosity'] >= 2:
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✅ Google {user.email}: +{result["created"]} '
                                f'~{result["updated"]} events'
                            ))

            # ── Apple ─────────────────────────────────────────────────────
            if provider in ('apple', 'all') and user.apple_calendar_connected:
                if dry_run:
                    self.stdout.write(f'  🔍 Would sync Apple for {user.email}')
                    a_ok += 1
                else:
                    result = apple_calendar.sync_events(user)
                    if 'error' in result:
                        a_fail += 1
                        if options['verbosity'] >= 1:
                            self.stderr.write(f'  ❌ Apple {user.email}: {result["error"]}')
                    else:
                        a_ok += 1
                        if options['verbosity'] >= 2:
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✅ Apple {user.email}: +{result["created"]} '
                                f'~{result["updated"]} events'
                            ))

            # ── Outlook ───────────────────────────────────────────────────────
            if provider in ('outlook', 'all') and user.outlook_calendar_connected:
                if dry_run:
                    self.stdout.write(f'  🔍 Would sync Outlook for {user.email}')
                    o_ok += 1
                else:
                    result = outlook_calendar.sync_events(user)
                    if 'error' in result:
                        o_fail += 1
                        if options['verbosity'] >= 1:
                            self.stderr.write(f'  ❌ Outlook {user.email}: {result["error"]}')
                    else:
                        o_ok += 1
                        if options['verbosity'] >= 2:
                            self.stdout.write(self.style.SUCCESS(
                                f'  ✅ Outlook {user.email}: +{result["created"]} '
                                f'~{result["updated"]} events'
                            ))

        summary = []
        if provider in ('google', 'all'):
            summary.append(f'Google: {g_ok} ok, {g_fail} failed')
        if provider in ('apple', 'all'):
            summary.append(f'Apple: {a_ok} ok, {a_fail} failed')
        if provider in ('outlook', 'all'):
            summary.append(f'Outlook: {o_ok} ok, {o_fail} failed')

        self.stdout.write(self.style.SUCCESS(f'\nSync complete — {" | ".join(summary)}'))
