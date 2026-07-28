"""
Agent service layer.

Each `run_*` function takes a User + input_data dict and returns an output_data
dict. Weather is fetched automatically via Open-Meteo (no key needed); Mistral AI
calls activate once MISTRAL_API_KEY is set.

This package was split out of a single `services.py` module. The per-agent logic
now lives in focused submodules (`daily`, `weekly`, `packing`, `conflicts`,
`cultural`, `planner`, `recommend`) over a shared `_common` helper module. The
public surface — the `run_*` entry points plus the few internals that callers and
tests import by name — is re-exported here so `agents.services.<name>` keeps
working exactly as before.
"""

from agents.services._common import (
    _get_weather,
    _has_mistral,
    _today_str,
    _wardrobe_for_user,
)
from agents.services.conflicts import run_conflict_detector
from agents.services.cultural import run_cultural_advisor
from agents.services.daily import (
    _build_outfit_transitions,
    _daily_look_stub,
    run_daily_look,
)
from agents.services.packing import run_packing_list
from agents.services.planner import run_outfit_planner
from agents.services.recommend import run_place_outfit, run_smart_recommend
from agents.services.weekly import run_weekly_looks

__all__ = [
    # Public agent entry points
    "run_daily_look",
    "run_weekly_looks",
    "run_packing_list",
    "run_conflict_detector",
    "run_cultural_advisor",
    "run_outfit_planner",
    "run_smart_recommend",
    "run_place_outfit",
    # Internals imported by name elsewhere (tests / cross-module helpers)
    "_build_outfit_transitions",
    "_daily_look_stub",
    "_get_weather",
    "_has_mistral",
    "_today_str",
    "_wardrobe_for_user",
]
