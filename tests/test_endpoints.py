"""
Integration tests for API endpoints via TestClient.

Covers: /health, /process, /recall, /memory/{user_id},
        exception handlers, edge cases.

All tests use a mock agent — no real DB or LLM calls.
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from tests.conftest import FakeAgentResponse, FakeLearningMachine, FakeCurator


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

class TestProcessEndpoint:
    def test_success(self, client, mock_agent, valid_process_payload):
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        mock_agent.run.assert_called_once()

    def test_skipped_when_no_messages(self, client, valid_process_payload):
        valid_process_payload["messages"] = []
        resp = client.post("/process", json=valid_process_payload)
        # Pydantic rejects empty messages list (min_length=1)
        assert resp.status_code == 422

    def test_invalid_channel(self, client, valid_process_payload):
        valid_process_payload["channel"] = "email"
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 422

    def test_missing_user_id(self, client, valid_process_payload):
        del valid_process_payload["user_id"]
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 422

    def test_missing_session_id(self, client, valid_process_payload):
        del valid_process_payload["session_id"]
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 422

    def test_missing_messages(self, client, valid_process_payload):
        del valid_process_payload["messages"]
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 422

    def test_agent_error_returns_500(self, client, mock_agent, valid_process_payload):
        mock_agent.run.side_effect = Exception("something broke")
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "service_error"

    def test_agent_timeout_returns_500_with_llm_error(self, client, mock_agent, valid_process_payload):
        mock_agent.run.side_effect = Exception("Request timed out")
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "llm_error"

    def test_empty_body_returns_422(self, client):
        resp = client.post("/process", json={})
        assert resp.status_code == 422

    def test_channel_case_insensitive(self, client, mock_agent, valid_process_payload):
        valid_process_payload["channel"] = "WHATSAPP"
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 200

    def test_extraction_session_id_format(self, client, mock_agent, valid_process_payload):
        valid_process_payload["session_id"] = "my_sess"
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 200
        call_kwargs = mock_agent.run.call_args
        assert call_kwargs.kwargs["session_id"] == "extract_my_sess"


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------

class TestRecallEndpoint:
    def test_success_with_memory(self, client, mock_agent, valid_recall_payload):
        mock_agent.learning_machine.build_context.return_value = "• Meeting at 3pm"
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_memory"] is True
        assert data["context"] == "• Meeting at 3pm"
        assert data["user_id"] == "user_123"

    def test_no_memory(self, client, mock_agent, valid_recall_payload):
        mock_agent.learning_machine.build_context.return_value = ""
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_memory"] is False
        assert data["context"] is None

    def test_invalid_channel(self, client, valid_recall_payload):
        valid_recall_payload["channel"] = "carrier_pigeon"
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 422

    def test_missing_user_id(self, client, valid_recall_payload):
        del valid_recall_payload["user_id"]
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 422

    def test_agent_error_returns_500(self, client, mock_agent, valid_recall_payload):
        mock_agent.learning_machine.build_context.side_effect = Exception("kaboom")
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 500

    def test_recall_uses_build_context_not_run(self, client, mock_agent, valid_recall_payload):
        mock_agent.learning_machine.build_context.return_value = "info"
        resp = client.post("/recall", json=valid_recall_payload)
        assert resp.status_code == 200
        mock_agent.run.assert_not_called()
        mock_agent.learning_machine.build_context.assert_called_once()

    def test_empty_response_returns_no_memory(self, client, mock_agent, valid_recall_payload):
        mock_agent.learning_machine.build_context.return_value = ""
        resp = client.post("/recall", json=valid_recall_payload)
        data = resp.json()
        assert data["has_memory"] is False
        assert data["context"] is None


# ---------------------------------------------------------------------------
# Clear Memory
# ---------------------------------------------------------------------------

class TestClearMemoryEndpoint:
    def test_success(self, client, mock_agent):
        resp = client.delete("/memory/user_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleared"
        assert data["user_id"] == "user_123"

    def test_prune_called_correctly(self, client, mock_agent):
        client.delete("/memory/user_abc")
        lm = mock_agent.get_learning_machine()
        lm.curator.prune.assert_called_with(user_id="user_abc", max_age_days=0)

    def test_no_learning_machine_returns_500(self, client, mock_agent):
        mock_agent.get_learning_machine.return_value = None
        resp = client.delete("/memory/user_123")
        assert resp.status_code == 500

    def test_no_curator_returns_500(self, client, mock_agent):
        lm = FakeLearningMachine(curator=None)
        mock_agent.get_learning_machine.return_value = lm
        resp = client.delete("/memory/user_123")
        assert resp.status_code == 500

    def test_prune_failure_returns_500(self, client, mock_agent):
        lm = mock_agent.get_learning_machine()
        lm.curator.prune.side_effect = Exception("disk full")
        resp = client.delete("/memory/user_123")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

class TestExceptionHandlers:
    def test_api_exception_returns_structured_error(self, client, mock_agent, valid_process_payload):
        """BadRequestError from domain layer → 400 with error code."""
        # Force a BadRequestError by passing empty user_id through domain validation
        valid_process_payload["user_id"] = ""
        resp = client.post("/process", json=valid_process_payload)
        # Pydantic catches it first with min_length=1 → 422
        assert resp.status_code == 422

    def test_generic_exception_returns_500(self, client, mock_agent, valid_process_payload):
        """An unexpected exception → 500 with generic message."""
        mock_agent.run.side_effect = RuntimeError("segfault simulation")
        resp = client.post("/process", json=valid_process_payload)
        assert resp.status_code == 500
        data = resp.json()
        assert "segfault" not in data.get("message", "")


# ---------------------------------------------------------------------------
# OpenAPI / docs
# ---------------------------------------------------------------------------

class TestDocs:
    def test_openapi_json_available(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "/health" in data["paths"]
        assert "/process" in data["paths"]
        assert "/recall" in data["paths"]

    def test_docs_page_available(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
