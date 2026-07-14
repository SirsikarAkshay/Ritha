"""Tests for the "Remind me to buy this later" saved shopping list."""

import datetime

import pytest
from itinerary.models import SavedShoppingItem, Trip

from .factories import UserFactory

pytestmark = pytest.mark.django_db

LIST_URL = "/api/itinerary/shopping-list/"


def login(client, user):
    r = client.post(
        "/api/auth/login/", {"email": user.email, "password": "testpass99"}, content_type="application/json"
    )
    return r.json()


def hdr(tokens):
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}


def results(resp):
    """Unwrap DRF's paginated list response."""
    data = resp.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


def make_trip(user):
    today = datetime.date.today()
    return Trip.objects.create(user=user, name="Trip", destination="Tokyo, Japan", start_date=today, end_date=today)


SUGGESTION = {
    "name": "Wool overcoat",
    "brand": "Uniqlo",
    "description": "A real coat for 8°C evenings.",
    "price_range": "₹6,000",
    "role": "outerwear",
    "category": "outerwear",
    "why": "No cold-weather layers in your wardrobe.",
    "links": {"google_shopping": "https://www.google.com/search?tbm=shop&q=wool+overcoat"},
}


class TestSaveAndList:
    def test_save_then_list_is_user_scoped(self, client):
        owner, other = UserFactory(), UserFactory()
        trip = make_trip(owner)
        m = hdr(login(client, owner))

        r = client.post(LIST_URL, {**SUGGESTION, "trip": trip.id}, content_type="application/json", **m)
        assert r.status_code == 201
        assert r.json()["name"] == "Wool overcoat"
        assert r.json()["purchased"] is False

        # owner sees it
        assert len(results(client.get(LIST_URL, **m))) == 1
        # a different user sees nothing
        assert results(client.get(LIST_URL, **hdr(login(client, other)))) == []

    def test_save_without_trip_is_allowed(self, client):
        user = UserFactory()
        r = client.post(LIST_URL, SUGGESTION, content_type="application/json", **hdr(login(client, user)))
        assert r.status_code == 201
        assert r.json()["trip"] is None

    def test_filter_by_trip_id(self, client):
        user = UserFactory()
        m = hdr(login(client, user))
        t1, t2 = make_trip(user), make_trip(user)
        client.post(LIST_URL, {**SUGGESTION, "trip": t1.id}, content_type="application/json", **m)
        client.post(LIST_URL, {**SUGGESTION, "trip": t2.id}, content_type="application/json", **m)
        assert len(results(client.get(f"{LIST_URL}?trip_id={t1.id}", **m))) == 1


class TestOwnership:
    def test_cannot_save_to_another_users_trip(self, client):
        a, b = UserFactory(), UserFactory()
        a_trip = make_trip(a)
        r = client.post(
            LIST_URL, {**SUGGESTION, "trip": a_trip.id}, content_type="application/json", **hdr(login(client, b))
        )
        assert r.status_code == 403


class TestMutations:
    def test_mark_purchased_and_delete(self, client):
        user = UserFactory()
        m = hdr(login(client, user))
        created = client.post(LIST_URL, SUGGESTION, content_type="application/json", **m).json()
        item_id = created["id"]

        patched = client.patch(f"{LIST_URL}{item_id}/", {"purchased": True}, content_type="application/json", **m)
        assert patched.status_code == 200
        assert patched.json()["purchased"] is True

        deleted = client.delete(f"{LIST_URL}{item_id}/", **m)
        assert deleted.status_code == 204
        assert not SavedShoppingItem.objects.filter(id=item_id).exists()

    def test_cannot_delete_another_users_item(self, client):
        a, b = UserFactory(), UserFactory()
        created = client.post(LIST_URL, SUGGESTION, content_type="application/json", **hdr(login(client, a))).json()
        # b cannot see or delete a's item (get_queryset is user-scoped → 404)
        resp = client.delete(f"{LIST_URL}{created['id']}/", **hdr(login(client, b)))
        assert resp.status_code == 404
        assert SavedShoppingItem.objects.filter(id=created["id"]).exists()
