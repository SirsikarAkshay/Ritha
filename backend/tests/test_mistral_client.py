"""
Tests for ritha/services/mistral_client.py
All Mistral API calls are mocked — no real network requests.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestHasMistral:
    def test_returns_false_when_key_missing(self, settings):
        settings.MISTRAL_API_KEY = ''
        from ritha.services import mistral_client
        assert mistral_client._has_mistral() is False

    def test_returns_false_for_placeholder(self, settings):
        settings.MISTRAL_API_KEY = 'your_mistral_key_here'
        from ritha.services import mistral_client
        assert mistral_client._has_mistral() is False

    def test_returns_true_for_real_looking_key(self, settings):
        settings.MISTRAL_API_KEY = 'abc123realkey'
        from ritha.services import mistral_client
        assert mistral_client._has_mistral() is True


class TestChat:
    def _mock_mistral(self, content: str):
        """Return a mock Mistral client whose chat.complete() returns content."""
        mock_client   = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        mock_client.chat.complete.return_value    = mock_response
        return mock_client

    def test_returns_text_response(self, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        from ritha.services import mistral_client

        mock_client = self._mock_mistral('Hello from Mistral')
        with patch.object(mistral_client, '_get_client', return_value=mock_client):
            result = mistral_client.chat('Say hello')

        assert result == 'Hello from Mistral'

    def test_uses_default_model(self, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        from ritha.services import mistral_client

        mock_client = self._mock_mistral('ok')
        with patch.object(mistral_client, '_get_client', return_value=mock_client):
            mistral_client.chat('test prompt')

        call_kwargs = mock_client.chat.complete.call_args[1]
        assert call_kwargs['model'] == mistral_client.DEFAULT_MODEL

    def test_accepts_custom_model(self, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        from ritha.services import mistral_client

        mock_client = self._mock_mistral('ok')
        with patch.object(mistral_client, '_get_client', return_value=mock_client):
            mistral_client.chat('test', model='mistral-large-latest')

        call_kwargs = mock_client.chat.complete.call_args[1]
        assert call_kwargs['model'] == 'mistral-large-latest'


class TestChatJson:
    def _mock_chat(self, monkeypatch, content: str):
        from ritha.services import mistral_client
        monkeypatch.setattr(mistral_client, 'chat', lambda p, model=None, **kw: content)

    def test_parses_clean_json(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        self._mock_chat(monkeypatch, '{"item_ids": [1, 2], "notes": "great outfit"}')
        from ritha.services.mistral_client import chat_json
        result = chat_json('give me outfit JSON')
        assert result == {'item_ids': [1, 2], 'notes': 'great outfit'}

    def test_strips_backtick_fences(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        self._mock_chat(monkeypatch, '```json\n{"key": "value"}\n```')
        from ritha.services.mistral_client import chat_json
        result = chat_json('return json')
        assert result == {'key': 'value'}

    def test_strips_plain_backtick_fences(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        self._mock_chat(monkeypatch, '```\n{"key": "value"}\n```')
        from ritha.services.mistral_client import chat_json
        result = chat_json('return json')
        assert result == {'key': 'value'}

    def test_raises_on_invalid_json(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        self._mock_chat(monkeypatch, 'This is not JSON at all.')
        from ritha.services.mistral_client import chat_json
        with pytest.raises(ValueError, match='valid JSON'):
            chat_json('return json')

    def test_raises_on_empty_response(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        self._mock_chat(monkeypatch, '')
        from ritha.services.mistral_client import chat_json
        with pytest.raises(ValueError):
            chat_json('return json')

    def test_json_instruction_appended_to_prompt(self, settings):
        """chat_json should append JSON-only instruction to the prompt."""
        settings.MISTRAL_API_KEY = 'test-key'
        from ritha.services import mistral_client

        received_prompts = []

        def capture_chat(prompt, model=None, **kw):
            received_prompts.append(prompt)
            return '{"ok": true}'

        with patch.object(mistral_client, 'chat', side_effect=capture_chat):
            mistral_client.chat_json('My original prompt')

        assert 'My original prompt' in received_prompts[0]
        assert 'JSON' in received_prompts[0]

    def test_nested_json_parsed_correctly(self, monkeypatch, settings):
        settings.MISTRAL_API_KEY = 'test-key'
        payload = '{"day_plans": [{"day": 1, "item_ids": [1,2,3], "notes": "casual"}]}'
        self._mock_chat(monkeypatch, payload)
        from ritha.services.mistral_client import chat_json
        result = chat_json('plan my trip')
        assert len(result['day_plans']) == 1
        assert result['day_plans'][0]['day'] == 1
