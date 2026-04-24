"""Tests for GET /api/weather/ endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from .factories import UserFactory

pytestmark = pytest.mark.django_db

MOCK_WEATHER = {
    'daily': {
        'temperature_2m_max':            [20.0],
        'temperature_2m_min':            [12.0],
        'precipitation_sum':             [0.0],
        'precipitation_probability_max': [15],
        'weathercode':                   [2],
        'windspeed_10m_max':             [18.0],
    },
    'hourly': {'relativehumidity_2m': [60]*24, 'temperature_2m': [16.0]*24},
    'current_weather': {'temperature': 16.5, 'weathercode': 2},
}

MOCK_GEO = {
    'results': [{'name': 'Zurich', 'latitude': 47.37, 'longitude': 8.54, 'country': 'Switzerland'}]
}


def auth(client, user):
    r = client.post('/api/auth/login/', {'email': user.email, 'password': 'testpass99'},
                    content_type='application/json')
    return {'HTTP_AUTHORIZATION': f"Bearer {r.json()['access']}"}


class TestWeatherEndpoint:
    @patch('ritha.services.weather.requests.get')
    def test_fetch_by_latlon(self, mock_get, client):
        user = UserFactory()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_WEATHER
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        h = auth(client, user)
        r = client.get('/api/weather/?lat=47.37&lon=8.54', **h)
        assert r.status_code == 200
        data = r.json()
        assert 'temp_c' in data
        assert 'condition' in data
        assert 'is_raining' in data
        assert data['source'] == 'open-meteo'

    @patch('ritha.services.weather.requests.get')
    def test_fetch_by_location_name(self, mock_get, client):
        user = UserFactory()
        geo_resp = MagicMock()
        geo_resp.json.return_value = MOCK_GEO
        geo_resp.raise_for_status = MagicMock()
        weather_resp = MagicMock()
        weather_resp.json.return_value = MOCK_WEATHER
        weather_resp.raise_for_status = MagicMock()
        mock_get.side_effect = [geo_resp, weather_resp]
        h = auth(client, user)
        r = client.get('/api/weather/?location=Zurich', **h)
        assert r.status_code == 200
        assert r.json()['location_name'] == 'Zurich'

    def test_missing_params_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/weather/', **h)
        assert r.status_code == 400

    def test_invalid_date_returns_400(self, client):
        user = UserFactory()
        h = auth(client, user)
        r = client.get('/api/weather/?lat=47.37&lon=8.54&date=not-a-date', **h)
        assert r.status_code == 400

    def test_unauthenticated_blocked(self, client):
        r = client.get('/api/weather/?lat=47.37&lon=8.54')
        assert r.status_code == 401

    @patch('ritha.services.weather.requests.get')
    def test_with_specific_date(self, mock_get, client):
        user = UserFactory()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_WEATHER
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        h = auth(client, user)
        r = client.get('/api/weather/?lat=47.37&lon=8.54&date=2026-04-01', **h)
        assert r.status_code == 200
        assert r.json()['date'] == '2026-04-01'
