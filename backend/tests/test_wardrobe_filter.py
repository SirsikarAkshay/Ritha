"""Tests for wardrobe filtering, search, and soft-delete."""
import pytest
from .factories import UserFactory, ClothingItemFactory

pytestmark = pytest.mark.django_db


def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestWardrobeFilters:
    def test_filter_by_category(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Blazer',   category='outerwear')
        ClothingItemFactory(user=user, name='T-Shirt',  category='top')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?category=outerwear', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert results[0]['name'] == 'Blazer'

    def test_filter_by_formality(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Suit',      formality='formal')
        ClothingItemFactory(user=user, name='Jeans',     formality='casual')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?formality=formal', **h)
        assert len(r.json()['results']) == 1

    def test_filter_by_season(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Winter Coat', season='winter')
        ClothingItemFactory(user=user, name='Basic Tee',   season='all')
        ClothingItemFactory(user=user, name='Flip Flops',  season='summer')
        h = auth(client, user)
        # ?season=winter should return winter + all
        r = client.get('/api/wardrobe/items/?season=winter', **h)
        names = {i['name'] for i in r.json()['results']}
        assert 'Winter Coat' in names
        assert 'Basic Tee'   in names
        assert 'Flip Flops'  not in names

    def test_search_by_name(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Navy Blazer')
        ClothingItemFactory(user=user, name='White Sneakers')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?q=blazer', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert 'Blazer' in results[0]['name']

    def test_search_by_brand(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Polo',  brand='Ralph Lauren')
        ClothingItemFactory(user=user, name='Shirt', brand='Zara')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?q=ralph', **h)
        assert r.json()['results'][0]['brand'] == 'Ralph Lauren'


class TestSoftDelete:
    def test_delete_soft_removes_item(self, client):
        from wardrobe.models import ClothingItem
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        h = auth(client, user)
        client.delete(f'/api/wardrobe/items/{item.id}/', **h)
        # Item still in DB but is_active=False
        item.refresh_from_db()
        assert item.is_active is False

    def test_soft_deleted_item_hidden_from_list(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        h = auth(client, user)
        client.delete(f'/api/wardrobe/items/{item.id}/', **h)
        r = client.get('/api/wardrobe/items/', **h)
        ids = [i['id'] for i in r.json()['results']]
        assert item.id not in ids

    def test_soft_deleted_item_not_retrievable(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        h = auth(client, user)
        client.delete(f'/api/wardrobe/items/{item.id}/', **h)
        r = client.get(f'/api/wardrobe/items/{item.id}/', **h)
        assert r.status_code == 404


class TestWardrobeSearchByMaterial:
    def test_search_by_material(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Silk Blouse', material='silk')
        ClothingItemFactory(user=user, name='Wool Coat',   material='wool')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?q=silk', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert results[0]['name'] == 'Silk Blouse'

    def test_combined_filters(self, client):
        user = UserFactory()
        ClothingItemFactory(user=user, name='Smart Blazer', category='outerwear', formality='smart')
        ClothingItemFactory(user=user, name='Casual Jacket', category='outerwear', formality='casual')
        h = auth(client, user)
        r = client.get('/api/wardrobe/items/?category=outerwear&formality=smart', **h)
        results = r.json()['results']
        assert len(results) == 1
        assert results[0]['name'] == 'Smart Blazer'
