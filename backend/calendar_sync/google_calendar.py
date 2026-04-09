"""
Google Calendar OAuth 2.0 integration.

Flow:
  1. GET  /api/calendar/google/connect/  → returns Google OAuth consent URL
  2. User visits URL, grants permission
  3. GET  /api/calendar/google/callback/?code=...  → exchanges code for tokens
  4. POST /api/calendar/google/sync/  → pulls events into CalendarEvent table
  5. POST /api/calendar/google/disconnect/  → revokes tokens and clears connection
"""
import json
import logging
import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone
from calendar_sync.token_store import load_google_tokens, store_google_tokens, encrypt_tokens

logger = logging.getLogger('arokah.calendar.google')

# Read-only calendar scope — we never write to the user's calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/userinfo.email']


def get_oauth_flow():
    """Return a configured google-auth Flow object."""
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id":     settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def get_authorization_url(state: str = '') -> tuple[str, str]:
    """
    Generate the Google OAuth consent URL.
    Returns (auth_url, state) — state is used to prevent CSRF in the callback.
    """
    flow = get_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',   # request refresh token
        include_granted_scopes='true',
        prompt='consent',        # always prompt so we get a refresh token
        state=state,
    )
    return auth_url, state


def exchange_code(code: str, state: str = '') -> dict:
    """
    Exchange an authorization code for access + refresh tokens.
    Returns the credentials dict to store on the user.
    """
    flow = get_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    return _creds_to_dict(creds)


def _creds_to_dict(creds) -> dict:
    return {
        'token':         creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri':     creds.token_uri,
        'client_id':     creds.client_id,
        'client_secret': creds.client_secret,
        'scopes':        list(creds.scopes) if creds.scopes else [],
        'expiry':        creds.expiry.isoformat() if creds.expiry else None,
    }


def _dict_to_creds(creds_dict: dict):
    from google.oauth2.credentials import Credentials
    import dateutil.parser

    expiry = None
    if creds_dict.get('expiry'):
        try:
            expiry = dateutil.parser.parse(creds_dict['expiry'])
        except Exception:
            pass

    return Credentials(
        token=creds_dict.get('token'),
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=creds_dict.get('client_id'),
        client_secret=creds_dict.get('client_secret'),
        scopes=creds_dict.get('scopes', SCOPES),
        expiry=expiry,
    )


def get_google_email(creds_dict: dict) -> Optional[str]:
    """Fetch the Gmail address associated with these credentials."""
    try:
        from googleapiclient.discovery import build
        creds = _dict_to_creds(creds_dict)
        service = build('oauth2', 'v2', credentials=creds)
        info = service.userinfo().get().execute()
        return info.get('email', '')
    except Exception as exc:
        logger.warning('Could not fetch Google email: %s', exc)
        return None


def sync_events(user, days_behind: int = 7, days_ahead: int = 60) -> dict:
    """
    Pull events from all of the user's Google Calendars and upsert them
    into the CalendarEvent table.

    Returns:
        {'created': int, 'updated': int, 'deleted': int, 'errors': list}
    """
    if not user.google_calendar_token:
        return {'error': 'No Google Calendar token. Connect first.'}

    creds_dict = load_google_tokens(user)
    if not creds_dict:
        return {'error': 'Stored token is corrupt or missing. Please reconnect.'}

    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        creds = _dict_to_creds(creds_dict)

        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist the refreshed token (encrypted)
            store_google_tokens(user, _creds_to_dict(creds))

        service  = build('calendar', 'v3', credentials=creds)
        now      = timezone.now()
        time_min = (now - datetime.timedelta(days=days_behind)).isoformat()
        time_max = (now + datetime.timedelta(days=days_ahead)).isoformat()

        created = updated = deleted = 0
        errors  = []

        # List all calendars the user has access to
        calendars = service.calendarList().list().execute()

        for cal in calendars.get('items', []):
            cal_id = cal['id']
            try:
                events_result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime',
                    maxResults=500,
                ).execute()

                for ev in events_result.get('items', []):
                    try:
                        c, u = _upsert_event(user, ev, cal_id)
                        created += c
                        updated += u
                    except Exception as e:
                        errors.append(f"Event {ev.get('id', '?')}: {e}")

            except Exception as e:
                errors.append(f"Calendar {cal_id}: {e}")

        # Mark sync timestamp
        user.google_calendar_synced_at = now
        user.google_calendar_connected  = True
        user.save(update_fields=['google_calendar_synced_at', 'google_calendar_connected'])

        logger.info(
            'Google sync for %s: +%d created, ~%d updated, %d errors',
            user.email, created, updated, len(errors)
        )
        return {'created': created, 'updated': updated, 'deleted': deleted, 'errors': errors}

    except Exception as exc:
        logger.error('Google Calendar sync failed for %s: %s', user.email, exc)
        return {'error': str(exc)}


def _upsert_event(user, raw_event: dict, calendar_id: str) -> tuple[int, int]:
    """
    Insert or update a single Google Calendar event.
    Returns (created_count, updated_count).
    """
    from itinerary.models import CalendarEvent
    from arokah.services.event_classifier import classify_event

    google_id = raw_event.get('id', '')
    status    = raw_event.get('status', 'confirmed')

    # Skip cancelled events — remove if we have them
    if status == 'cancelled':
        CalendarEvent.objects.filter(user=user, external_id=google_id, source='google').delete()
        return 0, 0

    # Parse start/end — Google sends either dateTime or date (all-day)
    start_raw = raw_event.get('start', {})
    end_raw   = raw_event.get('end', {})

    all_day   = 'date' in start_raw and 'dateTime' not in start_raw
    start_str = start_raw.get('dateTime') or (start_raw.get('date', '') + 'T00:00:00+00:00')
    end_str   = end_raw.get('dateTime')   or (end_raw.get('date', '') + 'T23:59:59+00:00')

    import dateutil.parser
    try:
        start_time = dateutil.parser.parse(start_str)
        end_time   = dateutil.parser.parse(end_str)
    except Exception:
        return 0, 0

    title       = raw_event.get('summary', '(No title)')
    description = raw_event.get('description', '')
    location    = raw_event.get('location', '')

    # Auto-classify the event type from title
    classification = classify_event(title, description)
    event_type     = classification['event_type']
    formality      = classification['formality']

    # Upsert by external_id + source
    event, created = CalendarEvent.objects.update_or_create(
        user=user,
        external_id=google_id,
        source='google',
        defaults={
            'title':       title,
            'description': description,
            'location':    location,
            'event_type':  event_type,
            'formality':   formality,
            'start_time':  start_time,
            'end_time':    end_time,
            'all_day':     all_day,
            'raw_data':    {
                'google_calendar_id': calendar_id,
                'google_event_id':    google_id,
                'html_link':          raw_event.get('htmlLink', ''),
                'attendees_count':    len(raw_event.get('attendees', [])),
            },
        },
    )
    return (1, 0) if created else (0, 1)


def revoke_access(user) -> bool:
    """Revoke Google OAuth tokens and clear connection from user."""
    if not user.google_calendar_token:
        return False
    try:
        import requests as req
        creds_dict = json.loads(user.google_calendar_token)
        token      = creds_dict.get('token') or creds_dict.get('refresh_token')
        if token:
            req.post('https://oauth2.googleapis.com/revoke',
                     params={'token': token}, timeout=5)
    except Exception as exc:
        logger.warning('Could not revoke Google token: %s', exc)

    user.google_calendar_token     = ''
    user.google_calendar_email     = ''
    user.google_calendar_connected  = False
    user.google_calendar_synced_at  = None
    user.save(update_fields=[
        'google_calendar_token', 'google_calendar_email',
        'google_calendar_connected', 'google_calendar_synced_at',
    ])
    return True
