"""
Tests for the weather service.
Uses mocked HTTP responses — no real network calls.
"""
import pytest
from unittest.mock import patch, MagicMock
import datetime
from ritha.services.weather import get_weather, get_weather_for_location, _fallback


MOCK_OPEN_METEO_RESPONSE = {
    'daily': {
        'temperature_2m_max':          [22.5],
        'temperature_2m_min':          [14.0],
        'precipitation_sum':           [0.0],
        'precipitation_probability_max': [10],
        'weathercode':                 [2],
        'windspeed_10m_max':           [15.0],
    },
    'hourly': {
        'relativehumidity_2m': [60] * 24,
        'temperature_2m':      [18.0] * 24,
    },
    'current_weather': {
        'temperature': 19.0,
        'weathercode': 2,
    },
}

MOCK_GEO_RESPONSE = {
    'results': [{'name': 'Zurich', 'latitude': 47.37, 'longitude': 8.54, 'country': 'Switzerland'}]
}


class TestGetWeather:
    @patch('ritha.services.weather.requests.get')
    def test_returns_snapshot_dict(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OPEN_METEO_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_weather(47.37, 8.54)

        assert 'temp_c' in result
        assert 'condition' in result
        assert 'precipitation_probability' in result
        assert result['source'] == 'open-meteo'
        assert isinstance(result['is_raining'], bool)
        assert isinstance(result['is_cold'], bool)

    @patch('ritha.services.weather.requests.get')
    def test_rainy_condition_detected(self, mock_get):
        rainy = {**MOCK_OPEN_METEO_RESPONSE}
        rainy['daily'] = {**rainy['daily'], 'weathercode': [61],
                          'precipitation_probability_max': [90],
                          'precipitation_sum': [8.5]}
        rainy['current_weather'] = {'temperature': 12.0, 'weathercode': 61}
        mock_resp = MagicMock()
        mock_resp.json.return_value = rainy
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_weather(47.37, 8.54)
        assert result['is_raining'] is True
        assert result['precipitation_probability'] == 90

    @patch('ritha.services.weather.requests.get')
    def test_cold_flag_set(self, mock_get):
        cold = {**MOCK_OPEN_METEO_RESPONSE}
        cold['current_weather'] = {'temperature': 4.0, 'weathercode': 0}
        mock_resp = MagicMock()
        mock_resp.json.return_value = cold
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_weather(47.37, 8.54)
        assert result['is_cold'] is True

    @patch('ritha.services.weather.requests.get')
    def test_fallback_on_network_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.RequestException('timeout')

        result = get_weather(47.37, 8.54)
        assert result['source'] == 'fallback'
        assert 'error' in result


class TestGetWeatherForLocation:
    @patch('ritha.services.weather.requests.get')
    def test_geocodes_and_fetches(self, mock_get):
        geo_resp  = MagicMock()
        geo_resp.json.return_value = MOCK_GEO_RESPONSE
        geo_resp.raise_for_status  = MagicMock()

        weather_resp = MagicMock()
        weather_resp.json.return_value = MOCK_OPEN_METEO_RESPONSE
        weather_resp.raise_for_status  = MagicMock()

        mock_get.side_effect = [geo_resp, weather_resp]

        result = get_weather_for_location('Zurich')
        assert result['location_name'] == 'Zurich'
        assert result['source'] == 'open-meteo'

    @patch('ritha.services.weather.requests.get')
    def test_unknown_location_returns_fallback(self, mock_get):
        no_results = MagicMock()
        no_results.json.return_value = {'results': []}
        no_results.raise_for_status  = MagicMock()
        mock_get.return_value = no_results

        result = get_weather_for_location('NonexistentPlace12345')
        assert result['source'] == 'fallback'


class TestFallback:
    def test_fallback_structure(self):
        result = _fallback('test error', datetime.date(2026, 3, 14))
        assert result['source'] == 'fallback'
        assert result['error'] == 'test error'
        assert result['date'] == '2026-03-14'
        assert 'temp_c' in result
