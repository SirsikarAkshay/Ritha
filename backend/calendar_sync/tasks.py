"""
Celery tasks for periodic calendar synchronization.

Scheduled via django-celery-beat:
  - sync_all_calendars: runs every 30 minutes, syncs all connected providers
  - deduplicate_events: runs hourly, merges cross-source duplicate events
"""
import logging
import datetime

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('ritha.calendar.tasks')


@shared_task(name='calendar.sync_user_calendars')
def sync_user_calendars(user_id: int) -> dict:
    """Sync all connected calendar providers for a single user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return {'error': 'user not found'}

    results = {}

    if user.google_calendar_connected:
        try:
            from . import google_calendar
            stats = google_calendar.sync_events(user)
            results['google'] = {'created': stats.get('created', 0), 'updated': stats.get('updated', 0)}
            logger.info('Google sync for %s: %s', user.email, results['google'])
        except Exception as exc:
            results['google'] = {'error': str(exc)}
            logger.warning('Google sync failed for %s: %s', user.email, exc)

    if user.apple_calendar_connected:
        try:
            from . import apple_calendar
            stats = apple_calendar.sync_events(user)
            results['apple'] = {'created': stats.get('created', 0), 'updated': stats.get('updated', 0)}
            logger.info('Apple sync for %s: %s', user.email, results['apple'])
        except Exception as exc:
            results['apple'] = {'error': str(exc)}
            logger.warning('Apple sync failed for %s: %s', user.email, exc)

    if user.outlook_calendar_connected:
        try:
            from . import outlook_calendar
            stats = outlook_calendar.sync_events(user)
            results['outlook'] = {'created': stats.get('created', 0), 'updated': stats.get('updated', 0)}
            logger.info('Outlook sync for %s: %s', user.email, results['outlook'])
        except Exception as exc:
            results['outlook'] = {'error': str(exc)}
            logger.warning('Outlook sync failed for %s: %s', user.email, exc)

    return results


@shared_task(name='calendar.sync_all_calendars')
def sync_all_calendars() -> dict:
    """
    Periodic task — sync calendars for all users with at least one connected provider.
    Dispatches individual sync tasks per user for parallelism.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()

    users = User.objects.filter(
        is_active=True,
    ).filter(
        Q(google_calendar_connected=True) |
        Q(apple_calendar_connected=True) |
        Q(outlook_calendar_connected=True)
    )

    dispatched = 0
    for user in users:
        sync_user_calendars.delay(user.id)
        dispatched += 1

    logger.info('sync_all_calendars: dispatched %d user sync tasks', dispatched)
    return {'dispatched': dispatched}


@shared_task(name='calendar.deduplicate_events')
def deduplicate_events() -> dict:
    """
    Merge duplicate events that appear from multiple sources.

    Two events are considered duplicates when they belong to the same user,
    have overlapping start times (within 5 minutes), and have similar titles.
    The event from the preferred source is kept; others get `is_duplicate=True`.
    """
    from itinerary.models import CalendarEvent
    from django.db.models import Count

    SOURCE_PRIORITY = {'google': 1, 'outlook': 2, 'apple': 3, 'device': 4}
    now = timezone.now()
    window_start = now - datetime.timedelta(days=7)
    window_end = now + datetime.timedelta(days=60)

    events = CalendarEvent.objects.filter(
        start_time__range=(window_start, window_end),
    ).exclude(
        raw_data__has_key='is_duplicate',
    ).select_related('user').order_by('user_id', 'start_time')

    merged = 0
    seen = {}

    for ev in events:
        norm_title = _normalize_title(ev.title)
        rounded_start = _round_time(ev.start_time, minutes=5)
        key = (ev.user_id, norm_title, rounded_start)

        if key in seen:
            existing = seen[key]
            existing_priority = SOURCE_PRIORITY.get(existing.source, 99)
            current_priority = SOURCE_PRIORITY.get(ev.source, 99)

            if current_priority < existing_priority:
                _mark_duplicate(existing, ev)
                seen[key] = ev
            else:
                _mark_duplicate(ev, existing)
            merged += 1
        else:
            seen[key] = ev

    logger.info('deduplicate_events: merged %d duplicates', merged)
    return {'merged': merged}


def _normalize_title(title: str) -> str:
    """Lowercase, strip whitespace and common prefixes for comparison."""
    import re
    t = (title or '').lower().strip()
    t = re.sub(r'^(re:|fwd?:)\s*', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def _round_time(dt, minutes=5):
    """Round a datetime to the nearest N minutes for fuzzy matching."""
    if dt is None:
        return None
    rounded = dt.replace(second=0, microsecond=0)
    minute = (rounded.minute // minutes) * minutes
    return rounded.replace(minute=minute)


def _mark_duplicate(duplicate_ev, primary_ev):
    """Mark an event as a duplicate, linking to the primary."""
    raw = duplicate_ev.raw_data or {}
    raw['is_duplicate'] = True
    raw['primary_event_id'] = primary_ev.id
    raw['primary_source'] = primary_ev.source
    duplicate_ev.raw_data = raw
    duplicate_ev.save(update_fields=['raw_data'])
