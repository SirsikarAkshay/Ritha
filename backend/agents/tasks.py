"""
Celery tasks for async agent execution.

Instead of blocking the HTTP request, agents can be dispatched as background tasks:
    result = run_daily_look_task.delay(user_id, input_data)
    job_id = result.id   # poll /api/agents/jobs/<job_id>/ for status
"""

import logging

from celery import shared_task

logger = logging.getLogger("ritha.tasks")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="agents.run_daily_look",
)
def run_daily_look_task(self, user_id: int, input_data: dict) -> dict:
    """Run daily look generation asynchronously."""
    import datetime

    from django.contrib.auth import get_user_model

    from .models import AgentJob
    from .services import run_daily_look

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error("run_daily_look_task: user %s not found", user_id)
        return {"status": "error", "message": "User not found"}

    job = AgentJob.objects.create(
        user=user,
        agent_type="daily_look",
        input_data=input_data,
        status="running",
    )
    try:
        output = run_daily_look(user, input_data)
        job.status = "completed"
        job.output_data = output
        job.completed_at = datetime.datetime.now(tz=datetime.UTC)
        job.save()
        logger.info("daily_look completed for user %s, rec #%s", user.email, output.get("recommendation_id"))
        return output
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.save()
        logger.error("daily_look failed for user %s: %s", user.email, exc)
        raise self.retry(exc=exc) from exc


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="agents.run_packing_list",
)
def run_packing_list_task(self, user_id: int, input_data: dict) -> dict:
    """Run packing list generation asynchronously."""
    import datetime

    from django.contrib.auth import get_user_model

    from .models import AgentJob
    from .services import run_packing_list

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return {"status": "error", "message": "User not found"}

    job = AgentJob.objects.create(
        user=user,
        agent_type="packing_list",
        input_data=input_data,
        status="running",
    )
    try:
        output = run_packing_list(user, input_data)
        job.status = "completed"
        job.output_data = output
        job.completed_at = datetime.datetime.now(tz=datetime.UTC)
        job.save()
        return output
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.save()
        raise self.retry(exc=exc) from exc


@shared_task(name="agents.rebuild_style_profiles")
def rebuild_style_profiles_task() -> dict:
    """Rebuild every active user's style profile (§2.1).

    Designed for a nightly Celery Beat schedule. Cheap per-user so safe to
    run for the entire user table; large deployments should switch to an
    incremental rebuild keyed on `feedback_count` change.
    """
    from django.contrib.auth import get_user_model
    from outfits.style_profile import rebuild_for_user

    User = get_user_model()
    rebuilt = 0
    failed = 0
    for user in User.objects.filter(is_active=True).iterator():
        try:
            rebuild_for_user(user)
            rebuilt += 1
        except Exception as exc:
            logger.warning("rebuild_style_profile failed for user=%s: %s", user.id, exc)
            failed += 1

    logger.info("rebuild_style_profiles: rebuilt=%d failed=%d", rebuilt, failed)
    return {"rebuilt": rebuilt, "failed": failed}


@shared_task(name="agents.batch_daily_looks")
def batch_daily_looks_task() -> dict:
    """
    Celery Beat scheduled task — runs daily at 06:00 UTC.
    Replaces the crude infinite-sleep loop in the Docker cron service.
    """
    import datetime

    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = datetime.date.today().isoformat()

    users_with_wardrobe = User.objects.filter(
        is_active=True,
        wardrobe__is_active=True,
    ).distinct()

    dispatched = 0
    for user in users_with_wardrobe:
        run_daily_look_task.delay(user.id, {"_target_date": today})
        dispatched += 1

    logger.info("batch_daily_looks: dispatched %d tasks for %s", dispatched, today)
    return {"dispatched": dispatched, "date": today}
