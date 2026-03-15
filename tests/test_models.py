"""
Tests for src/domain/models.py

Covers: Channel enum, Message validation/formatting, SessionContext validation.
"""

import pytest

from src.core.errors import BadRequestError
from src.domain.models import Channel, VALID_CHANNELS, Message, SessionContext


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------

class TestChannel:
    def test_all_values(self):
        assert set(VALID_CHANNELS) == {"whatsapp", "slack", "telegram", "discord", "teams"}

    def test_enum_members(self):
        assert Channel.WHATSAPP.value == "whatsapp"
        assert Channel.SLACK.value == "slack"
        assert Channel.TEAMS.value == "teams"


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class TestMessage:
    def test_valid_message(self):
        m = Message(role="user", content="hello")
        assert m.role == "user"
        assert m.content == "hello"

    def test_str_format(self):
        m = Message(role="user", content="hello world")
        assert str(m) == "[USER] hello world"

    def test_str_uppercases_role(self):
        m = Message(role="assistant", content="hi")
        assert str(m) == "[ASSISTANT] hi"

    def test_empty_role_raises(self):
        with pytest.raises(BadRequestError):
            Message(role="", content="hello")

    def test_none_role_raises(self):
        with pytest.raises(BadRequestError):
            Message(role=None, content="hello")

    def test_empty_content_raises(self):
        with pytest.raises(BadRequestError):
            Message(role="user", content="")

    def test_none_content_raises(self):
        with pytest.raises(BadRequestError):
            Message(role="user", content=None)

    def test_integer_role_raises(self):
        with pytest.raises(BadRequestError):
            Message(role=123, content="hello")

    def test_content_exceeds_max_length(self):
        """Content longer than settings.max_message_length should raise."""
        long_content = "x" * 100_001  # default max is 10_000
        with pytest.raises(BadRequestError):
            Message(role="user", content=long_content)


# ---------------------------------------------------------------------------
# SessionContext
# ---------------------------------------------------------------------------

class TestSessionContext:
    def test_valid_context(self):
        ctx = SessionContext(user_id="u1", session_id="s1", channel="whatsapp")
        assert ctx.user_id == "u1"
        assert ctx.session_id == "s1"
        assert ctx.channel == "whatsapp"

    # --- user_id ---
    def test_empty_user_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="", session_id="s1", channel="whatsapp")

    def test_none_user_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id=None, session_id="s1", channel="whatsapp")

    def test_long_user_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="x" * 256, session_id="s1", channel="whatsapp")

    def test_max_user_id_ok(self):
        ctx = SessionContext(user_id="x" * 255, session_id="s1", channel="slack")
        assert len(ctx.user_id) == 255

    # --- session_id ---
    def test_empty_session_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="u1", session_id="", channel="whatsapp")

    def test_none_session_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="u1", session_id=None, channel="whatsapp")

    def test_long_session_id_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="u1", session_id="x" * 256, channel="whatsapp")

    # --- channel ---
    def test_invalid_channel_raises(self):
        with pytest.raises(BadRequestError):
            SessionContext(user_id="u1", session_id="s1", channel="email")

    def test_all_valid_channels(self):
        for ch in VALID_CHANNELS:
            ctx = SessionContext(user_id="u1", session_id="s1", channel=ch)
            assert ctx.channel == ch


class TestSessionContextValidateUserId:
    """Test the static _validate_user_id method directly (used by DELETE /memory)."""

    def test_valid(self):
        SessionContext._validate_user_id("user_123")  # should not raise

    def test_empty(self):
        with pytest.raises(BadRequestError):
            SessionContext._validate_user_id("")

    def test_none(self):
        with pytest.raises(BadRequestError):
            SessionContext._validate_user_id(None)
