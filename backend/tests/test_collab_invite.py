"""Phase 1 — trip/shared-wardrobe invite links + join by link."""

import datetime

import pytest
from itinerary.models import Trip
from shared_wardrobe.models import MemberRole, SharedWardrobe, SharedWardrobeMember

from .factories import UserFactory

pytestmark = pytest.mark.django_db


def login(client, user):
    r = client.post(
        "/api/auth/login/", {"email": user.email, "password": "testpass99"}, content_type="application/json"
    )
    return r.json()


def hdr(tokens):
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}


def wardrobe_with_owner(owner):
    sw = SharedWardrobe.objects.create(name="Tokyo crew", created_by=owner)
    SharedWardrobeMember.objects.create(wardrobe=sw, user=owner, role=MemberRole.OWNER)
    return sw


def make_trip(user, sw=None):
    today = datetime.date.today()
    return Trip.objects.create(
        user=user,
        name="Tokyo 2027",
        destination="Tokyo, Japan",
        start_date=today,
        end_date=today + datetime.timedelta(days=3),
        shared_wardrobe=sw,
    )


class TestInviteLink:
    def test_member_gets_token_and_stranger_joins(self, client):
        owner, friend = UserFactory(), UserFactory()
        sw = wardrobe_with_owner(owner)

        r = client.post(f"/api/shared-wardrobes/{sw.id}/invite-link/", **hdr(login(client, owner)))
        assert r.status_code == 200
        token = r.json()["token"]
        assert token and r.json()["join_path"] == f"/join/{token}"

        # A user not connected to the owner can still join via the link.
        j = client.post(
            "/api/shared-wardrobes/join/",
            {"token": token},
            content_type="application/json",
            **hdr(login(client, friend)),
        )
        assert j.status_code == 200
        assert j.json()["status"] == "joined"
        assert sw.members.filter(user=friend, role=MemberRole.EDITOR).exists()

    def test_token_is_stable_across_calls(self, client):
        owner = UserFactory()
        sw = wardrobe_with_owner(owner)
        m = hdr(login(client, owner))
        t1 = client.post(f"/api/shared-wardrobes/{sw.id}/invite-link/", **m).json()["token"]
        t2 = client.post(f"/api/shared-wardrobes/{sw.id}/invite-link/", **m).json()["token"]
        assert t1 == t2

    def test_non_member_cannot_get_link(self, client):
        owner, stranger = UserFactory(), UserFactory()
        sw = wardrobe_with_owner(owner)
        r = client.post(f"/api/shared-wardrobes/{sw.id}/invite-link/", **hdr(login(client, stranger)))
        assert r.status_code == 403

    def test_invalid_token_join_is_404(self, client):
        r = client.post(
            "/api/shared-wardrobes/join/",
            {"token": "nope"},
            content_type="application/json",
            **hdr(login(client, UserFactory())),
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "invalid_token"

    def test_rejoin_is_idempotent(self, client):
        owner, friend = UserFactory(), UserFactory()
        sw = wardrobe_with_owner(owner)
        token = client.post(f"/api/shared-wardrobes/{sw.id}/invite-link/", **hdr(login(client, owner))).json()["token"]
        f = hdr(login(client, friend))
        client.post("/api/shared-wardrobes/join/", {"token": token}, content_type="application/json", **f)
        again = client.post("/api/shared-wardrobes/join/", {"token": token}, content_type="application/json", **f)
        assert again.status_code == 200
        assert again.json()["already_member"] is True
        assert sw.members.filter(user=friend).count() == 1


class TestTripShare:
    def test_share_creates_wardrobe_and_friend_joins_and_sees_trip(self, client):
        owner, friend = UserFactory(), UserFactory()
        trip = make_trip(owner)  # no shared wardrobe yet
        o = hdr(login(client, owner))

        s = client.post(f"/api/itinerary/trips/{trip.id}/share/", **o)
        assert s.status_code == 200
        token = s.json()["token"]
        assert s.json()["wardrobe_id"]

        trip.refresh_from_db()
        assert trip.shared_wardrobe_id == s.json()["wardrobe_id"]

        # Friend joins via the trip's link, then the shared trip shows up for them.
        f = hdr(login(client, friend))
        client.post("/api/shared-wardrobes/join/", {"token": token}, content_type="application/json", **f)
        listing = client.get("/api/itinerary/trips/", **f).json()
        trips = listing["results"] if isinstance(listing, dict) and "results" in listing else listing
        assert any(t["id"] == trip.id for t in trips)

    def test_only_owner_can_share(self, client):
        owner, other = UserFactory(), UserFactory()
        trip = make_trip(owner)
        r = client.post(f"/api/itinerary/trips/{trip.id}/share/", **hdr(login(client, other)))
        assert r.status_code in (403, 404)  # not owner → forbidden or not visible


class TestMemberWardrobeCount:
    def test_member_list_exposes_personal_item_count(self, client):
        from tests.factories import ClothingItemFactory

        owner = UserFactory()
        sw = wardrobe_with_owner(owner)
        ClothingItemFactory(user=owner)
        ClothingItemFactory(user=owner)
        detail = client.get(f"/api/shared-wardrobes/{sw.id}/", **hdr(login(client, owner))).json()
        me = next(m for m in detail["members"] if m["user"]["id"] == owner.id)
        assert me["wardrobe_item_count"] == 2
