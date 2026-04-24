"""
Push notification service using Firebase Admin SDK (FCM v1 API).

Authentication (in priority order):
  1. GOOGLE_APPLICATION_CREDENTIALS env var pointing to a service account JSON
  2. gcloud auth application-default login (local dev)
  3. Cloud provider metadata (GCE, Cloud Run, etc.) — works automatically in prod

No file paths or API keys needed in code.
"""
import logging

logger = logging.getLogger('ritha.notifications')

_firebase_app = None


def _init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return True
    try:
        import firebase_admin

        _firebase_app = firebase_admin.initialize_app()
        logger.info('Firebase Admin SDK initialised (project: %s)', _firebase_app.project_id)
        return True
    except Exception as exc:
        logger.error('Firebase init failed: %s', exc)
        return False


def send_push(user, *, title: str, body: str, data: dict | None = None) -> dict:
    """
    Send a push notification to a single user via FCM v1 API.

    Returns dict with keys: status ('sent'|'stub'|'error'), message
    """
    device_token = getattr(user, 'device_push_token', '')

    if not device_token:
        return {
            'status': 'stub',
            'message': 'No device token registered for this user.',
        }

    if not _init_firebase():
        return {
            'status': 'stub',
            'message': 'Firebase not configured. Run: gcloud auth application-default login',
        }

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=device_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(sound='default'),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default', badge=1),
                ),
            ),
        )

        resp = messaging.send(message)
        logger.info('Push sent to %s — message_id=%s', user.email, resp)
        return {'status': 'sent', 'message_id': resp}

    except Exception as exc:
        logger.error('Push failed for %s: %s', user.email, exc)
        return {'status': 'error', 'message': str(exc)}


def send_daily_look_notification(user, recommendation) -> dict:
    """Send a morning "Today's Look" push notification."""
    item_count = recommendation.outfititem_set.count()
    return send_push(
        user,
        title="Today's Look is ready",
        body=(
            f"{recommendation.notes or 'Your outfit for today is ready.'} "
            f"({item_count} item{'s' if item_count != 1 else ''})"
        ),
        data={
            'type': 'daily_look',
            'recommendation_id': str(recommendation.id),
            'date': str(recommendation.date),
        },
    )
