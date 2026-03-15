"""
Tests for src/infrastructure/prompts.py

Covers: get_system_prompt, get_extraction_prompt, get_recall_prompt.
"""

from src.infrastructure.prompts import (
    get_system_prompt,
    get_extraction_prompt,
    get_recall_prompt,
)


class TestGetSystemPrompt:
    def test_returns_non_empty_string(self):
        prompt = get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_core_instructions(self):
        prompt = get_system_prompt()
        assert "cross-session memory bridge" in prompt.lower()
        assert "WHAT TO SAVE" in prompt
        assert "WHAT TO IGNORE" in prompt
        assert "CONFLICT RESOLUTION" in prompt
        assert "latest-write-wins" in prompt.lower()

    def test_contains_channel_attribution_instructions(self):
        prompt = get_system_prompt()
        assert "source_channel" in prompt
        assert "last_updated_channel" in prompt

    def test_contains_noise_filtering(self):
        prompt = get_system_prompt()
        # Greetings should be ignored
        assert "Greetings" in prompt or "greetings" in prompt
        assert "noise" in prompt.lower() or "IGNORE" in prompt


class TestGetExtractionPrompt:
    def test_includes_channel(self):
        prompt = get_extraction_prompt("whatsapp", "sess_1", "Hello world")
        assert "whatsapp" in prompt

    def test_includes_session_id(self):
        prompt = get_extraction_prompt("slack", "sess_abc", "Hello")
        assert "sess_abc" in prompt

    def test_includes_conversation(self):
        prompt = get_extraction_prompt("telegram", "sess_1", "My meeting is at 3pm")
        assert "My meeting is at 3pm" in prompt

    def test_conflict_instructions_present(self):
        prompt = get_extraction_prompt("whatsapp", "s1", "msg")
        assert "conflict" in prompt.lower() or "UPDATE" in prompt


class TestGetRecallPrompt:
    def test_includes_channel(self):
        prompt = get_recall_prompt("slack")
        assert "slack" in prompt

    def test_includes_no_memory_sentinel(self):
        prompt = get_recall_prompt("whatsapp")
        assert "NO_MEMORY" in prompt

    def test_includes_all_channels_instruction(self):
        prompt = get_recall_prompt("discord")
        assert "ALL channels" in prompt or "all channels" in prompt

    def test_includes_token_limit(self):
        prompt = get_recall_prompt("whatsapp")
        # Should contain the max_tokens value from settings
        assert "300" in prompt or "tokens" in prompt.lower()
