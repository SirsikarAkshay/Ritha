"""
Management command: register a Google Calendar push notification channel.

This tells Google to POST to your webhook URL whenever events change,
eliminating the need for constant polling.

Usage:
  python manage.py register_google_webhook
  python manage.py register_google_webhook --user user@example.com
  python manage.py register_google_webhook --ttl 604800  # 7-day channel

Prerequisites:
  - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET set in .env
  - FRONTEND_URL / webhook URL must be publicly accessible (not localhost)
  - User must have Google Calendar connected

Google's webhook channels expire — run this command weekly via cron or
use `make register-webhooks` to renew all channels.
"""
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    help = 'Register Google Calendar push notification webhook channels'

    def add_arguments(self, parser):
        parser.add_argument('--user',    default=None, help='Limit to specific user email')
        parser.add_argument('--ttl',     type=int, default=604800, help='Channel TTL in seconds (default: 7 days)')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        from calendar_sync.google_calendar import _dict_to_creds
        from calendar_sync.token_store import load_google_tokens

        webhook_url = (
            getattr(settings, 'GOOGLE_WEBHOOK_URL', None)
            or f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')}"
              .replace('localhost:3000', 'localhost:8000')
              + '/api/calendar/google/webhook/'
        )

        users = User.objects.filter(is_active=True, google_calendar_connected=True)
        if options['user']:
            users = users.filter(email=options['user'])

        if not users.exists():
            self.stdout.write(self.style.WARNING('No users with Google Calendar connected.'))
            return

        registered = failed = 0

        for user in users:
            creds_dict = load_google_tokens(user)
            if not creds_dict:
                self.stderr.write(f'  ⚠ {user.email}: no stored credentials')
                failed += 1
                continue

            if options['dry_run']:
                self.stdout.write(f'  🔍 Would register webhook for {user.email} → {webhook_url}')
                registered += 1
                continue

            try:
                from googleapiclient.discovery import build
                from google.auth.transport.requests import Request

                creds = _dict_to_creds(creds_dict)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())

                service    = build('calendar', 'v3', credentials=creds)
                channel_id = str(uuid.uuid4())

                body = {
                    'id':      channel_id,
                    'type':    'web_hook',
                    'address': webhook_url,
                    'token':   str(user.id),  # used to identify user in webhook handler
                    'params':  {'ttl': str(options['ttl'])},
                }

                # Register for the primary calendar
                result = service.events().watch(calendarId='primary', body=body).execute()

                if options['verbosity'] >= 1:
                    expiry_ms = result.get('expiration', 0)
                    import datetime
                    expiry = datetime.datetime.fromtimestamp(int(expiry_ms) / 1000).strftime('%Y-%m-%d %H:%M')
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✅ {user.email}: channel {channel_id[:8]}… expires {expiry}'
                    ))
                registered += 1

            except Exception as exc:
                failed += 1
                if options['verbosity'] >= 1:
                    self.stderr.write(f'  ❌ {user.email}: {exc}')

        self.stdout.write(self.style.SUCCESS(
            f'\nWebhook registration complete — {registered} registered, {failed} failed'
        ))
        if failed and 'localhost' in webhook_url:
            self.stdout.write(self.style.WARNING(
                '\n⚠ Webhook URL contains localhost — '
                'Google cannot reach this. Set GOOGLE_WEBHOOK_URL to your public URL.'
            ))
