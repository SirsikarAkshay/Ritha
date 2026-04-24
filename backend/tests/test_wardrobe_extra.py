"""Tests for background-removal, receipt-import, and luggage-weight endpoints."""
import pytest
from .factories import UserFactory, ClothingItemFactory
from io import BytesIO
from PIL import Image

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestBackgroundRemoval:
    def _make_image(self):
        img = Image.new('RGB', (100, 100), color='red')
        buf = BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        buf.name = 'shirt.jpg'
        return buf

    def test_no_image_returns_400(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/background-removal/', {}, **h)
        assert r.status_code == 400

    def test_image_upload_returns_stub(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        img = self._make_image()
        r = client.post('/api/wardrobe/background-removal/',
                        {'image': img}, format='multipart', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'stub'
        assert 'original_filename' in r.json()


class TestReceiptImport:
    def test_missing_email_body_returns_400(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/receipt-import/', {},
                        content_type='application/json', **h)
        assert r.status_code == 400

    def test_without_openai_key_returns_stub(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/receipt-import/',
                        {'email_body': 'Your order: 1x Blue Denim Jacket - £49.99'},
                        content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['status'] == 'stub'
        assert r.json()['items_created'] == 0


class TestLuggageWeight:
    def test_no_items_returns_400(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/luggage-weight/', {'item_ids': []},
                        content_type='application/json', **h)
        assert r.status_code == 400

    def test_weight_calculated(self, client):
        user  = UserFactory()
        item1 = ClothingItemFactory(user=user, category='top',     weight_grams=250)
        item2 = ClothingItemFactory(user=user, category='bottom',  weight_grams=400)
        item3 = ClothingItemFactory(user=user, category='footwear',weight_grams=600)
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/luggage-weight/',
                        {'item_ids': [item1.id, item2.id, item3.id]},
                        content_type='application/json', **h)
        assert r.status_code == 200
        data = r.json()
        assert data['total_grams'] == 1250
        assert data['total_kg']    == 1.25
        assert data['fits_carry_on'] is True

    def test_estimated_weight_used_when_null(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user, category='outerwear', weight_grams=None)
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/luggage-weight/',
                        {'item_ids': [item.id]},
                        content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['items'][0]['estimated'] is True
        assert r.json()['items'][0]['weight_grams'] == 800  # category default for outerwear

    def test_carry_on_limit_exceeded(self, client):
        user  = UserFactory()
        heavy = [ClothingItemFactory(user=user, category='outerwear', weight_grams=2000)
                 for _ in range(6)]  # 12 kg total
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/luggage-weight/',
                        {'item_ids': [i.id for i in heavy], 'airline': 'ryanair'},
                        content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['fits_carry_on'] is False

    def test_co2_saving_calculated(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user, category='top', weight_grams=300)
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/luggage-weight/', {'item_ids': [item.id]},
                        content_type='application/json', **h)
        assert r.json()['co2_saved_vs_checked_kg'] > 0

    def test_cannot_weigh_other_users_items(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        item   = ClothingItemFactory(user=user_b, weight_grams=300)
        h = auth_header(client, user_a)
        r = client.post('/api/wardrobe/luggage-weight/', {'item_ids': [item.id]},
                        content_type='application/json', **h)
        # Item not found for user_a → 400
        assert r.status_code == 400


class TestReceiptImportLivePath:
    """Test the OpenAI live path for receipt import (mocked)."""

    def test_live_path_creates_items(self, client, settings):
        from unittest.mock import patch
        user = UserFactory()
        h = auth_header(client, user)

        # Activate live path by setting a real-looking key
        settings.MISTRAL_API_KEY = 'test-key-live'

        with patch('ritha.services.mistral_client.chat_json',
                   return_value={'items': [
                       {'name': 'Blue Denim Jacket', 'category': 'outerwear',
                        'colors': ['blue'], 'brand': "Levi's", 'material': 'denim'},
                       {'name': 'White T-Shirt', 'category': 'top',
                        'colors': ['white'], 'brand': '', 'material': 'cotton'},
                   ]}):
            r = client.post('/api/wardrobe/receipt-import/',
                            {'email_body': 'Order confirmed: 1x Blue Denim Jacket, 1x White T-Shirt'},
                            content_type='application/json', **h)

        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'success'
        assert data['items_created'] == 2
        names = [i['name'] for i in data['items']]
        assert 'Blue Denim Jacket' in names

    def test_live_path_items_saved_to_wardrobe(self, client, settings):
        from unittest.mock import patch
        from wardrobe.models import ClothingItem
        user = UserFactory()
        h = auth_header(client, user)

        settings.MISTRAL_API_KEY = 'test-mistral-key'

        with patch('ritha.services.mistral_client.chat_json',
                   return_value={'items': [
                       {'name': 'Silk Blouse', 'category': 'top',
                        'colors': ['white'], 'brand': 'Zara', 'material': 'silk'},
                   ]}):
            client.post('/api/wardrobe/receipt-import/',
                        {'email_body': 'Your order: 1x Silk Blouse'},
                        content_type='application/json', **h)

        assert ClothingItem.objects.filter(user=user, name='Silk Blouse').exists()
        item = ClothingItem.objects.get(user=user, name='Silk Blouse')
        assert item.category == 'top'
        assert item.material == 'silk'
