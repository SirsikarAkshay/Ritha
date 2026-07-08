import pytest
from agents.models import AgentJob

from .factories import CalendarEventFactory, ClothingItemFactory, UserFactory

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post(
        "/api/auth/login/", {"email": user.email, "password": "testpass99"}, content_type="application/json"
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {r.json()['access']}"}


class TestDailyLookAgent:
    def test_daily_look_no_wardrobe(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/daily-look/",
            {"weather": {"temp_c": 18, "precipitation_probability": 10}},
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert data["output"]["status"] == "no_wardrobe"

    def test_daily_look_with_wardrobe(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name="White Tee")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/daily-look/",
            {"weather": {"temp_c": 20, "precipitation_probability": 5}},
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        # Stub mode — OpenAI key not real
        assert data["output"]["status"] in ("stub", "no_wardrobe", "ai")
        assert "item_ids" in data["output"] or "message" in data["output"]

    def test_daily_look_creates_agent_job(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        client.post("/api/agents/daily-look/", {}, content_type="application/json", **h)
        assert AgentJob.objects.filter(user=user, agent_type="daily_look").exists()

    def test_daily_look_unauthenticated(self, client):
        r = client.post("/api/agents/daily-look/", {}, content_type="application/json")
        assert r.status_code == 401


class TestConflictDetector:
    def test_no_conflicts_clear_weather(self, client):
        user = UserFactory()
        CalendarEventFactory(user=user, event_type="workout")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/conflict-detector/",
            {
                "date": "2026-03-14",
                "weather": {"precipitation_probability": 10},
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        assert r.json()["output"]["conflicts"] == []

    def test_rain_conflict_with_workout(self, client):
        user = UserFactory()
        CalendarEventFactory(user=user, event_type="workout")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/conflict-detector/",
            {
                "date": "2026-03-14",
                "weather": {"precipitation_probability": 85},
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        conflicts = r.json()["output"]["conflicts"]
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "weather_activity"
        assert conflicts[0]["severity"] == "warning"

    def test_events_counted(self, client):
        user = UserFactory()
        CalendarEventFactory(user=user, event_type="internal_meeting")
        CalendarEventFactory(user=user, event_type="social")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/conflict-detector/",
            {"date": "2026-03-14", "weather": {}},
            content_type="application/json",
            **h,
        )
        assert r.json()["output"]["events_checked"] == 2


class TestCulturalAdvisor:
    def test_returns_rules(self, client):
        from cultural.models import CulturalRule

        CulturalRule.objects.create(
            country="Turkey",
            city="Istanbul",
            rule_type="cover_head",
            description="Headscarf required",
            severity="required",
        )
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/cultural-advisor/",
            {
                "country": "Turkey",
                "city": "Istanbul",
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        output = r.json()["output"]
        assert output["country"] == "Turkey"
        assert len(output["rules"]) == 1
        assert output["rules"][0]["rule_type"] == "cover_head"

    def test_returns_local_events(self, client):
        from cultural.models import LocalEvent

        LocalEvent.objects.create(
            country="India",
            name="Holi",
            description="Festival of colours",
            clothing_note="Pack clothes you don't mind staining",
            start_month=3,
            end_month=3,
        )
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/cultural-advisor/",
            {
                "country": "India",
                "month": 3,  # Holi is a March event; advisor filters by month
            },
            content_type="application/json",
            **h,
        )
        output = r.json()["output"]
        assert any(e["name"] == "Holi" for e in output["local_events"])

    def test_unknown_country_returns_empty(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/cultural-advisor/",
            {
                "country": "Narnia",
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        output = r.json()["output"]
        assert output["rules"] == []
        assert output["local_events"] == []


class TestPackingList:
    def test_packing_list_stub(self, client):
        user = UserFactory()
        for name in ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress"]:
            ClothingItemFactory(user=user, name=name)
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/packing-list/",
            {
                "days": 5,
                "activities": ["beach", "sightseeing", "dinner"],
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        output = r.json()["output"]
        assert "packing_list" in output
        assert isinstance(output["packing_list"], list)

    def test_packing_list_respects_bag_capacity(self, client):
        user = UserFactory()
        for cat, n in [("top", 5), ("bottom", 4), ("outerwear", 3), ("footwear", 2)]:
            for _ in range(n):
                ClothingItemFactory(user=user, category=cat)
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/packing-list/",
            {"days": 14, "location": "Europe", "bag_capacity_liters": 12},
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        output = r.json()["output"]
        # Capacity is respected and reported.
        assert output["bag_capacity_liters"] == 12
        assert output["estimated_volume_liters"] <= 12
        assert output["capacity_utilization_pct"] is not None
        # Every packed item carries its estimated volume.
        assert all("packed_volume_liters" in i for i in output["packing_list"])
        # A 12L bag can't hold the whole ~30L capsule, so some items are left behind.
        assert len(output["left_behind"]) > 0
        # Human-readable headline uses the week phrasing.
        assert output["headline"] == "How to pack for 2 weeks in Europe in a 12L bag"

    def test_packing_list_bag_type_preset_maps_to_liters(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, category="top")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/packing-list/",
            {"days": 3, "bag_type": "backpack"},
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        assert r.json()["output"]["bag_capacity_liters"] == 30


_MOCK_WEATHER = {
    "temp_c": 20,
    "feels_like_c": 20,
    "condition": "Clear",
    "is_raining": False,
    "is_cold": False,
    "is_hot": False,
    "is_windy": False,
}


class TestPlaceOutfit:
    def test_place_outfit_returns_matches_with_image_url(self, client):
        user = UserFactory()
        for cat in ["top", "bottom", "footwear", "outerwear"]:
            ClothingItemFactory(user=user, category=cat)
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/place-outfit/",
            {
                "place": "Blue Mosque",
                "destination": "Istanbul",
                "place_type": "religious",
                "formality": "smart",
                "clothing_tip": "Cover shoulders and knees.",
                "weather": _MOCK_WEATHER,
            },
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        output = r.json()["output"]
        assert output["place"] == "Blue Mosque"
        # A religious site maps to the modest 'cultural_visit' occasion.
        assert output["occasion"] == "cultural_visit"
        assert isinstance(output["wardrobe_matches"], list)
        # Every matched item exposes image_url so the UI can render a photo
        # (empty here -> the UI falls back to the category illustration).
        for m in output["wardrobe_matches"]:
            assert "image_url" in m["item"]

    def test_place_outfit_formality_maps_to_occasion(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, category="top")
        h = auth_header(client, user)
        r = client.post(
            "/api/agents/place-outfit/",
            {"place": "Rooftop Bar", "destination": "Singapore", "formality": "smart", "weather": _MOCK_WEATHER},
            content_type="application/json",
            **h,
        )
        assert r.status_code == 200
        assert r.json()["output"]["occasion"] == "business"
