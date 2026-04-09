"""
Push notification scaffold
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger('arokah.notifications')


def send_daily_look_notification(user, recommendation) -> dict:
    """
    Send a morning "Today's Look" push notification to a user.

    Args:
        user: auth_app.User instance
        recommendation: outfits.OutfitRecommendation instance

    Returns:
        dict with keys: status ('sent'|'stub'|'error'), message
    """
    fcm_key = getattr(settings, 'FIREBASE_SERVER_KEY', '')
    device_token = getattr(user, 'device_push_token', '')

    if not fcm_key or not device_token:
        logger.debug(
            'Push notification stub for %s — rec #%s. '
            'Set FIREBASE_SERVER_KEY and user.device_push_token to activate.',
            user.email, recommendation.id
        )
        return {
            'status':  'stub',
            'message': 'Push notifications not configured.',
            'user':    user.email,
            'rec_id':  recommendation.id,
        }

    # ── Live FCM path (activate with FIREBASE_SERVER_KEY in .env) ──────────
    try:
        item_count = recommendation.outfititem_set.count()
        payload = {
            'to': device_token,
            'notification': {
                'title': "Today's Look is ready ✨",
                'body':  (
                    f"{recommendation.notes or 'Your outfit for today is ready.'} "
                    f"({item_count} item{'s' if item_count != 1 else ''})"
                ),
                'sound': 'default',
            },
            'data': {
                'type':           'daily_look',
                'recommendation_id': str(recommendation.id),
                'date':           str(recommendation.date),
            },
        }
        resp = requests.post(
            'https://fcm.googleapis.com/fcm/send',
            json=payload,
            headers={
                'Authorization': f'key={fcm_key}',
                'Content-Type':  'application/json',
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info('Push sent to %s — rec #%s', user.email, recommendation.id)
        return {'status': 'sent', 'fcm_response': resp.json()}

    except Exception as exc:
        logger.error('Push failed for %s: %s', user.email, exc)
        return {'status': 'error', 'message': str(exc)}
