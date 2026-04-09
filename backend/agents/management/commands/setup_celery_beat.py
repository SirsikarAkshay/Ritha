"""
Register Celery Beat periodic tasks in the database.
Run once after migrate: python manage.py setup_celery_beat
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Register Celery Beat periodic tasks'

    def handle(self, *args, **options):
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json

        # Daily looks at 06:00 UTC every day
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='6',
            day_of_week='*', day_of_month='*', month_of_year='*',
        )

        task, created = PeriodicTask.objects.update_or_create(
            name='Daily look batch',
            defaults={
                'task':    'agents.batch_daily_looks',
                'crontab': schedule,
                'args':    json.dumps([]),
                'enabled': True,
            }
        )

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} periodic task: "{task.name}" — runs daily at 06:00 UTC'
        ))
