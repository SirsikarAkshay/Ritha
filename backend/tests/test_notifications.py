"""Tests for the push notification service (Firebase Admin SDK / FCM v1)."""

import datetime
from unittest.mock import patch

import pytest
from outfits.models import OutfitItem, OutfitRecommendation
from outfits.notifications import send_daily_look_notification

from .factories import ClothingItemFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestPushNotifications:
    def _make_recommendation(self, user):
        item = ClothingItemFactory(user=user)
        rec = OutfitRecommendation.objects.create(
            user=user, date=datetime.date.today(), source="daily", notes="A great outfit for today"
        )
        OutfitItem.objects.create(outfit=rec, clothing_item=item, role="main")
        return rec

    def test_stub_when_no_device_token(self):
        """No registered device token → stub, no send attempted."""
        user = UserFactory()
        user.device_push_token = ""
        rec = self._make_recommendation(user)
        result = send_daily_look_notification(user, rec)
        assert result["status"] == "stub"
        assert "no device token" in result["message"].lower()

    @patch("outfits.notifications._init_firebase", return_value=False)
    def test_stub_when_firebase_not_configured(self, _mock_init):
        """Device token present but Firebase isn't initialised → stub."""
        user = UserFactory()
        user.device_push_token = "fake-device-token-abc123"
        rec = self._make_recommendation(user)
        result = send_daily_look_notification(user, rec)
        assert result["status"] == "stub"
        assert "not configured" in result["message"].lower()

    # create=True: send_push imports `firebase_admin.messaging` lazily, so the
    # attribute may not exist on the package yet when patching starts.
    @patch("firebase_admin.messaging", create=True)
    @patch("outfits.notifications._init_firebase", return_value=True)
    def test_sent_when_firebase_ok(self, _mock_init, mock_messaging):
        """Token + initialised Firebase → message sent, message_id returned."""
        user = UserFactory()
        user.device_push_token = "fake-device-token-abc123"
        rec = self._make_recommendation(user)

        mock_messaging.send.return_value = "projects/ritha/messages/123"
        result = send_daily_look_notification(user, rec)

        assert result["status"] == "sent"
        assert result["message_id"] == "projects/ritha/messages/123"
        mock_messaging.send.assert_called_once()

    @patch("firebase_admin.messaging", create=True)
    @patch("outfits.notifications._init_firebase", return_value=True)
    def test_send_error_returns_error_status(self, _mock_init, mock_messaging):
        """An exception from messaging.send is captured as status 'error'."""
        user = UserFactory()
        user.device_push_token = "fake-token"
        rec = self._make_recommendation(user)

        mock_messaging.send.side_effect = RuntimeError("FCM unavailable")
        result = send_daily_look_notification(user, rec)

        assert result["status"] == "error"
        assert "FCM unavailable" in result["message"]
