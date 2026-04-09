import pytest
from .factories import UserFactory, ClothingItemFactory

pytestmark = pytest.mark.django_db


def auth_header(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestWardrobeItems:
    def test_list_own_items_only(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        ClothingItemFactory(user=user_a, name='A Blazer')
        ClothingItemFactory(user=user_b, name='B Dress')
        h = auth_header(client, user_a)
        r = client.get('/api/wardrobe/items/', **h)
        assert r.status_code == 200
        names = [i['name'] for i in r.json()['results']]
        assert 'A Blazer' in names
        assert 'B Dress' not in names

    def test_create_item(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/items/', {
            'name': 'Silk Blouse',
            'category': 'top',
            'formality': 'smart',
            'season': 'summer',
            'colors': ['white', 'cream'],
            'material': 'silk',
        }, content_type='application/json', **h)
        assert r.status_code == 201
        assert r.json()['name'] == 'Silk Blouse'
        assert r.json()['user'] == user.id

    def test_create_item_invalid_category(self, client):
        user = UserFactory()
        h = auth_header(client, user)
        r = client.post('/api/wardrobe/items/', {
            'name': 'Mystery Item', 'category': 'spaceship',
        }, content_type='application/json', **h)
        assert r.status_code == 400

    def test_update_item(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user, name='Old Name')
        h = auth_header(client, user)
        r = client.patch(f'/api/wardrobe/items/{item.id}/', {'name': 'New Name'},
                         content_type='application/json', **h)
        assert r.status_code == 200
        assert r.json()['name'] == 'New Name'

    def test_delete_item(self, client):
        user = UserFactory()
        item = ClothingItemFactory(user=user)
        h = auth_header(client, user)
        r = client.delete(f'/api/wardrobe/items/{item.id}/', **h)
        assert r.status_code == 204

    def test_cannot_access_other_users_item(self, client):
        user_a = UserFactory()
        user_b = UserFactory()
        item = ClothingItemFactory(user=user_b)
        h = auth_header(client, user_a)
        r = client.get(f'/api/wardrobe/items/{item.id}/', **h)
        assert r.status_code == 404

    def test_unauthenticated_blocked(self, client):
        r = client.get('/api/wardrobe/items/')
        assert r.status_code == 401
