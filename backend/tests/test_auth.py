import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from .factories import UserFactory

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestRegister:
    def test_register_success(self, client):
        r = client.post('/api/auth/register/', {
            'email': 'new@arokah.com',
            'password': 'strongpass99',
            'first_name': 'Ada',
        }, content_type='application/json')
        assert r.status_code == 201
        assert r.json()['email'] == 'new@arokah.com'
        assert User.objects.filter(email='new@arokah.com').exists()

    def test_register_duplicate_email(self, client):
        UserFactory(email='dup@arokah.com')
        r = client.post('/api/auth/register/', {
            'email': 'dup@arokah.com', 'password': 'strongpass99',
        }, content_type='application/json')
        assert r.status_code == 400

    def test_register_missing_password(self, client):
        r = client.post('/api/auth/register/', {
            'email': 'nopw@arokah.com',
        }, content_type='application/json')
        assert r.status_code == 400

    def test_register_weak_password(self, client):
        r = client.post('/api/auth/register/', {
            'email': 'weak@arokah.com', 'password': '123',
        }, content_type='application/json')
        assert r.status_code == 400


class TestLogin:
    def test_login_returns_tokens(self, client):
        UserFactory(email='login@arokah.com')
        r = client.post('/api/auth/login/', {
            'email': 'login@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 200
        data = r.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_login_wrong_password(self, client):
        UserFactory(email='wp@arokah.com')
        r = client.post('/api/auth/login/', {
            'email': 'wp@arokah.com', 'password': 'wrongpass',
        }, content_type='application/json')
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post('/api/auth/login/', {
            'email': 'ghost@arokah.com', 'password': 'testpass99',
        }, content_type='application/json')
        assert r.status_code == 401


class TestMe:
    def _auth(self, client, user):
        r = client.post('/api/auth/login/', {
            'email': user.email, 'password': 'testpass99',
        }, content_type='application/json')
        return r.json()['access']

    def test_me_authenticated(self, client):
        user  = UserFactory(first_name='Jane')
        token = self._auth(client, user)
        r = client.get('/api/auth/me/', HTTP_AUTHORIZATION=f'Bearer {token}')
        assert r.status_code == 200
        assert r.json()['email'] == user.email
        assert r.json()['first_name'] == 'Jane'

    def test_me_unauthenticated(self, client):
        r = client.get('/api/auth/me/')
        assert r.status_code == 401

    def test_me_patch_name(self, client):
        user  = UserFactory()
        token = self._auth(client, user)
        r = client.patch('/api/auth/me/', {'first_name': 'Updated'},
                         content_type='application/json',
                         HTTP_AUTHORIZATION=f'Bearer {token}')
        assert r.status_code == 200
        assert r.json()['first_name'] == 'Updated'


class TestUserModel:
    def test_full_name_with_both_names(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User(first_name='Jane', last_name='Doe', email='j@x.com')
        assert user.full_name == 'Jane Doe'

    def test_full_name_email_fallback(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User(email='jane@arokah.com')
        assert user.full_name == 'jane@arokah.com'

    def test_str_returns_email(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User(email='str@arokah.com')
        assert str(user) == 'str@arokah.com'

    @pytest.mark.django_db
    def test_create_superuser(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.create_superuser('admin2@test.com', 'adminpass99')
        assert admin.is_staff is True
        assert admin.is_superuser is True

    @pytest.mark.django_db
    def test_create_user_without_email_raises(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with pytest.raises(ValueError):
            User.objects.create_user(email='', password='pw')
