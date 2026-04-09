"""
Microsoft Outlook / Microsoft 365 Calendar integration.
Uses MSAL (Microsoft Authentication Library) for OAuth 2.0.

Flow:
  1. GET  /api/calendar/outlook/connect/   → returns Microsoft OAuth consent URL
  2. User visits URL, grants permission
  3. GET  /api/calendar/outlook/callback/  → exchanges code for tokens
  4. POST /api/calendar/outlook/sync/      → pulls events via Microsoft Graph API
  5. POST /api/calendar/outlook/disconnect/ → clears tokens

Required scopes (delegated, read-only):
  - Calendars.Read
  - User.Read (to get the Microsoft account email)
"""
import json
import logging
import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone
from calendar_sync.token_store import load_outlook_tokens, store_outlook_tokens

logger = logging.getLogger('arokah.calendar.outlook')

GRAPH_BASE   = 'https://graph.microsoft.com/v1.0'
AUTHORITY    = 'https://login.microsoftonline.com/common'
SCOPES       = ['Calendars.Read', 'User.Read', 'offline_access']


def _get_msal_app():
    """Return a configured MSAL ConfidentialClientApplication."""
    import msal
    return msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=AUTHORITY,
    )


def get_authorization_url(state: str = '') -> tuple[str, str]:
    """
    Generate the Microsoft OAuth consent URL.
    Returns (auth_url, state).
    """
    app      = _get_msal_app()
    flow     = app.initiate_auth_code_flow(
        scopes=SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        state=state,
        response_mode='query',
    )
    return flow['auth_uri'], flow.get('state', state)


def exchange_code(code: str, state: str = '') -> dict:
    """
    Exchange an authorization code for access + refresh tokens.
    Returns a dict to store on the user.
    """
    import msal, requests as req

    app = _get_msal_app()
    # MSAL requires the full flow dict — rebuild a minimal one
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )
    if 'error' in result:
        raise Exception(f"Token exchange failed: {result.get('error_description', result['error'])}")

    return {
        'access_token':  result['access_token'],
        'refresh_token': result.get('refresh_token', ''),
        'id_token':      result.get('id_token', ''),
        'expires_in':    result.get('expires_in', 3600),
        'token_type':    result.get('token_type', 'Bearer'),
    }


def _get_access_token(user) -> Optional[str]:
    """Return a valid access token, refreshing if needed."""
    import msal

    creds = load_outlook_tokens(user)
    refresh_token = creds.get('refresh_token', '')
    if not refresh_token:
        return creds.get('access_token')

    app    = _get_msal_app()
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
    if 'error' not in result:
        creds['access_token']  = result['access_token']
        creds['refresh_token'] = result.get('refresh_token', refresh_token)
        store_outlook_tokens(user, creds)
        return creds['access_token']

    logger.warning('Outlook token refresh failed for %s: %s', user.email, result.get('error_description'))
    return creds.get('access_token')


def get_outlook_email(access_token: str) -> Optional[str]:
    """Fetch the Microsoft account email via Graph API /me."""
    try:
        import requests as req
        r = req.get(
            f'{GRAPH_BASE}/me',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=8,
        )
        r.raise_for_status()
        return r.json().get('mail') or r.json().get('userPrincipalName', '')
    except Exception as exc:
        logger.warning('Could not fetch Outlook email: %s', exc)
        return None


def sync_events(user, days_behind: int = 7, days_ahead: int = 60) -> dict:
    """
    Pull events from Microsoft 365 Calendar via Graph API.
    Returns {'created': int, 'updated': int, 'errors': list}
    """
    if not user.outlook_calendar_token:
        return {'error': 'Outlook Calendar not connected. Connect first.'}

    try:
        access_token = _get_access_token(user)
        if not access_token:
            return {'error': 'Could not obtain valid access token. Please reconnect.'}
        import requests as req

        now      = timezone.now()
        start_dt = (now - datetime.timedelta(days=days_behind)).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_dt   = (now + datetime.timedelta(days=days_ahead)).strftime('%Y-%m-%dT%H:%M:%SZ')

        headers  = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type':  'application/json',
            'Prefer':        'outlook.timezone="UTC"',
        }

        # Get all calendars
        cals_r = req.get(f'{GRAPH_BASE}/me/calendars', headers=headers, timeout=10)
        cals_r.raise_for_status()
        calendars = cals_r.json().get('value', [])

        created = updated = 0
        errors  = []

        for cal in calendars:
            cal_id   = cal['id']
            cal_name = cal.get('name', 'Calendar')
            url      = (
                f"{GRAPH_BASE}/me/calendars/{cal_id}/calendarView"
                f"?startDateTime={start_dt}&endDateTime={end_dt}"
                f"&$top=500&$select=id,subject,bodyPreview,location,start,end,isAllDay,isCancelled,status"
            )

            while url:
                try:
                    r = req.get(url, headers=headers, timeout=15)
                    r.raise_for_status()
                    data     = r.json()
                    for ev in data.get('value', []):
                        try:
                            c, u = _upsert_event(user, ev, cal_name)
                            created += c
                            updated += u
                        except Exception as e:
                            errors.append(f"Event {ev.get('id','?')}: {e}")
                    url = data.get('@odata.nextLink')   # pagination
                except Exception as e:
                    errors.append(f"Calendar {cal_name}: {e}")
                    break

        user.outlook_calendar_synced_at  = now
        user.outlook_calendar_connected  = True
        user.save(update_fields=['outlook_calendar_synced_at', 'outlook_calendar_connected'])

        logger.info('Outlook sync for %s: +%d created, ~%d updated, %d errors',
                    user.email, created, updated, len(errors))
        return {'created': created, 'updated': updated, 'errors': errors}

    except Exception as exc:
        logger.error('Outlook sync failed for %s: %s', user.email, exc)
        return {'error': str(exc)}


def _upsert_event(user, raw: dict, calendar_name: str) -> tuple[int, int]:
    from itinerary.models import CalendarEvent
    from arokah.services.event_classifier import classify_event

    event_id  = raw.get('id', '')
    cancelled = raw.get('isCancelled', False)

    if cancelled:
        CalendarEvent.objects.filter(user=user, external_id=event_id, source='outlook').delete()
        return 0, 0

    title       = raw.get('subject', '(No title)')
    description = raw.get('bodyPreview', '')
    location    = raw.get('location', {}).get('displayName', '')
    all_day     = raw.get('isAllDay', False)

    # Graph API returns start/end as { dateTime, timeZone } or { date } for all-day
    start_raw = raw.get('start', {})
    end_raw   = raw.get('end', {})

    import dateutil.parser, pytz

    def _parse(d):
        v = d.get('dateTime') or d.get('date', '')
        if not v:
            return timezone.now()
        dt = dateutil.parser.parse(v)
        return dt if dt.tzinfo else pytz.utc.localize(dt)

    start_time = _parse(start_raw)
    end_time   = _parse(end_raw)

    classification = classify_event(title, description)

    event, created = CalendarEvent.objects.update_or_create(
        user=user,
        external_id=event_id,
        source='outlook',
        defaults={
            'title':       title,
            'description': description,
            'location':    location,
            'event_type':  classification['event_type'],
            'formality':   classification['formality'],
            'start_time':  start_time,
            'end_time':    end_time,
            'all_day':     all_day,
            'raw_data':    {'calendar_name': calendar_name, 'source': 'microsoft_graph'},
        },
    )
    return (1, 0) if created else (0, 1)


def revoke_access(user) -> bool:
    """Clear Outlook tokens from user (Microsoft doesn't have a simple revoke endpoint)."""
    user.outlook_calendar_token = ''
    user.save(update_fields=['outlook_calendar_token'])
    logger.info('Outlook Calendar disconnected for %s', user.email)
    return True
