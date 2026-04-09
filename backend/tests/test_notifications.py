"""Tests for push notification scaffold."""
import pytest
import datetime
from unittest.mock import patch, MagicMock
from .factories import UserFactory, ClothingItemFactory
from outfits.models import OutfitRecommendation, OutfitItem
from outfits.notifications import send_daily_look_notification

pytestmark = pytest.mark.django_db


class TestPushNotifications:
    def _make_recommendation(self, user):
        item = ClothingItemFactory(user=user)
        rec  = OutfitRecommendation.objects.create(
            user=user, date=datetime.date.today(), source='daily',
            notes='A great outfit for today'
        )
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role='main')
        return rec

    def test_stub_when_no_key(self):
        user = UserFactory()
        rec  = self._make_recommendation(user)
        result = send_daily_look_notification(user, rec)
        assert result['status'] == 'stub'
        assert 'not configured' in result['message'].lower()

    def test_stub_includes_user_and_rec_id(self):
        user = UserFactory()
        rec  = self._make_recommendation(user)
        result = send_daily_look_notification(user, rec)
        assert result['user'] == user.email
        assert result['rec_id'] == rec.id

    @patch('outfits.notifications.requests.post')
    def test_live_fcm_send(self, mock_post, settings):
        """With a key + device token, a real FCM POST is made."""
        user = UserFactory()
        user.device_push_token = 'fake-device-token-abc123'
        rec  = self._make_recommendation(user)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {'results': [{'message_id': '123'}]}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        settings.FIREBASE_SERVER_KEY = 'fake-fcm-key'
        result = send_daily_look_notification(user, rec)

        assert result['status'] == 'sent'
        mock_post.assert_called_once()
        assert 'fcm.googleapis.com' in mock_post.call_args[0][0]

    @patch('outfits.notifications.requests.post')
    def test_network_error_returns_error_status(self, mock_post, settings):
        import requests as req_lib
        user = UserFactory()
        user.device_push_token = 'fake-token'
        rec  = self._make_recommendation(user)
        mock_post.side_effect = req_lib.RequestException('timeout')

        settings.FIREBASE_SERVER_KEY = 'fake-key'
        result = send_daily_look_notification(user, rec)

        assert result['status'] == 'error'
        assert 'timeout' in result['message']
