"""
Weather service using Open-Meteo (https://open-meteo.com).
Free, no API key required. Returns a standardised WeatherSnapshot dict.
"""
import datetime
import requests
from typing import Optional


# WMO weather interpretation codes → human label
WMO_CODES = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Foggy', 48: 'Icy fog',
    51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
    61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
    71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains',
    80: 'Light showers', 81: 'Showers', 82: 'Heavy showers',
    85: 'Snow showers', 86: 'Heavy snow showers',
    95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with heavy hail',
}


def get_weather(lat: float, lon: float, date: Optional[datetime.date] = None) -> dict:
    """
    Fetch weather for a lat/lon coordinate.
    Returns today's forecast if date is None, else the forecast for that date.

    Returns a WeatherSnapshot dict:
        {
            'temp_c': float,
            'temp_min_c': float,
            'temp_max_c': float,
            'condition': str,          # human-readable
            'wmo_code': int,
            'precipitation_mm': float,
            'precipitation_probability': int,  # 0-100
            'wind_kmh': float,
            'humidity': int,           # %
            'is_raining': bool,
            'is_cold': bool,           # < 10 °C
            'is_hot': bool,            # > 28 °C
            'date': str,               # ISO
            'source': 'open-meteo',
        }
    """
    if date is None:
        date = datetime.date.today()

    params = {
        'latitude':  lat,
        'longitude': lon,
        'daily': [
            'temperature_2m_max',
            'temperature_2m_min',
            'precipitation_sum',
            'precipitation_probability_max',
            'weathercode',
            'windspeed_10m_max',
        ],
        'hourly': ['relativehumidity_2m', 'temperature_2m'],
        'current_weather': True,
        'timezone': 'auto',
        'start_date': date.isoformat(),
        'end_date':   date.isoformat(),
    }

    try:
        resp = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return _fallback(str(exc), date)

    daily = data.get('daily', {})
    current = data.get('current_weather', {})

    temp_max  = _first(daily.get('temperature_2m_max'))
    temp_min  = _first(daily.get('temperature_2m_min'))
    temp_now  = current.get('temperature', (temp_max + temp_min) / 2 if temp_max is not None else 15)
    wmo       = _first(daily.get('weathercode')) or current.get('weathercode', 0)
    precip    = _first(daily.get('precipitation_sum')) or 0.0
    precip_p  = _first(daily.get('precipitation_probability_max')) or 0
    wind      = _first(daily.get('windspeed_10m_max')) or 0.0

    # Average hourly humidity for the day
    hourly_hum = data.get('hourly', {}).get('relativehumidity_2m', [])
    humidity   = int(sum(hourly_hum) / len(hourly_hum)) if hourly_hum else 60

    feels_like = _feels_like(temp_now, wind, humidity)
    return {
        'temp_c':                   round(temp_now, 1),
        'feels_like_c':             round(feels_like, 1),
        'temp_min_c':               round(temp_min or temp_now, 1),
        'temp_max_c':               round(temp_max or temp_now, 1),
        'condition':                WMO_CODES.get(int(wmo), 'Unknown'),
        'wmo_code':                 int(wmo),
        'precipitation_mm':         round(float(precip), 1),
        'precipitation_probability': int(precip_p),
        'wind_kmh':                 round(float(wind), 1),
        'humidity':                 humidity,
        'is_raining':               int(wmo) in {51,53,55,61,63,65,80,81,82,95,96,99},
        'is_cold':                  feels_like < 10,
        'is_hot':                   feels_like > 28,
        'date':                     date.isoformat(),
        'source':                   'open-meteo',
    }


def get_weather_for_location(location_str: str, date: Optional[datetime.date] = None) -> dict:
    """
    Geocode a location string then fetch weather.
    Uses Open-Meteo's free geocoding API.
    """
    try:
        geo = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search',
            params={'name': location_str, 'count': 1, 'language': 'en', 'format': 'json'},
            timeout=5,
        )
        geo.raise_for_status()
        results = geo.json().get('results', [])
        if not results:
            return _fallback(f'Location not found: {location_str}', date or datetime.date.today())
        lat = results[0]['latitude']
        lon = results[0]['longitude']
        loc_name = results[0].get('name', location_str)
        target_date = date or datetime.date.today()
        horizon_limit = datetime.date.today() + datetime.timedelta(days=15)
        if target_date > horizon_limit:
            climo = get_climatology_forecast(lat, lon, target_date, target_date, loc_name)
            return climo[0] if climo else _fallback('climatology unavailable', target_date)
        snapshot = get_weather(lat, lon, target_date)
        snapshot['location_name'] = loc_name
        # If the live forecast came back as a generic fallback, try climatology.
        if snapshot.get('source') == 'fallback':
            climo = get_climatology_forecast(lat, lon, target_date, target_date, loc_name)
            if climo and climo[0].get('source') == 'climatology':
                return climo[0]
        return snapshot
    except requests.RequestException as exc:
        return _fallback(str(exc), date or datetime.date.today())


FORECAST_HORIZON_DAYS = 15  # Open-Meteo forecast is reliable within ~16 days


def get_weather_forecast(location_str: str, start_date: datetime.date, end_date: datetime.date) -> list:
    """
    Return a list of WeatherSnapshot dicts, one per day from start_date to end_date.
    Uses Open-Meteo's multi-day forecast with a single API call.  Falls back to
    a climatology estimate (historical averages) when the requested window is
    beyond the forecast horizon or when the live forecast is unavailable.
    """
    # Geocode first
    try:
        geo = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search',
            params={'name': location_str, 'count': 1, 'language': 'en', 'format': 'json'},
            timeout=5,
        )
        geo.raise_for_status()
        results = geo.json().get('results', [])
        if not results:
            num_days = (end_date - start_date).days + 1
            return [_fallback(f'Location not found: {location_str}', start_date + datetime.timedelta(days=i))
                    for i in range(num_days)]
        lat = results[0]['latitude']
        lon = results[0]['longitude']
        loc_name = results[0].get('name', location_str)
    except requests.RequestException as exc:
        num_days = (end_date - start_date).days + 1
        return [_fallback(str(exc), start_date + datetime.timedelta(days=i)) for i in range(num_days)]

    # If the trip is beyond the forecast horizon, skip forecast and go straight
    # to climatology — no point asking the forecast API for dates it can't serve.
    today = datetime.date.today()
    if start_date > today + datetime.timedelta(days=FORECAST_HORIZON_DAYS):
        return get_climatology_forecast(lat, lon, start_date, end_date, loc_name)

    # Fetch multi-day forecast in one call
    params = {
        'latitude': lat, 'longitude': lon,
        'daily': [
            'temperature_2m_max', 'temperature_2m_min',
            'precipitation_sum', 'precipitation_probability_max',
            'weathercode', 'windspeed_10m_max',
        ],
        'hourly': ['relativehumidity_2m'],
        'timezone': 'auto',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    try:
        resp = requests.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return get_climatology_forecast(lat, lon, start_date, end_date, loc_name)

    daily = data.get('daily', {})
    dates = daily.get('time', [])
    if not dates:
        return get_climatology_forecast(lat, lon, start_date, end_date, loc_name)

    # Extract per-day average humidity from hourly data (24 values per day)
    hourly_hum = data.get('hourly', {}).get('relativehumidity_2m', [])
    day_humidities = []
    for d in range(len(dates)):
        h_start = d * 24
        h_end = h_start + 24
        day_h = [v for v in hourly_hum[h_start:h_end] if v is not None]
        day_humidities.append(int(sum(day_h) / len(day_h)) if day_h else 60)

    forecasts = []
    for i, date_str in enumerate(dates):
        temp_max = (daily.get('temperature_2m_max') or [])[i] if i < len(daily.get('temperature_2m_max', [])) else None
        temp_min = (daily.get('temperature_2m_min') or [])[i] if i < len(daily.get('temperature_2m_min', [])) else None
        temp_avg = round((temp_max + temp_min) / 2, 1) if temp_max is not None and temp_min is not None else 15.0
        wmo = (daily.get('weathercode') or [])[i] if i < len(daily.get('weathercode', [])) else 0
        precip = (daily.get('precipitation_sum') or [])[i] if i < len(daily.get('precipitation_sum', [])) else 0
        precip_p = (daily.get('precipitation_probability_max') or [])[i] if i < len(daily.get('precipitation_probability_max', [])) else 0
        wind = (daily.get('windspeed_10m_max') or [])[i] if i < len(daily.get('windspeed_10m_max', [])) else 0
        humidity = day_humidities[i] if i < len(day_humidities) else 60

        feels = _feels_like(temp_avg, float(wind or 0), humidity)
        forecasts.append({
            'temp_c': temp_avg,
            'feels_like_c': round(feels, 1),
            'temp_min_c': round(temp_min or temp_avg, 1),
            'temp_max_c': round(temp_max or temp_avg, 1),
            'condition': WMO_CODES.get(int(wmo), 'Unknown'),
            'wmo_code': int(wmo),
            'precipitation_mm': round(float(precip), 1),
            'precipitation_probability': int(precip_p or 0),
            'wind_kmh': round(float(wind or 0), 1),
            'humidity': humidity,
            'is_raining': int(wmo) in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99},
            'is_cold': feels < 10,
            'is_hot': feels > 28,
            'date': date_str,
            'source': 'open-meteo',
            'location_name': loc_name,
        })

    # If forecast came back short (trip extends past the horizon), extend the
    # tail with climatology so every day has a sensible estimate.
    num_days = (end_date - start_date).days + 1
    if len(forecasts) < num_days:
        last_forecast_date = datetime.date.fromisoformat(forecasts[-1]['date']) if forecasts else start_date - datetime.timedelta(days=1)
        tail_start = last_forecast_date + datetime.timedelta(days=1)
        if tail_start <= end_date:
            forecasts.extend(get_climatology_forecast(lat, lon, tail_start, end_date, loc_name))

    return forecasts


def get_climatology_forecast(lat: float, lon: float, start_date: datetime.date,
                              end_date: datetime.date, loc_name: str = '') -> list:
    """
    Build per-day climatology estimates by averaging the same calendar day over
    the past 5 completed years using Open-Meteo's free archive API.  Used when
    the requested dates are beyond the live forecast horizon or the forecast
    call failed.  Returns one WeatherSnapshot per day, tagged source='climatology'.
    """
    num_days = (end_date - start_date).days + 1
    today = datetime.date.today()
    years_back = 5
    base_year = today.year - 1  # last fully completed year

    # Aggregate by day offset (0..num_days-1) across sampled past years.
    agg = {i: {'tmax': [], 'tmin': [], 'precip': [], 'precip_p': [], 'wmo': [], 'wind': []}
           for i in range(num_days)}

    for yoff in range(years_back):
        year = base_year - yoff
        try:
            hist_start = start_date.replace(year=year)
            hist_end = end_date.replace(year=year)
        except ValueError:
            # Handles Feb 29 on non-leap years — step back one day.
            try:
                hist_start = (start_date - datetime.timedelta(days=1)).replace(year=year)
                hist_end = (end_date - datetime.timedelta(days=1)).replace(year=year)
            except ValueError:
                continue

        try:
            resp = requests.get(
                'https://archive-api.open-meteo.com/v1/archive',
                params={
                    'latitude': lat, 'longitude': lon,
                    'daily': [
                        'temperature_2m_max', 'temperature_2m_min',
                        'precipitation_sum', 'weathercode', 'windspeed_10m_max',
                    ],
                    'timezone': 'auto',
                    'start_date': hist_start.isoformat(),
                    'end_date': hist_end.isoformat(),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            continue

        daily = data.get('daily', {})
        times = daily.get('time', []) or []
        tmax_l = daily.get('temperature_2m_max') or []
        tmin_l = daily.get('temperature_2m_min') or []
        pr_l   = daily.get('precipitation_sum') or []
        wmo_l  = daily.get('weathercode') or []
        wind_l = daily.get('windspeed_10m_max') or []
        for idx in range(min(len(times), num_days)):
            if idx < len(tmax_l) and tmax_l[idx] is not None: agg[idx]['tmax'].append(tmax_l[idx])
            if idx < len(tmin_l) and tmin_l[idx] is not None: agg[idx]['tmin'].append(tmin_l[idx])
            if idx < len(pr_l)   and pr_l[idx]   is not None: agg[idx]['precip'].append(pr_l[idx])
            if idx < len(wmo_l)  and wmo_l[idx]  is not None: agg[idx]['wmo'].append(int(wmo_l[idx]))
            if idx < len(wind_l) and wind_l[idx] is not None: agg[idx]['wind'].append(wind_l[idx])
            # Derive precipitation probability from historical rainy-day frequency later.

    # If every year's call failed, bail out to the generic fallback.
    if not any(agg[i]['tmax'] for i in range(num_days)):
        return [_fallback('climatology unavailable', start_date + datetime.timedelta(days=i))
                for i in range(num_days)]

    def _avg(xs, default=None):
        return round(sum(xs) / len(xs), 1) if xs else default

    def _mode_wmo(codes):
        if not codes: return 0
        counts = {}
        for c in codes: counts[c] = counts.get(c, 0) + 1
        return max(counts, key=counts.get)

    forecasts = []
    for i in range(num_days):
        date = start_date + datetime.timedelta(days=i)
        bucket = agg[i]
        tmax = _avg(bucket['tmax'])
        tmin = _avg(bucket['tmin'])
        tavg = round((tmax + tmin) / 2, 1) if tmax is not None and tmin is not None else 15.0
        precip = _avg(bucket['precip'], 0.0) or 0.0
        wmo = _mode_wmo(bucket['wmo'])
        wind = _avg(bucket['wind'], 0.0) or 0.0
        # Share of past years where any rain fell → proxy for probability.
        rainy_years = sum(1 for v in bucket['precip'] if v and v > 0.5)
        precip_p = int(round(100 * rainy_years / len(bucket['precip']))) if bucket['precip'] else 0
        forecasts.append({
            'temp_c': tavg,
            'temp_min_c': round(tmin if tmin is not None else tavg, 1),
            'temp_max_c': round(tmax if tmax is not None else tavg, 1),
            'condition': WMO_CODES.get(int(wmo), 'Typical seasonal'),
            'wmo_code': int(wmo),
            'precipitation_mm': round(float(precip), 1),
            'precipitation_probability': precip_p,
            'wind_kmh': round(float(wind), 1),
            'humidity': 60,
            'is_raining': precip > 1.0 or int(wmo) in {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99},
            'is_cold': tavg < 10,
            'is_hot': tavg > 28,
            'date': date.isoformat(),
            'source': 'climatology',
            'climatology_years': years_back,
            'location_name': loc_name,
        })
    return forecasts


def _feels_like(temp: float, wind_kmh: float, humidity: int) -> float:
    """Approximate feels-like temperature considering wind chill and heat index."""
    if temp <= 10 and wind_kmh > 5:
        return 13.12 + 0.6215 * temp - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp * (wind_kmh ** 0.16)
    if temp > 26 and humidity > 40:
        e = 6.105 * 2.7183 ** (17.27 * temp / (237.7 + temp))
        return temp + 0.33 * (humidity / 100 * e) - 4.0
    return temp


def _first(lst):
    if lst and len(lst) > 0:
        return lst[0]
    return None


_MONTH_LABEL = {
    1: 'winter', 2: 'late winter', 3: 'early spring', 4: 'spring', 5: 'late spring',
    6: 'early summer', 7: 'summer', 8: 'late summer', 9: 'early autumn',
    10: 'autumn', 11: 'late autumn', 12: 'winter',
}

# Temperate Northern-hemisphere seasonal baseline used as a last-ditch estimate
# when neither the live forecast nor the historical archive is reachable.
_SEASONAL_DEFAULTS = {
    1:  (2, -2, 6), 2:  (4,  0, 8), 3:  (9,  4, 14), 4:  (13, 7, 18),
    5:  (18, 11, 23), 6:  (22, 15, 28), 7:  (25, 18, 30), 8:  (25, 18, 30),
    9:  (20, 13, 26), 10: (14, 8, 19), 11: (8, 3, 12), 12: (3, -1, 7),
}


def _fallback(reason: str, date: datetime.date) -> dict:
    """
    Last-resort weather estimate when both the forecast API and the historical
    archive are unreachable.  Returns a seasonal baseline with source tag
    'estimated' so the UI can flag it as a rough estimate rather than a real
    forecast.  Never surfaces the raw API error to users.
    """
    tavg, tmin, tmax = _SEASONAL_DEFAULTS.get(date.month, (15, 10, 20))
    return {
        'temp_c': float(tavg), 'temp_min_c': float(tmin), 'temp_max_c': float(tmax),
        'condition': f'Typical {_MONTH_LABEL.get(date.month, "seasonal")} weather',
        'wmo_code': 0, 'precipitation_mm': 0.0,
        'precipitation_probability': 0, 'wind_kmh': 0.0,
        'humidity': 60,
        'is_raining': False,
        'is_cold': tavg < 10, 'is_hot': tavg > 28,
        'date': date.isoformat(), 'source': 'estimated',
        'note': reason,
    }
