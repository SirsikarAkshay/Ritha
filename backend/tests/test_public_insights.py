"""Tests for the unauthenticated destination-insight preview (weather gap + gauge)."""
import pytest

from ritha.services.public_insights import trip_insights

COLD = {"temp_c": 8, "condition": "Cold & clear", "is_cold": True}
WARM = {"temp_c": 31, "condition": "Hot & humid", "is_hot": True}


def test_weather_gap_headline_and_delta_for_cold_destination():
    r = trip_insights("Tokyo, Japan", date="2027-04-06", weather=COLD)
    gap = r["weather_gap"]
    assert gap["home_temp_c"] == 26          # assumed Bengaluru baseline
    assert gap["dest_temp_c"] == 8
    assert gap["delta_c"] == -18
    assert gap["colder"] is True
    assert gap["assumed_home"] is True
    assert gap["headline"] == "Your closet's built for 26°C. Tokyo isn't."


def test_home_city_and_temp_override():
    r = trip_insights("Tokyo, Japan", weather=COLD, home_city="Zurich", home_temp_c=4)
    gap = r["weather_gap"]
    assert r["home"]["city"] == "Zurich"
    assert r["home"]["assumed"] is False
    assert gap["home_temp_c"] == 4
    assert gap["delta_c"] == 4               # 8 - 4, destination warmer
    assert gap["colder"] is False
    # 4°C gap is under the threshold → no dramatic headline
    assert gap["headline"] is None


def test_cues_are_tagged_gap_dresscode_seasonal():
    r = trip_insights("Tokyo, Japan", date="2027-04-06", weather=COLD)
    cues = r["cues"]
    assert 1 <= len(cues) <= 3
    tags = [c["tag"] for c in cues]
    assert tags[0] == "gap"
    assert any(t == "April tip" for t in tags)       # seasonal tip uses the month
    for c in cues:
        assert c["icon"] and c["text"] and c["tag"]


def test_cues_have_no_seasonal_without_date():
    r = trip_insights("Tokyo, Japan", weather=COLD)
    assert all(not t["tag"].endswith("tip") for t in r["cues"])


def test_packing_gauge_shape():
    r = trip_insights("Tokyo, Japan", weather=COLD)
    pk = r["packing"]
    assert pk["bag_capacity_l"] == 40
    assert pk["piece_count"] >= pk["line_count"] >= 1  # quantities counted
    assert pk["volume_l"] > 0
    assert pk["percent_of_bag"] == round(100 * pk["volume_l"] / 40)
    assert pk["note"].endswith(f"{pk['volume_l']} L")


def test_warm_destination_flips_gap_direction():
    r = trip_insights("Dubai, UAE", weather=WARM)
    gap = r["weather_gap"]
    assert gap["delta_c"] == 5               # 31 - 26
    assert gap["colder"] is False
