"""Tests for logout, password change, and account deletion."""
import pytest
from .factories import UserFactory

pytestmark = pytest.mark.django_db


def get_tokens(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return r.json()


class TestLogout:
    def test_logout_blacklists_refresh_token(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        r = client.post('/api/auth/logout/', {'refresh': tokens['refresh']},
                        content_type='application/json',
                        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 205

    def test_blacklisted_refresh_token_rejected(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        # Logout first
        client.post('/api/auth/logout/', {'refresh': tokens['refresh']},
                    content_type='application/json',
                    HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # Try to refresh with now-blacklisted token
        r = client.post('/api/auth/refresh/', {'refresh': tokens['refresh']},
                        content_type='application/json')
        assert r.status_code == 401

    def test_logout_missing_refresh_returns_400(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        r = client.post('/api/auth/logout/', {},
                        content_type='application/json',
                        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 400

    def test_logout_requires_authentication(self, client):
        r = client.post('/api/auth/logout/', {'refresh': 'x'},
                        content_type='application/json')
        assert r.status_code == 401


class TestPasswordChange:
    def test_change_password_success(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        r = client.post('/api/auth/me/password/',
                        {'current_password': 'testpass99', 'new_password': 'newSecure123'},
                        content_type='application/json',
                        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 200
        # Old token still valid (access token isn't revoked, only login credentials changed)
        # New login should work
        r2 = client.post('/api/auth/login/', {'email': user.email, 'password': 'newSecure123'},
                         content_type='application/json')
        assert r2.status_code == 200

    def test_wrong_current_password_rejected(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        r = client.post('/api/auth/me/password/',
                        {'current_password': 'wrongpassword', 'new_password': 'newSecure123'},
                        content_type='application/json',
                        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 400

    def test_weak_new_password_rejected(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        r = client.post('/api/auth/me/password/',
                        {'current_password': 'testpass99', 'new_password': '123'},
                        content_type='application/json',
                        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 400


class TestDeleteAccount:
    def test_delete_removes_user(self, client):
        from django.contrib.auth import get_user_model
        user   = UserFactory()
        uid    = user.id
        tokens = get_tokens(client, user)
        r = client.delete('/api/auth/me/delete/',
                          HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 204
        assert not get_user_model().objects.filter(id=uid).exists()

    def test_delete_cascades_wardrobe(self, client):
        from .factories import ClothingItemFactory
        from wardrobe.models import ClothingItem
        user   = UserFactory()
        item   = ClothingItemFactory(user=user)
        item_id = item.id
        tokens  = get_tokens(client, user)
        client.delete('/api/auth/me/delete/',
                      HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert not ClothingItem.objects.filter(id=item_id).exists()

    def test_delete_requires_authentication(self, client):
        r = client.delete('/api/auth/me/delete/')
        assert r.status_code == 401


class TestPasswordChangeLoginVerification:
    def test_old_password_rejected_after_change(self, client):
        """After password change, the old password must no longer work."""
        user   = UserFactory()
        tokens = get_tokens(client, user)
        # Change password
        client.post('/api/auth/me/password/',
                    {'current_password': 'testpass99', 'new_password': 'newSecure999'},
                    content_type='application/json',
                    HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # Try logging in with old password
        r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                        content_type='application/json')
        assert r.status_code == 401

    def test_new_password_works_after_change(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        client.post('/api/auth/me/password/',
                    {'current_password': 'testpass99', 'new_password': 'newSecure999'},
                    content_type='application/json',
                    HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        r = client.post('/api/auth/login/', {'email': user.email, 'password': 'newSecure999'},
                        content_type='application/json')
        assert r.status_code == 200
        assert 'access' in r.json()


class TestTokenBlacklistIntegration:
    def test_blacklisted_token_returns_401_on_refresh(self, client):
        user   = UserFactory()
        tokens = get_tokens(client, user)
        # Blacklist via logout
        client.post('/api/auth/logout/', {'refresh': tokens['refresh']},
                    content_type='application/json',
                    HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # Attempt to use blacklisted refresh token
        r = client.post('/api/auth/refresh/', {'refresh': tokens['refresh']},
                        content_type='application/json')
        assert r.status_code == 401

    def test_access_token_still_works_after_logout(self, client):
        """Access token remains valid until expiry even after logout."""
        user   = UserFactory()
        tokens = get_tokens(client, user)
        client.post('/api/auth/logout/', {'refresh': tokens['refresh']},
                    content_type='application/json',
                    HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # Access token still valid (JWT is stateless until expiry)
        r = client.get('/api/auth/me/', HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert r.status_code == 200
