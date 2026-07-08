"""Region-aware starter wardrobe: North/South India packs + real CC0 photos.

Images are redirected to a tmp dir (never the repo), and the Openverse fetch is
mocked so nothing touches the network.
"""

import io

import pytest
from django.core.management import call_command
from PIL import Image
from wardrobe.models import ClothingItem, StarterPackItem

from .factories import UserFactory

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post(
        "/api/auth/login/", {"email": user.email, "password": "testpass99"}, content_type="application/json"
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {r.json()['access']}"}


@pytest.fixture
def seed_env(settings, tmp_path, monkeypatch):
    """Point media + the seed-image cache at tmp dirs so tests never touch the repo."""
    media = tmp_path / "media"
    media.mkdir()
    settings.MEDIA_ROOT = str(media)
    seed_dir = tmp_path / "seed_images"
    monkeypatch.setattr("wardrobe.images.SEED_IMAGES_DIR", seed_dir)
    monkeypatch.setattr("wardrobe.management.commands.fetch_starter_images.SEED_IMAGES_DIR", seed_dir)
    monkeypatch.setattr("wardrobe.management.commands.fetch_starter_images.CREDITS_PATH", seed_dir / "CREDITS.json")
    return seed_dir


def _write_seed_img(seed_dir, region, gender, subcategory):
    d = seed_dir / region / gender
    d.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (48, 60), (60, 80, 160)).save(d / f"{subcategory}.jpg", "JPEG")


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 120, 60)).save(buf, "PNG")
    return buf.getvalue()


class TestPackData:
    def test_seed_creates_north_region_with_winter_contrast(self, seed_env):
        call_command("seed_starter_packs", verbosity=0)
        north = set(
            StarterPackItem.objects.filter(region_cluster__code="south_asian_north", gender="women").values_list(
                "subcategory", flat=True
            )
        )
        south = set(
            StarterPackItem.objects.filter(region_cluster__code="south_asian_tropical", gender="women").values_list(
                "subcategory", flat=True
            )
        )
        assert north and south
        # North India's real winter → layering items the tropical south doesn't default to.
        assert {"sweater-wool", "coat-wool"} <= north
        assert "sweater-wool" not in south

    def test_seed_idempotent(self, seed_env):
        call_command("seed_starter_packs", verbosity=0)
        n1 = StarterPackItem.objects.count()
        call_command("seed_starter_packs", verbosity=0)
        assert StarterPackItem.objects.count() == n1


class TestPreviewImages:
    def test_photo_when_cached_else_illustration(self, seed_env):
        call_command("seed_starter_packs", verbosity=0)
        _write_seed_img(seed_env, "south_asian_north", "women", "kurta")
        call_command("seed_starter_packs", verbosity=0)

        kurta = StarterPackItem.objects.get(
            region_cluster__code="south_asian_north", gender="women", subcategory="kurta"
        )
        tee = StarterPackItem.objects.get(
            region_cluster__code="south_asian_north", gender="women", subcategory="tshirt-cotton"
        )
        assert kurta.preview_image_url.endswith(".jpg") and "starter/" in kurta.preview_image_url
        assert tee.preview_image_url.endswith(".svg")  # no cached photo → category illustration


class TestApply:
    def _apply(self, client, seed_env, cache_kurta):
        call_command("seed_starter_packs", verbosity=0)
        if cache_kurta:
            _write_seed_img(seed_env, "south_asian_north", "women", "kurta")
            call_command("seed_starter_packs", verbosity=0)
        user = UserFactory()
        ids = list(
            StarterPackItem.objects.filter(
                region_cluster__code="south_asian_north", gender="women", is_default=True
            ).values_list("id", flat=True)
        )
        r = client.post(
            "/api/wardrobe/starter-pack/apply/",
            {"region_code": "south_asian_north", "gender": "women", "accepted_ids": ids},
            content_type="application/json",
            **auth_header(client, user),
        )
        assert r.status_code == 201, r.content
        return user

    def test_apply_attaches_cached_photo(self, client, seed_env):
        user = self._apply(client, seed_env, cache_kurta=True)
        kurta = ClothingItem.objects.get(user=user, name="Kurta (long tunic)")
        assert kurta.image, "cached region photo should be attached to the applied item"

    def test_apply_without_cache_leaves_no_image(self, client, seed_env):
        user = self._apply(client, seed_env, cache_kurta=False)
        items = ClothingItem.objects.filter(user=user, source="starter_pack")
        assert items.exists()
        assert all(not it.image for it in items)  # falls back to the illustration in the UI


class TestFetchCommand:
    def test_fetch_starter_images_mocked(self, seed_env, monkeypatch):
        from wardrobe.management.commands.fetch_starter_images import Command as FetchCmd

        hit = {
            "url": "http://example.test/i.png",
            "license": "cc0",
            "title": "t",
            "creator": "c",
            "license_url": "u",
            "source": "s",
            "foreign_landing_url": "f",
        }
        monkeypatch.setattr(FetchCmd, "_search", lambda self, q: hit)
        monkeypatch.setattr(FetchCmd, "_download", lambda self, url: _png_bytes())

        call_command("fetch_starter_images", region="south_asian_north", gender="men", limit=2, sleep=0, verbosity=0)
        men_dir = seed_env / "south_asian_north" / "men"
        assert len(list(men_dir.glob("*.jpg"))) == 2
        assert (seed_env / "CREDITS.json").exists()

    def test_fetch_no_result_is_graceful(self, seed_env, monkeypatch):
        from wardrobe.management.commands.fetch_starter_images import Command as FetchCmd

        monkeypatch.setattr(FetchCmd, "_search", lambda self, q: None)
        # No results → no crash, no files written.
        call_command("fetch_starter_images", region="south_asian_north", gender="men", limit=1, sleep=0, verbosity=0)
        assert not (seed_env / "south_asian_north" / "men").exists()


class TestDemoUser:
    def test_region_demo_populates_wardrobe_with_photos(self, seed_env):
        call_command("seed_starter_packs", verbosity=0)
        _write_seed_img(seed_env, "south_asian_north", "women", "kurta")
        call_command("seed_starter_packs", verbosity=0)
        call_command(
            "seed_demo_user",
            region="south_asian_north",
            gender="women",
            email="demo-north@test.local",
            verbosity=0,
        )
        from django.contrib.auth import get_user_model

        demo = get_user_model().objects.get(email="demo-north@test.local")
        wardrobe = list(demo.wardrobe.all())
        assert len(wardrobe) >= 10
        assert any(w.image for w in wardrobe)  # the cached kurta photo was attached
