"""
Calendar integration API views.

Google Calendar:
  GET  /api/calendar/google/connect/      → OAuth consent URL
  GET  /api/calendar/google/callback/     → OAuth callback (browser redirect)
  POST /api/calendar/google/sync/         → Pull events now
  POST /api/calendar/google/disconnect/  → Revoke & clear

Apple Calendar:
  POST /api/calendar/apple/connect/       → Validate credentials + save
  POST /api/calendar/apple/sync/          → Pull events now
  POST /api/calendar/apple/disconnect/   → Clear credentials

Status:
  GET  /api/calendar/status/              → Both connections' status
"""
import json
import secrets
import logging

from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import google_calendar, apple_calendar

logger = logging.getLogger('arokah.calendar.views')


# ── Shared response schema ─────────────────────────────────────────────────
def _sync_schema(name):
    return inline_serializer(name=name, fields={
        'created': serializers.IntegerField(),
        'updated': serializers.IntegerField(),
        'errors':  serializers.ListField(child=serializers.CharField()),
    })


# ── Status ─────────────────────────────────────────────────────────────────
class CalendarStatusView(APIView):
    """GET /api/calendar/status/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Calendar connection status",
        description="Returns connection status for Google and Apple calendars.",
        responses={200: None},
    )
    def get(self, request):
        user = request.user
        return Response({
            'google': {
                'connected':  user.google_calendar_connected,
                'email':      user.google_calendar_email or None,
                'synced_at':  user.google_calendar_synced_at,
            },
            'apple': {
                'connected':  user.apple_calendar_connected,
                'username':   user.apple_calendar_username or None,
                'synced_at':  user.apple_calendar_synced_at,
            },
            'outlook': {
                'connected':  user.outlook_calendar_connected,
                'email':      user.outlook_calendar_email or None,
                'synced_at':  user.outlook_calendar_synced_at,
            },
        })


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

class GoogleConnectView(APIView):
    """GET /api/calendar/google/connect/ — returns the OAuth URL."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Start Google Calendar OAuth flow",
        description=(
            "Returns a URL the user should open in their browser to grant "
            "Arokah read-only access to their Google Calendar. "
            "Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to be set."
        ),
        responses={200: None},
    )
    def get(self, request):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return Response(
                {'error': {'code': 'not_configured',
                           'message': 'Google Calendar integration is not configured. '
                                      'Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.'}},
                status=503,
            )

        # Store user ID in state to link callback to user
        state = f"{request.user.id}:{secrets.token_hex(16)}"

        try:
            auth_url, _, code_verifier = google_calendar.get_authorization_url(state=state)
        except Exception as exc:
            return Response(
                {'error': {'code': 'oauth_error', 'message': str(exc)}},
                status=500,
            )

        # Persist the PKCE verifier so the callback can complete the exchange.
        from django.core.cache import cache
        cache.set(f'google_oauth_verifier:{state}', code_verifier, timeout=600)

        return Response({
            'auth_url':   auth_url,
            'message':    'Open auth_url in the browser to connect your Google Calendar.',
            'note':       'The user will be redirected back to GOOGLE_REDIRECT_URI after granting access.',
        })


class GoogleCallbackView(APIView):
    """
    GET /api/calendar/google/callback/?code=...&state=...
    Handles the OAuth redirect from Google.
    In production this redirects the browser to the frontend.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class   = None

    def get(self, request):
        code  = request.query_params.get('code', '')
        state = request.query_params.get('state', '')
        error = request.query_params.get('error', '')

        frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        if error:
            return redirect(f"{frontend_base}/profile?calendar=google&status=denied")

        if not code:
            return redirect(f"{frontend_base}/profile?calendar=google&status=error&reason=no_code")

        # Extract user ID from state
        try:
            user_id = int(state.split(':')[0])
        except (ValueError, IndexError):
            return redirect(f"{frontend_base}/profile?calendar=google&status=error&reason=invalid_state")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return redirect(f"{frontend_base}/profile?calendar=google&status=error&reason=user_not_found")

        from django.core.cache import cache
        verifier_key  = f'google_oauth_verifier:{state}'
        code_verifier = cache.get(verifier_key, '')

        try:
            creds_dict = google_calendar.exchange_code(code, code_verifier=code_verifier)
        except Exception as exc:
            logger.error('Google OAuth exchange failed: %s', exc)
            return redirect(f"{frontend_base}/profile?calendar=google&status=error&reason=exchange_failed")
        finally:
            cache.delete(verifier_key)

        # Fetch the Google account email for display
        google_email = google_calendar.get_google_email(creds_dict) or ''

        from calendar_sync.token_store import encrypt_tokens
        user.google_calendar_token     = encrypt_tokens(creds_dict)
        user.google_calendar_email     = google_email
        user.google_calendar_connected  = True
        user.save(update_fields=[
            'google_calendar_token', 'google_calendar_email', 'google_calendar_connected',
        ])

        logger.info('Google Calendar connected for %s (%s)', user.email, google_email)

        # Trigger an initial sync asynchronously (fire and forget)
        try:
            google_calendar.sync_events(user)
        except Exception as exc:
            logger.warning('Initial Google sync failed: %s', exc)

        return redirect(f"{frontend_base}/profile?calendar=google&status=connected")


class GoogleSyncView(APIView):
    """POST /api/calendar/google/sync/ — pull latest events."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Sync Google Calendar events",
        description="Pulls events from the last 7 days and next 60 days into Arokah.",
        responses={200: _sync_schema('GoogleSyncResult')},
    )
    def post(self, request):
        if not request.user.google_calendar_connected:
            return Response(
                {'error': {'code': 'not_connected',
                           'message': 'Google Calendar is not connected. Use /api/calendar/google/connect/ first.'}},
                status=400,
            )

        result = google_calendar.sync_events(
            request.user,
            days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
            days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
        )

        if 'error' in result:
            return Response({'error': {'code': 'sync_failed', 'message': result['error']}}, status=500)

        return Response({
            'status':  'synced',
            'created': result['created'],
            'updated': result['updated'],
            'errors':  result.get('errors', []),
        })


class GoogleDisconnectView(APIView):
    """POST /api/calendar/google/disconnect/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Disconnect Google Calendar",
        description="Revokes OAuth tokens and removes the connection.",
        responses={200: None},
    )
    def post(self, request):
        google_calendar.revoke_access(request.user)
        return Response({'message': 'Google Calendar disconnected.'})


# ─────────────────────────────────────────────────────────────────────────────
# APPLE CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

class AppleConnectView(APIView):
    """POST /api/calendar/apple/connect/ — validate & save credentials."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Connect Apple Calendar (CalDAV)",
        description=(
            "Validates the provided Apple ID and App-Specific Password by "
            "connecting to Apple's CalDAV server. "
            "Users must generate an App-Specific Password at appleid.apple.com — "
            "their regular Apple ID password will NOT work."
        ),
        responses={200: None},
    )
    def post(self, request):
        username = apple_calendar.normalize_apple_id(request.data.get('username', ''))
        password = apple_calendar.normalize_app_password(request.data.get('password', ''))

        if not username or not password:
            return Response(
                {'error': {'code': 'missing_fields',
                           'message': '`username` (Apple ID email) and `password` (App-Specific Password) are required.'}},
                status=400,
            )

        success, message = apple_calendar.test_connection(username, password)
        if not success:
            return Response(
                {'error': {'code': 'connection_failed', 'message': message}},
                status=400,
            )

        apple_calendar.save_credentials(request.user, username, password)
        return Response({
            'status':  'connected',
            'message': message,
            'username': username,
        })


class AppleSyncView(APIView):
    """POST /api/calendar/apple/sync/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Sync Apple Calendar events",
        description="Pulls events via CalDAV from the last 7 days and next 60 days.",
        responses={200: _sync_schema('AppleSyncResult')},
    )
    def post(self, request):
        if not request.user.apple_calendar_connected:
            return Response(
                {'error': {'code': 'not_connected',
                           'message': 'Apple Calendar is not connected. Use /api/calendar/apple/connect/ first.'}},
                status=400,
            )

        result = apple_calendar.sync_events(
            request.user,
            days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
            days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
        )

        if 'error' in result:
            return Response({'error': {'code': 'sync_failed', 'message': result['error']}}, status=500)

        return Response({
            'status':  'synced',
            'created': result['created'],
            'updated': result['updated'],
            'errors':  result.get('errors', []),
        })


class AppleDisconnectView(APIView):
    """POST /api/calendar/apple/disconnect/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Disconnect Apple Calendar",
        description="Removes stored Apple credentials from Arokah.",
        responses={200: None},
    )
    def post(self, request):
        apple_calendar.disconnect(request.user)
        return Response({'message': 'Apple Calendar disconnected and credentials removed.'})


# ─────────────────────────────────────────────────────────────────────────────
# OUTLOOK / MICROSOFT 365 CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

class OutlookConnectView(APIView):
    """GET /api/calendar/outlook/connect/ — returns the Microsoft OAuth consent URL."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Start Outlook Calendar OAuth flow",
        description=(
            "Returns a URL for Microsoft OAuth consent. "
            "Requires MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET in .env."
        ),
        responses={200: None},
    )
    def get(self, request):
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            return Response(
                {'error': {'code': 'not_configured',
                           'message': 'Outlook Calendar integration is not configured. '
                                      'Add MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET to .env.'}},
                status=503,
            )

        state = f"{request.user.id}:{secrets.token_hex(16)}"
        try:
            from calendar_sync import outlook_calendar
            auth_url, flow_dict = outlook_calendar.get_authorization_url(state=state)
        except Exception as exc:
            return Response({'error': {'code': 'oauth_error', 'message': str(exc)}}, status=500)

        # Persist the MSAL auth code flow dict so the callback can use it.
        # Store on the user record (encrypted) — MSAL needs it to complete the exchange.
        from calendar_sync.token_store import encrypt_tokens
        request.user.outlook_calendar_token = encrypt_tokens({'_msal_flow': flow_dict})
        request.user.save(update_fields=['outlook_calendar_token'])

        return Response({
            'auth_url': auth_url,
            'message':  'Open auth_url in the browser to connect your Outlook / Microsoft 365 Calendar.',
        })


class OutlookCallbackView(APIView):
    """GET /api/calendar/outlook/callback/?code=...&state=..."""
    permission_classes = [permissions.AllowAny]
    serializer_class   = None

    def get(self, request):
        from calendar_sync import outlook_calendar
        from calendar_sync.token_store import encrypt_tokens, decrypt_tokens

        code  = request.query_params.get('code', '')
        state = request.query_params.get('state', '')
        error = request.query_params.get('error', '')
        frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5175')

        if error:
            return redirect(f"{frontend_base}/profile?calendar=outlook&status=denied")
        if not code:
            return redirect(f"{frontend_base}/profile?calendar=outlook&status=error&reason=no_code")

        try:
            user_id = int(state.split(':')[0])
        except (ValueError, IndexError):
            return redirect(f"{frontend_base}/profile?calendar=outlook&status=error&reason=invalid_state")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return redirect(f"{frontend_base}/profile?calendar=outlook&status=error&reason=user_not_found")

        # Recover the MSAL auth code flow dict persisted during connect
        stored = decrypt_tokens(user.outlook_calendar_token) if user.outlook_calendar_token else {}
        msal_flow = stored.get('_msal_flow')

        try:
            creds_dict = outlook_calendar.exchange_code(code, state, msal_flow=msal_flow)
        except Exception as exc:
            logger.error('Outlook OAuth exchange failed: %s', exc)
            return redirect(f"{frontend_base}/profile?calendar=outlook&status=error&reason=exchange_failed")

        outlook_email = outlook_calendar.get_outlook_email(creds_dict['access_token']) or ''
        user.outlook_calendar_token     = encrypt_tokens(creds_dict)
        user.outlook_calendar_email     = outlook_email
        user.outlook_calendar_connected = True
        user.save(update_fields=[
            'outlook_calendar_token', 'outlook_calendar_email', 'outlook_calendar_connected',
        ])

        logger.info('Outlook Calendar connected for %s (%s)', user.email, outlook_email)

        try:
            outlook_calendar.sync_events(user)
        except Exception as exc:
            logger.warning('Initial Outlook sync failed: %s', exc)

        return redirect(f"{frontend_base}/profile?calendar=outlook&status=connected")


class OutlookSyncView(APIView):
    """POST /api/calendar/outlook/sync/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Sync Outlook Calendar events",
        description="Pulls events via Microsoft Graph API for the last 7 days and next 60 days.",
        responses={200: _sync_schema('OutlookSyncResult')},
    )
    def post(self, request):
        if not request.user.outlook_calendar_connected:
            return Response(
                {'error': {'code': 'not_connected',
                           'message': 'Outlook Calendar is not connected.'}},
                status=400,
            )
        from calendar_sync import outlook_calendar
        result = outlook_calendar.sync_events(
            request.user,
            days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
            days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
        )
        if 'error' in result:
            return Response({'error': {'code': 'sync_failed', 'message': result['error']}}, status=500)
        return Response({'status': 'synced', 'created': result['created'],
                         'updated': result['updated'], 'errors': result.get('errors', [])})


class OutlookDisconnectView(APIView):
    """POST /api/calendar/outlook/disconnect/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(summary="Disconnect Outlook Calendar", responses={200: None})
    def post(self, request):
        from calendar_sync import outlook_calendar
        outlook_calendar.revoke_access(request.user)
        request.user.outlook_calendar_email     = ''
        request.user.outlook_calendar_connected = False
        request.user.outlook_calendar_synced_at = None
        request.user.save(update_fields=[
            'outlook_calendar_email', 'outlook_calendar_connected', 'outlook_calendar_synced_at',
        ])
        return Response({'message': 'Outlook Calendar disconnected.'})

class GoogleWebhookView(APIView):
    """
    POST /api/calendar/google/webhook/
    Receives Google Calendar push notifications (RFC 7230 headers).
    When Google reports a calendar change, we queue a sync for that user.

    To register a webhook channel:
      POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/watch
      Body: { "id": "<uuid>", "type": "web_hook", "address": "https://yourdomain.com/api/calendar/google/webhook/" }
    """
    permission_classes = [permissions.AllowAny]   # Google doesn't send auth headers
    serializer_class   = None

    @extend_schema(
        summary="Google Calendar push notification webhook",
        description="Receives change notifications from Google and triggers a calendar sync.",
        responses={200: None},
    )
    def post(self, request):
        # Google sends X-Goog-Channel-ID and X-Goog-Resource-State headers
        channel_id     = request.headers.get('X-Goog-Channel-ID', '')
        resource_state = request.headers.get('X-Goog-Resource-State', '')
        channel_token  = request.headers.get('X-Goog-Channel-Token', '')

        if resource_state == 'sync':
            # Initial handshake — just acknowledge
            return Response(status=200)

        if resource_state not in ('exists', 'not_exists'):
            return Response(status=200)

        # Validate channel token matches a user (we store user_id in token when registering)
        if channel_token:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=int(channel_token), google_calendar_connected=True)
                # Sync asynchronously — in prod use Celery; here we do it inline
                from calendar_sync.google_calendar import sync_events
                sync_events(user)
                logger.info('Google webhook sync triggered for user %s', user.email)
            except (User.DoesNotExist, ValueError):
                logger.warning('Google webhook: unknown channel token %s', channel_token)

        return Response(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# DEVICE CALENDAR (native iOS/Android — events pushed from the app)
# ─────────────────────────────────────────────────────────────────────────────

class DeviceCalendarSyncView(APIView):
    """
    POST /api/calendar/device/sync/

    Receives events read from the device's native calendar (EventKit on iOS,
    CalendarProvider on Android). The mobile app reads events locally and
    pushes them here — no passwords, no OAuth, just OS-level permission.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    @extend_schema(
        summary="Sync device calendar events",
        description="Receives events from the mobile device's native calendar.",
        request=inline_serializer(name='DeviceSyncRequest', fields={
            'events': serializers.ListField(child=serializers.DictField()),
        }),
        responses={200: _sync_schema('DeviceSyncResponse')},
    )
    def post(self, request):
        from itinerary.models import CalendarEvent
        from arokah.services.event_classifier import classify_event

        events = request.data.get('events', [])
        if not isinstance(events, list):
            return Response({'error': 'events must be a list'}, status=400)

        created = 0
        updated = 0
        errors = []

        for ev in events:
            try:
                ext_id = ev.get('external_id', '')
                title = ev.get('title', '(No title)')
                description = ev.get('description', '')
                location = ev.get('location', '')
                start_time = ev.get('start_time')
                end_time = ev.get('end_time')
                all_day = ev.get('all_day', False)
                calendar_name = ev.get('calendar_name', '')

                if not start_time or not end_time:
                    errors.append(f'Missing start/end for: {title}')
                    continue

                classification = classify_event(title, description)

                obj, was_created = CalendarEvent.objects.update_or_create(
                    user=request.user,
                    external_id=ext_id,
                    source='device',
                    defaults={
                        'title': title[:500],
                        'description': description,
                        'location': location[:500],
                        'start_time': start_time,
                        'end_time': end_time,
                        'all_day': all_day,
                        'event_type': classification.get('event_type', 'other'),
                        'formality': classification.get('formality', ''),
                        'raw_data': {
                            'calendar_name': calendar_name,
                            'device_sync': True,
                        },
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as exc:
                errors.append(f'{ev.get("title", "?")}: {exc}')

        return Response({
            'created': created,
            'updated': updated,
            'total': created + updated,
            'errors': errors,
        })
