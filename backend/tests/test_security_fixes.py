"""Regression tests for the backend security review fixes."""

import datetime

import pytest
from itinerary.models import Trip
from shared_wardrobe.models import SharedWardrobe, SharedWardrobeMember

from .factories import ClothingItemFactory, UserFactory

pytestmark = pytest.mark.django_db


def login(client, user):
    r = client.post(
        "/api/auth/login/", {"email": user.email, "password": "testpass99"}, content_type="application/json"
    )
    return r.json()  # {access, refresh}


def hdr(tokens):
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}


def make_trip(user, sw=None):
    today = datetime.date.today()
    return Trip.objects.create(
        user=user,
        name="Trip",
        destination="Tokyo, Japan",
        start_date=today,
        end_date=today + datetime.timedelta(days=3),
        shared_wardrobe=sw,
    )


def shared_wardrobe(owner, *members):
    sw = SharedWardrobe.objects.create(name="Fam", created_by=owner)
    SharedWardrobeMember.objects.create(wardrobe=sw, user=owner, role="owner")
    for m in members:
        SharedWardrobeMember.objects.create(wardrobe=sw, user=m, role="editor")
    return sw


class TestTripWriteIDOR:
    """M1 — a shared-wardrobe member may READ the owner's trip but not modify/delete it."""

    def test_member_cannot_modify_or_delete_owners_trip(self, client):
        owner, member = UserFactory(), UserFactory()
        sw = shared_wardrobe(owner, member)
        trip = make_trip(owner, sw)
        m = hdr(login(client, member))

        assert client.get(f"/api/itinerary/trips/{trip.id}/", **m).status_code == 200  # read OK
        assert (
            client.patch(
                f"/api/itinerary/trips/{trip.id}/",
                {"destination": "Hacked"},
                content_type="application/json",
                **m,
            ).status_code
            == 403
        )
        assert client.delete(f"/api/itinerary/trips/{trip.id}/", **m).status_code == 403

        trip.refresh_from_db()
        assert trip.destination == "Tokyo, Japan"


class TestSaveRecommendationLeak:
    """H2 — save-recommendation must not push another user's items into a shared wardrobe."""

    def test_cannot_push_another_users_item(self, client):
        owner, other = UserFactory(), UserFactory()
        sw = shared_wardrobe(owner)
        trip = make_trip(owner, sw)
        secret = ClothingItemFactory(user=other, name="Secret Blazer")

        payload = {
            "days": [{"wardrobe_matches": [{"item": {"id": secret.id, "name": "Secret Blazer"}, "role": "main"}]}]
        }
        r = client.post(
            f"/api/itinerary/trips/{trip.id}/save-recommendation/",
            {"recommendation": payload},
            content_type="application/json",
            **hdr(login(client, owner)),
        )
        assert r.status_code == 200
        assert r.json()["shared_wardrobe_items_added"] == 0
        assert not sw.items.filter(name="Secret Blazer").exists()


class TestPackingChecklistIDOR:
    """M2 — cannot add a checklist item onto another user's trip via a client-supplied FK."""

    def test_cannot_target_another_users_trip(self, client):
        a, b = UserFactory(), UserFactory()
        a_trip = make_trip(a)
        r = client.post(
            "/api/itinerary/checklist/",
            {"trip": a_trip.id, "custom_name": "junk", "quantity": 1},
            content_type="application/json",
            **hdr(login(client, b)),
        )
        assert r.status_code == 403


class TestSessionInvalidation:
    """M4 — a password change blacklists outstanding refresh tokens."""

    def test_password_change_revokes_refresh(self, client):
        user = UserFactory()
        tokens = login(client, user)
        r = client.post(
            "/api/auth/me/password/",
            {"current_password": "testpass99", "new_password": "NewPass1234!"},
            content_type="application/json",
            **hdr(tokens),
        )
        assert r.status_code == 200
        # The refresh token issued at login must now be rejected.
        rr = client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, content_type="application/json")
        assert rr.status_code == 401


class TestAntiEnumeration:
    """M6 — unknown-email responses don't reveal account existence."""

    def test_verify_email_unknown_is_generic(self, client):
        r = client.post(
            "/api/auth/verify-email/",
            {"email": "nobody@nowhere.test", "token": "x"},
            content_type="application/json",
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "invalid_token"

    def test_reset_password_unknown_is_generic(self, client):
        r = client.post(
            "/api/auth/reset-password/",
            {"email": "nobody@nowhere.test", "token": "x", "new_password": "NewPass1234!"},
            content_type="application/json",
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "invalid_token"

    def test_forgot_password_unknown_still_200(self, client):
        r = client.post(
            "/api/auth/forgot-password/",
            {"email": "nobody@nowhere.test"},
            content_type="application/json",
        )
        assert r.status_code == 200
