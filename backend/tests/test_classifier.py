"""Tests for the rule-based event type classifier."""
import pytest
from ritha.services.event_classifier import classify_event, dominant_formality


class TestClassifyEvent:
    def test_workout_keywords(self):
        for title in ['Gym session', 'Morning run', 'Yoga class', 'Spin at 7am', 'CrossFit']:
            result = classify_event(title)
            assert result['event_type'] == 'workout', f"Failed for: {title}"
            assert result['formality'] == 'activewear'

    def test_external_meeting(self):
        for title in ['Client presentation', 'Board meeting', 'Investor pitch', 'Demo for exec']:
            result = classify_event(title)
            assert result['event_type'] == 'external_meeting', f"Failed for: {title}"
            assert result['formality'] == 'smart'

    def test_internal_meeting(self):
        for title in ['Team standup', 'Sprint planning', 'Retro', '1:1 with Alex', 'All-hands']:
            result = classify_event(title)
            assert result['event_type'] == 'internal_meeting', f"Failed for: {title}"

    def test_social_events(self):
        for title in ["Sarah's birthday dinner", 'Team lunch', 'Drinks after work']:
            result = classify_event(title)
            assert result['event_type'] == 'social', f"Failed for: {title}"

    def test_travel(self):
        for title in ['Flight to Zurich', 'Check-in AMS hotel', 'Train to Basel']:
            result = classify_event(title)
            assert result['event_type'] == 'travel', f"Failed for: {title}"

    def test_wedding(self):
        for title in ['Anna & Tom wedding', 'Black tie gala', 'Engagement party']:
            result = classify_event(title)
            assert result['event_type'] == 'wedding', f"Failed for: {title}"
            assert result['formality'] == 'formal'

    def test_interview(self):
        result = classify_event('Job interview at Google')
        assert result['event_type'] == 'interview'
        assert result['formality'] == 'smart'

    def test_unknown_returns_other(self):
        result = classify_event('Buy milk')
        assert result['event_type'] == 'other'
        assert result['confidence'] == 'low'

    def test_case_insensitive(self):
        assert classify_event('GYM')['event_type'] == 'workout'
        assert classify_event('BOARD PRESENTATION')['event_type'] == 'external_meeting'

    def test_uses_description_fallback(self):
        result = classify_event('Meet up', description='yoga and coffee')
        assert result['event_type'] == 'workout'


class TestDominantFormality:
    """Tests for dominant_formality() using mock event objects."""

    class MockEvent:
        def __init__(self, title, formality=''):
            self.title    = title
            self.formality = formality

    def test_formal_wins(self):
        events = [
            self.MockEvent('Team standup', 'casual_smart'),
            self.MockEvent('Black tie gala', 'formal'),
        ]
        assert dominant_formality(events) == 'formal'

    def test_smart_over_casual(self):
        events = [
            self.MockEvent('Morning run', 'activewear'),
            self.MockEvent('Client demo', 'smart'),
        ]
        assert dominant_formality(events) == 'smart'

    def test_empty_list_returns_casual(self):
        assert dominant_formality([]) == 'casual'

    def test_infers_from_title_when_no_formality(self):
        events = [self.MockEvent('Board presentation')]
        assert dominant_formality(events) == 'smart'
