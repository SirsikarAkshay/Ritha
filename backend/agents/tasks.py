"""
Celery tasks for async agent execution.

Instead of blocking the HTTP request, agents can be dispatched as background tasks:
    result = run_daily_look_task.delay(user_id, input_data)
    job_id = result.id   # poll /api/agents/jobs/<job_id>/ for status
"""
from celery import shared_task
import logging

logger = logging.getLogger('ritha.tasks')


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='agents.run_daily_look',
)
def run_daily_look_task(self, user_id: int, input_data: dict) -> dict:
    """Run daily look generation asynchronously."""
    from django.contrib.auth import get_user_model
    from .services import run_daily_look
    from .models import AgentJob
    import datetime

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error('run_daily_look_task: user %s not found', user_id)
        return {'status': 'error', 'message': 'User not found'}

    job = AgentJob.objects.create(
        user=user, agent_type='daily_look',
        input_data=input_data, status='running',
    )
    try:
        output = run_daily_look(user, input_data)
        job.status       = 'completed'
        job.output_data  = output
        job.completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        job.save()
        logger.info('daily_look completed for user %s, rec #%s',
                    user.email, output.get('recommendation_id'))
        return output
    except Exception as exc:
        job.status = 'failed'
        job.error  = str(exc)
        job.save()
        logger.error('daily_look failed for user %s: %s', user.email, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name='agents.run_packing_list',
)
def run_packing_list_task(self, user_id: int, input_data: dict) -> dict:
    """Run packing list generation asynchronously."""
    from django.contrib.auth import get_user_model
    from .services import run_packing_list
    from .models import AgentJob
    import datetime

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {'status': 'error', 'message': 'User not found'}

    job = AgentJob.objects.create(
        user=user, agent_type='packing_list',
        input_data=input_data, status='running',
    )
    try:
        output = run_packing_list(user, input_data)
        job.status       = 'completed'
        job.output_data  = output
        job.completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
        job.save()
        return output
    except Exception as exc:
        job.status = 'failed'
        job.error  = str(exc)
        job.save()
        raise self.retry(exc=exc)


@shared_task(name='agents.batch_daily_looks')
def batch_daily_looks_task() -> dict:
    """
    Celery Beat scheduled task — runs daily at 06:00 UTC.
    Replaces the crude infinite-sleep loop in the Docker cron service.
    """
    from django.contrib.auth import get_user_model
    from wardrobe.models import ClothingItem
    import datetime

    User = get_user_model()
    today = datetime.date.today().isoformat()

    users_with_wardrobe = User.objects.filter(
        is_active=True,
        wardrobe__is_active=True,
    ).distinct()

    dispatched = 0
    for user in users_with_wardrobe:
        run_daily_look_task.delay(user.id, {'_target_date': today})
        dispatched += 1

    logger.info('batch_daily_looks: dispatched %d tasks for %s', dispatched, today)
    return {'dispatched': dispatched, 'date': today}
