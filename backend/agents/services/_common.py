"""
Helpers shared across the agent service modules.

These are the primitives more than one `run_*` agent needs: Mistral
availability, "today" formatting, and the wardrobe/weather loaders. The two
loaders delegate to the shared `ritha.services` helpers so the agent layer and
the destination recommender fetch data through a single code path.
"""

import datetime


def _has_mistral() -> bool:
    from ritha.services.mistral_client import _has_mistral as _check

    return _check()


def _today_str() -> str:
    return datetime.date.today().isoformat()


def _get_weather(input_data: dict) -> dict:
    """
    Return a WeatherSnapshot.
    Priority:
      1. weather dict passed directly in input_data (test / override)
      2. lat/lon from input_data  → Open-Meteo by coordinates
      3. location string          → geocode then Open-Meteo
      4. fallback to default snapshot
    """
    from ritha.services.weather import resolve_from_input

    return resolve_from_input(input_data)


def _wardrobe_for_user(user):
    from ritha.services.wardrobe_query import AGENT_FIELDS, fetch_wardrobe

    return fetch_wardrobe(user, AGENT_FIELDS)
