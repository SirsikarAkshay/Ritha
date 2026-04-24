"""
Send a test push notification to a user's registered device.

Usage:
    python manage.py test_push <email>
    python manage.py test_push <email> --title "Hello" --body "Test message"
"""
from django.core.management.base import BaseCommand, CommandError

from auth_app.models import User
from outfits.notifications import send_push


class Command(BaseCommand):
    help = 'Send a test push notification to a user via FCM'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email address')
        parser.add_argument('--title', default='Ritha Test', help='Notification title')
        parser.add_argument('--body', default='Push notifications are working!', help='Notification body')

    def handle(self, *args, **options):
        email = options['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'User not found: {email}')

        token = user.device_push_token
        if not token:
            raise CommandError(
                f'{email} has no device token registered. '
                f'Open the app → Profile → enable push notifications first.'
            )

        self.stdout.write(f'Sending test push to {email} (token: {token[:20]}…)')

        result = send_push(
            user,
            title=options['title'],
            body=options['body'],
            data={'type': 'test'},
        )

        if result['status'] == 'sent':
            self.stdout.write(self.style.SUCCESS(
                f'Push sent — message_id: {result.get("message_id")}'
            ))
        elif result['status'] == 'stub':
            self.stdout.write(self.style.WARNING(f'Not sent: {result["message"]}'))
        else:
            self.stdout.write(self.style.ERROR(f'Error: {result.get("message")}'))
