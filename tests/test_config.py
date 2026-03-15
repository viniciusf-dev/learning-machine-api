"""
Tests for src/core/config.py

Covers: Settings defaults, database_url property, llm_model_id validator.
"""

import os
import pytest

from src.core.config import Settings


class TestSettingsDefaults:
    """Verify default values when no env vars are set (except required ones)."""

    def test_default_postgres_user(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.postgres_user == "agno_user"

    def test_default_postgres_db(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.postgres_db == "agno_memory"

    def test_default_api_port(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.api_port == 8000

    def test_default_learning_mode(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.learning_mode == "always"

    def test_default_enable_entity_memory(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.enable_entity_memory is True

    def test_default_recall_max_tokens(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.recall_max_tokens == 300

    def test_default_max_messages_per_request(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.max_messages_per_request == 100

    def test_default_log_level(self):
        s = Settings(anthropic_api_key="sk-test")
        assert s.log_level == "INFO"


class TestDatabaseUrl:
    def test_builds_correct_url(self):
        s = Settings(
            anthropic_api_key="sk-test",
            postgres_user="u",
            postgres_password="p",
            postgres_host="h",
            postgres_port=5433,
            postgres_db="d",
        )
        assert s.database_url == "postgresql://u:p@h:5433/d"


class TestLlmModelIdValidator:
    def test_strips_whitespace(self):
        s = Settings(anthropic_api_key="sk-test", llm_model_id="  claude-haiku  ")
        assert s.llm_model_id == "claude-haiku"

    def test_empty_raises(self):
        with pytest.raises(Exception):  # Pydantic ValidationError
            Settings(anthropic_api_key="sk-test", llm_model_id="")

    def test_whitespace_only_raises(self):
        with pytest.raises(Exception):
            Settings(anthropic_api_key="sk-test", llm_model_id="   ")


class TestRequiredFields:
    def test_missing_anthropic_key_raises(self):
        """anthropic_api_key has no default — must raise if absent."""
        env_backup = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(Exception):
                Settings(_env_file=None)
        finally:
            if env_backup:
                os.environ["ANTHROPIC_API_KEY"] = env_backup
