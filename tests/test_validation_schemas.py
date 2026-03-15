"""
Tests for src/validation/schemas.py

Covers: Pydantic request/response models, field validators, edge cases.
"""

import pytest
from pydantic import ValidationError

from src.validation.schemas import (
    MessageRequest,
    ProcessRequest,
    ProcessResponse,
    RecallRequest,
    RecallResponse,
    HealthResponse,
    ClearMemoryResponse,
    ErrorDetail,
)


# ---------------------------------------------------------------------------
# MessageRequest
# ---------------------------------------------------------------------------

class TestMessageRequest:
    def test_valid(self):
        m = MessageRequest(role="user", content="hello")
        assert m.role == "user"
        assert m.content == "hello"

    def test_role_normalized_to_lowercase(self):
        m = MessageRequest(role="  USER  ", content="hi")
        assert m.role == "user"

    def test_content_stripped(self):
        m = MessageRequest(role="user", content="  hi  ")
        assert m.content == "hi"

    def test_empty_role_raises(self):
        with pytest.raises(ValidationError):
            MessageRequest(role="", content="hi")

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError):
            MessageRequest(role="user", content="")

    def test_content_exceeds_max_length_raises(self):
        with pytest.raises(ValidationError):
            MessageRequest(role="user", content="x" * 100_001)


# ---------------------------------------------------------------------------
# ProcessRequest
# ---------------------------------------------------------------------------

class TestProcessRequest:
    def test_valid(self):
        r = ProcessRequest(
            user_id="u1",
            session_id="s1",
            channel="whatsapp",
            messages=[MessageRequest(role="user", content="hi")],
        )
        assert r.user_id == "u1"
        assert r.channel == "whatsapp"

    def test_channel_normalized_to_lowercase(self):
        r = ProcessRequest(
            user_id="u1",
            session_id="s1",
            channel="  WhatsApp  ",
            messages=[MessageRequest(role="user", content="hi")],
        )
        assert r.channel == "whatsapp"

    def test_whitespace_stripped_from_ids(self):
        r = ProcessRequest(
            user_id="  u1  ",
            session_id="  s1  ",
            channel="slack",
            messages=[MessageRequest(role="user", content="hi")],
        )
        assert r.user_id == "u1"
        assert r.session_id == "s1"

    def test_invalid_channel_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ProcessRequest(
                user_id="u1",
                session_id="s1",
                channel="email",
                messages=[MessageRequest(role="user", content="hi")],
            )
        assert "Unsupported channel" in str(exc_info.value)

    def test_empty_messages_raises(self):
        with pytest.raises(ValidationError):
            ProcessRequest(
                user_id="u1",
                session_id="s1",
                channel="slack",
                messages=[],
            )

    def test_too_many_messages_raises(self):
        msgs = [MessageRequest(role="user", content="m")] * 101
        with pytest.raises(ValidationError) as exc_info:
            ProcessRequest(
                user_id="u1",
                session_id="s1",
                channel="slack",
                messages=msgs,
            )
        assert "maximum allowed" in str(exc_info.value).lower() or "100" in str(exc_info.value)

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            ProcessRequest(
                session_id="s1",
                channel="slack",
                messages=[MessageRequest(role="user", content="hi")],
            )

    def test_all_valid_channels(self):
        for ch in ("whatsapp", "slack", "telegram", "discord", "teams"):
            r = ProcessRequest(
                user_id="u1",
                session_id="s1",
                channel=ch,
                messages=[MessageRequest(role="user", content="hi")],
            )
            assert r.channel == ch


# ---------------------------------------------------------------------------
# RecallRequest
# ---------------------------------------------------------------------------

class TestRecallRequest:
    def test_valid(self):
        r = RecallRequest(user_id="u1", session_id="s1", channel="slack")
        assert r.user_id == "u1"

    def test_channel_case_insensitive(self):
        r = RecallRequest(user_id="u1", session_id="s1", channel="SLACK")
        assert r.channel == "slack"

    def test_invalid_channel_raises(self):
        with pytest.raises(ValidationError):
            RecallRequest(user_id="u1", session_id="s1", channel="sms")

    def test_whitespace_stripped(self):
        r = RecallRequest(user_id="  u1  ", session_id="  s1  ", channel="  slack  ")
        assert r.user_id == "u1"
        assert r.session_id == "s1"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class TestProcessResponse:
    def test_processed(self):
        r = ProcessResponse(status="processed")
        assert r.status == "processed"
        assert r.reason is None

    def test_skipped_with_reason(self):
        r = ProcessResponse(status="skipped", reason="no messages")
        assert r.reason == "no messages"


class TestRecallResponse:
    def test_with_memory(self):
        r = RecallResponse(user_id="u1", context="some info", has_memory=True)
        assert r.has_memory is True
        assert r.context == "some info"

    def test_no_memory(self):
        r = RecallResponse(user_id="u1", has_memory=False)
        assert r.has_memory is False
        assert r.context is None


class TestHealthResponse:
    def test_ok(self):
        r = HealthResponse(status="ok")
        assert r.status == "ok"


class TestClearMemoryResponse:
    def test_cleared(self):
        r = ClearMemoryResponse(status="cleared", user_id="u1")
        assert r.status == "cleared"
        assert r.user_id == "u1"


class TestErrorDetail:
    def test_basic(self):
        e = ErrorDetail(error="bad_request", message="invalid")
        assert e.error == "bad_request"
        assert e.detail is None

    def test_with_detail(self):
        e = ErrorDetail(error="service_error", message="err", detail="traceback")
        assert e.detail == "traceback"
