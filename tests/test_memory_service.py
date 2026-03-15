"""
Tests for src/services/memory_service.py

Covers: process_messages, recall_context, clear_memory, _extract_content,
        _raise_agent_error, NO_MEMORY sentinel.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.errors import BadRequestError, ServiceError, LlmError
from src.domain.models import Message, SessionContext
from src.services.memory_service import MemoryService

from tests.conftest import FakeAgentResponse, FakeLearningMachine, FakeCurator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(channel="whatsapp", session_id="sess_1"):
    return SessionContext(user_id="user_1", session_id=session_id, channel=channel)


def _make_messages():
    return [
        Message(role="user", content="I have a meeting at 3pm"),
        Message(role="assistant", content="Got it!"),
    ]


# ---------------------------------------------------------------------------
# process_messages
# ---------------------------------------------------------------------------

class TestProcessMessages:
    @pytest.mark.asyncio
    async def test_success(self, mock_agent):
        svc = MemoryService(mock_agent)
        ctx = _make_context()
        await svc.process_messages(ctx, _make_messages())

        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args
        assert call_kwargs.kwargs["user_id"] == "user_1"
        assert call_kwargs.kwargs["session_id"] == "extract_sess_1"

    @pytest.mark.asyncio
    async def test_empty_messages_raises_bad_request(self, mock_agent):
        svc = MemoryService(mock_agent)
        ctx = _make_context()
        with pytest.raises(BadRequestError, match="No messages"):
            await svc.process_messages(ctx, [])

    @pytest.mark.asyncio
    async def test_extraction_session_id_prefix(self, mock_agent):
        svc = MemoryService(mock_agent)
        ctx = _make_context(session_id="my_session")
        await svc.process_messages(ctx, _make_messages())

        call_kwargs = mock_agent.run.call_args
        assert call_kwargs.kwargs["session_id"] == "extract_my_session"

    @pytest.mark.asyncio
    async def test_agent_timeout_raises_llm_error(self, mock_agent):
        mock_agent.run.side_effect = Exception("Request timed out after 30s")
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(LlmError):
            await svc.process_messages(ctx, _make_messages())

    @pytest.mark.asyncio
    async def test_agent_db_error_raises_service_error(self, mock_agent):
        mock_agent.run.side_effect = Exception("database connection refused")
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(ServiceError):
            await svc.process_messages(ctx, _make_messages())

    @pytest.mark.asyncio
    async def test_agent_generic_error_raises_service_error(self, mock_agent):
        mock_agent.run.side_effect = RuntimeError("something unexpected")
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(ServiceError):
            await svc.process_messages(ctx, _make_messages())


# ---------------------------------------------------------------------------
# recall_context
# ---------------------------------------------------------------------------

class TestRecallContext:
    @pytest.mark.asyncio
    async def test_success_returns_content(self, mock_agent):
        mock_agent.learning_machine.build_context.return_value = "• Meeting at 3pm"
        svc = MemoryService(mock_agent)
        ctx = _make_context(channel="slack", session_id="sess_abc")

        result = await svc.recall_context(ctx)
        assert result == "• Meeting at 3pm"

    @pytest.mark.asyncio
    async def test_calls_build_context_with_user_id(self, mock_agent):
        mock_agent.learning_machine.build_context.return_value = "info"
        svc = MemoryService(mock_agent)
        ctx = _make_context(session_id="my_sess")

        await svc.recall_context(ctx)
        mock_agent.learning_machine.build_context.assert_called_once_with(
            user_id="user_1",
        )

    @pytest.mark.asyncio
    async def test_does_not_call_agent_run(self, mock_agent):
        """Recall uses build_context, NOT agent.run — no LLM call."""
        mock_agent.learning_machine.build_context.return_value = "info"
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        await svc.recall_context(ctx)
        mock_agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_build_context_returns_none(self, mock_agent):
        mock_agent.learning_machine.build_context.return_value = None
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        result = await svc.recall_context(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_build_context_returns_none(self, mock_agent):
        mock_agent.learning_machine.build_context.return_value = ""
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        result = await svc.recall_context(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_none(self, mock_agent):
        mock_agent.learning_machine.build_context.return_value = "   "
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        result = await svc.recall_context(ctx)
        assert result is None

    @pytest.mark.asyncio
    async def test_learning_machine_none_raises_service_error(self, mock_agent):
        mock_agent.learning_machine = None
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(ServiceError) as exc_info:
            await svc.recall_context(ctx)
        assert "Learning machine not available" in exc_info.value.internal_detail

    @pytest.mark.asyncio
    async def test_build_context_timeout_raises_llm_error(self, mock_agent):
        mock_agent.learning_machine.build_context.side_effect = Exception("timed out")
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(LlmError):
            await svc.recall_context(ctx)

    @pytest.mark.asyncio
    async def test_build_context_db_error_raises_service_error(self, mock_agent):
        mock_agent.learning_machine.build_context.side_effect = Exception("database connection lost")
        svc = MemoryService(mock_agent)
        ctx = _make_context()

        with pytest.raises(ServiceError):
            await svc.recall_context(ctx)


# ---------------------------------------------------------------------------
# clear_memory
# ---------------------------------------------------------------------------

class TestClearMemory:
    @pytest.mark.asyncio
    async def test_success(self, mock_agent):
        svc = MemoryService(mock_agent)
        await svc.clear_memory("user_1")

        lm = mock_agent.get_learning_machine()
        lm.curator.prune.assert_called_once_with(user_id="user_1", max_age_days=0)

    @pytest.mark.asyncio
    async def test_no_learning_machine_raises(self, mock_agent):
        mock_agent.get_learning_machine.return_value = None
        svc = MemoryService(mock_agent)

        with pytest.raises(ServiceError) as exc_info:
            await svc.clear_memory("user_1")
        assert "Learning machine not available" in exc_info.value.internal_detail

    @pytest.mark.asyncio
    async def test_no_curator_raises(self, mock_agent):
        lm = FakeLearningMachine(curator=None)
        mock_agent.get_learning_machine.return_value = lm
        svc = MemoryService(mock_agent)

        with pytest.raises(ServiceError) as exc_info:
            await svc.clear_memory("user_1")
        assert "Memory curator not available" in exc_info.value.internal_detail

    @pytest.mark.asyncio
    async def test_prune_failure_raises_service_error(self, mock_agent):
        lm = mock_agent.get_learning_machine()
        lm.curator.prune.side_effect = Exception("disk full")
        svc = MemoryService(mock_agent)

        with pytest.raises(ServiceError) as exc_info:
            await svc.clear_memory("user_1")
        assert "Failed to clear memory" in exc_info.value.internal_detail


# ---------------------------------------------------------------------------
# _extract_content (static method)
# ---------------------------------------------------------------------------

class TestExtractContent:
    def test_normal_response(self):
        resp = FakeAgentResponse("hello world")
        assert MemoryService._extract_content(resp) == "hello world"

    def test_strips_whitespace(self):
        resp = FakeAgentResponse("  hello  ")
        assert MemoryService._extract_content(resp) == "hello"

    def test_none_response(self):
        assert MemoryService._extract_content(None) is None

    def test_none_content(self):
        resp = FakeAgentResponse(None)
        assert MemoryService._extract_content(resp) is None

    def test_empty_content(self):
        resp = FakeAgentResponse("")
        assert MemoryService._extract_content(resp) is None

    def test_no_content_attribute(self):
        assert MemoryService._extract_content("plain string") is None


# ---------------------------------------------------------------------------
# _raise_agent_error (static method)
# ---------------------------------------------------------------------------

class TestRaiseAgentError:
    def test_timeout_raises_llm_error(self):
        with pytest.raises(LlmError):
            MemoryService._raise_agent_error(Exception("Request timed out"))

    def test_timed_out_raises_llm_error(self):
        with pytest.raises(LlmError):
            MemoryService._raise_agent_error(Exception("timed out after 30s"))

    def test_interrupted_raises_llm_error(self):
        with pytest.raises(LlmError):
            MemoryService._raise_agent_error(Exception("request was interrupted"))

    def test_database_raises_service_error(self):
        with pytest.raises(ServiceError):
            MemoryService._raise_agent_error(Exception("database connection lost"))

    def test_postgres_raises_service_error(self):
        with pytest.raises(ServiceError):
            MemoryService._raise_agent_error(Exception("postgres: connection refused"))

    def test_psycopg_raises_service_error(self):
        with pytest.raises(ServiceError):
            MemoryService._raise_agent_error(Exception("psycopg2.OperationalError"))

    def test_generic_raises_service_error(self):
        with pytest.raises(ServiceError):
            MemoryService._raise_agent_error(RuntimeError("unknown failure"))
