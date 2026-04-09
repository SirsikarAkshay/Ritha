"""
Apple Calendar CalDAV integration.

Apple does not use OAuth — users provide their Apple ID and an
App-Specific Password (generated at appleid.apple.com/account/manage).

Flow:
  1. User provides Apple ID + App-Specific Password in the app
  2. POST /api/calendar/apple/connect/  → validates credentials, stores them
  3. POST /api/calendar/apple/sync/     → pulls events via CalDAV
  4. POST /api/calendar/apple/disconnect/ → clears credentials
"""
import logging
import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('arokah.calendar.apple')

APPLE_CALDAV_URL = 'https://caldav.icloud.com/'


def test_connection(username: str, password: str) -> tuple[bool, str]:
    """
    Validate Apple ID credentials by attempting a CalDAV connection.
    Returns (success: bool, message: str).
    """
    try:
        import caldav
        client = caldav.DAVClient(
            url=APPLE_CALDAV_URL,
            username=username,
            password=password,
        )
        principal = client.principal()
        calendars = principal.calendars()
        cal_count = len(calendars)
        return True, f'Connected — {cal_count} calendar{"s" if cal_count != 1 else ""} found.'
    except Exception as exc:
        msg = str(exc)
        if 'Unauthorized' in msg or '401' in msg:
            return False, ('Authentication failed. Make sure you are using an '
                           'App-Specific Password from appleid.apple.com, not your Apple ID password.')
        if 'SSL' in msg or 'certificate' in msg.lower():
            return False, 'SSL error connecting to Apple servers. Please try again.'
        return False, f'Connection failed: {msg}'


def _encrypt_password(raw: str) -> str:
    """
    Simple reversible encryption for the App-Specific Password.
    In production, use Django's django-encrypted-model-fields or AWS KMS.
    Here we use a Fernet key derived from SECRET_KEY for at-rest protection.
    """
    from cryptography.fernet import Fernet
    import base64, hashlib
    from django.conf import settings

    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
    f = Fernet(key)
    return f.encrypt(raw.encode()).decode()


def _decrypt_password(encrypted: str) -> str:
    from cryptography.fernet import Fernet, InvalidToken
    import base64, hashlib
    from django.conf import settings

    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    )
    f = Fernet(key)
    try:
        return f.decrypt(encrypted.encode()).decode()
    except (InvalidToken, Exception):
        return ''


def save_credentials(user, username: str, password: str) -> None:
    """Encrypt and persist Apple credentials on the user."""
    user.apple_calendar_username  = username
    user.apple_calendar_password  = _encrypt_password(password)
    user.apple_calendar_connected = True
    user.save(update_fields=[
        'apple_calendar_username', 'apple_calendar_password', 'apple_calendar_connected',
    ])


def get_credentials(user) -> tuple[str, str]:
    """Return (username, decrypted_password) for a connected user."""
    if not user.apple_calendar_username:
        return '', ''
    return user.apple_calendar_username, _decrypt_password(user.apple_calendar_password)


def sync_events(user, days_behind: int = 7, days_ahead: int = 60) -> dict:
    """
    Pull events from Apple Calendar (CalDAV) and upsert into CalendarEvent table.
    Returns {'created': int, 'updated': int, 'errors': list}
    """
    username, password = get_credentials(user)
    if not username:
        return {'error': 'Apple Calendar not connected. Add credentials first.'}

    try:
        import caldav
        from caldav.elements import dav

        client    = caldav.DAVClient(url=APPLE_CALDAV_URL, username=username, password=password)
        principal = client.principal()
        calendars = principal.calendars()

        now      = timezone.now()
        start_dt = now - datetime.timedelta(days=days_behind)
        end_dt   = now + datetime.timedelta(days=days_ahead)

        created = updated = 0
        errors  = []

        for cal in calendars:
            try:
                cal_name = str(cal.name or 'Calendar')
                events   = cal.date_search(start=start_dt, end=end_dt, expand=True)
                for event in events:
                    try:
                        c, u = _upsert_caldav_event(user, event, cal_name)
                        created += c
                        updated += u
                    except Exception as e:
                        errors.append(f'{cal_name}: {e}')
            except Exception as e:
                errors.append(f'Calendar error: {e}')

        user.apple_calendar_synced_at  = now
        user.apple_calendar_connected  = True
        user.save(update_fields=['apple_calendar_synced_at', 'apple_calendar_connected'])

        logger.info(
            'Apple sync for %s: +%d created, ~%d updated, %d errors',
            user.email, created, updated, len(errors)
        )
        return {'created': created, 'updated': updated, 'errors': errors}

    except Exception as exc:
        logger.error('Apple Calendar sync failed for %s: %s', user.email, exc)
        return {'error': str(exc)}


def _upsert_caldav_event(user, caldav_event, calendar_name: str) -> tuple[int, int]:
    """Parse a CalDAV event object and upsert into CalendarEvent."""
    from itinerary.models import CalendarEvent
    from arokah.services.event_classifier import classify_event
    import icalendar

    try:
        cal     = icalendar.Calendar.from_ical(caldav_event.data)
        components = list(cal.walk('VEVENT'))
        if not components:
            return 0, 0
        vevent = components[0]
    except Exception:
        return 0, 0

    # Extract fields
    uid         = str(vevent.get('UID', ''))
    summary     = str(vevent.get('SUMMARY', '(No title)'))
    description = str(vevent.get('DESCRIPTION', ''))
    location    = str(vevent.get('LOCATION', ''))
    status      = str(vevent.get('STATUS', 'CONFIRMED')).upper()

    if status == 'CANCELLED':
        CalendarEvent.objects.filter(user=user, external_id=uid, source='apple').delete()
        return 0, 0

    # Parse start/end — may be date or datetime
    dtstart = vevent.get('DTSTART')
    dtend   = vevent.get('DTEND') or vevent.get('DURATION')

    if dtstart is None:
        return 0, 0

    start_val = dtstart.dt
    end_val   = dtend.dt if dtend else start_val

    all_day = isinstance(start_val, datetime.date) and not isinstance(start_val, datetime.datetime)

    # Normalise to timezone-aware datetimes
    import pytz
    def _to_dt(v):
        if isinstance(v, datetime.datetime):
            return v if v.tzinfo else pytz.utc.localize(v)
        if isinstance(v, datetime.date):
            return pytz.utc.localize(datetime.datetime(v.year, v.month, v.day))
        return timezone.now()

    start_time = _to_dt(start_val)
    end_time   = _to_dt(end_val)

    # Handle DURATION instead of DTEND
    if hasattr(end_val, 'seconds') or hasattr(end_val, 'days'):
        end_time = start_time + end_val

    classification = classify_event(summary, description)

    event, created = CalendarEvent.objects.update_or_create(
        user=user,
        external_id=uid,
        source='apple',
        defaults={
            'title':       summary,
            'description': description,
            'location':    location,
            'event_type':  classification['event_type'],
            'formality':   classification['formality'],
            'start_time':  start_time,
            'end_time':    end_time,
            'all_day':     all_day,
            'raw_data':    {
                'calendar_name': calendar_name,
                'uid':           uid,
                'source':        'apple_caldav',
            },
        },
    )
    return (1, 0) if created else (0, 1)


def disconnect(user) -> None:
    """Clear Apple Calendar credentials from user."""
    user.apple_calendar_username  = ''
    user.apple_calendar_password  = ''
    user.apple_calendar_connected = False
    user.apple_calendar_synced_at = None
    user.save(update_fields=[
        'apple_calendar_username', 'apple_calendar_password',
        'apple_calendar_connected', 'apple_calendar_synced_at',
    ])
