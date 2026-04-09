"""Tests for the /api/health/ endpoint."""
import pytest

pytestmark = pytest.mark.django_db


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get('/api/health/')
        assert r.status_code == 200

    def test_health_no_auth_required(self, client):
        """Health endpoint must be publicly accessible for load balancers."""
        r = client.get('/api/health/')
        assert r.status_code != 401

    def test_health_response_structure(self, client):
        r = client.get('/api/health/')
        data = r.json()
        assert 'status' in data
        assert 'version' in data
        assert 'checks' in data
        assert 'database' in data['checks']
        assert 'cache' in data['checks']

    def test_health_database_ok(self, client):
        r = client.get('/api/health/')
        assert r.json()['checks']['database'] == 'ok'

    def test_health_status_healthy(self, client):
        r = client.get('/api/health/')
        assert r.json()['status'] == 'healthy'

    def test_health_version_present(self, client):
        r = client.get('/api/health/')
        assert r.json()['version'] == '1.0.0'


class TestHealthCheckEdgeCases:
    def test_health_debug_flag_present(self, client):
        r = client.get('/api/health/')
        assert 'debug' in r.json()

    def test_health_wardrobe_count_present(self, client):
        r = client.get('/api/health/')
        assert 'wardrobe_items' in r.json()['checks']
        assert isinstance(r.json()['checks']['wardrobe_items'], int)

    def test_health_db_failure_returns_503(self, client, monkeypatch):
        """Simulate DB failure — health should return 503."""
        from django.db import connection

        original = connection.cursor

        def bad_cursor():
            raise Exception("DB unavailable")

        monkeypatch.setattr(connection, 'cursor', bad_cursor)
        r = client.get('/api/health/')
        assert r.status_code == 503
        assert r.json()['status'] == 'degraded'
        assert 'error' in r.json()['checks']['database']
