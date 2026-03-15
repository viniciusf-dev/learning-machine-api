"""
Shared fixtures for the Agno Memory Bridge API test suite.

Provides mock agents, fake app instances, and HTTP clients
so tests never touch real databases or LLM APIs.
"""

import os
import asyncio
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure ANTHROPIC_API_KEY is set before any import that triggers Settings()
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-fake-key-for-testing")


# ---------------------------------------------------------------------------
# Mock response objects
# ---------------------------------------------------------------------------

class FakeAgentResponse:
    """Mimics the object returned by agent.run()."""

    def __init__(self, content: Optional[str] = "some memory"):
        self.content = content


class FakeLearningMachine:
    """Mimics agent.get_learning_machine() result."""

    def __init__(self, curator=None):
        self.curator = curator


class FakeCurator:
    """Mimics the curator returned by LearningMachine."""

    def __init__(self):
        self.prune = MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_agent():
    """
    A MagicMock that behaves like agno.agent.Agent.

    - agent.run() returns a FakeAgentResponse by default
    - agent.get_learning_machine() returns a FakeLearningMachine with a curator
    """
    agent = MagicMock()
    agent.run = MagicMock(return_value=FakeAgentResponse("• Meeting with Acme: Thursday 2pm"))

    curator = FakeCurator()
    lm = FakeLearningMachine(curator=curator)
    agent.get_learning_machine = MagicMock(return_value=lm)

    return agent


@pytest.fixture
def app(mock_agent):
    """
    A fully wired FastAPI app with the mock agent injected into app.state.

    Bypasses lifespan_context entirely — no database, no LLM.
    """
    from src.infrastructure.dependencies import AppState
    from src.main import app as real_app

    real_app.state.services = AppState(db=MagicMock(), agent=mock_agent)
    return real_app


@pytest.fixture
def client(app):
    """Synchronous test client for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_process_payload():
    """A valid /process request payload."""
    return {
        "user_id": "user_123",
        "session_id": "sess_abc",
        "channel": "whatsapp",
        "messages": [
            {"role": "user", "content": "Hello, I have a meeting at 3pm"},
            {"role": "assistant", "content": "Got it!"},
        ],
    }


@pytest.fixture
def valid_recall_payload():
    """A valid /recall request payload."""
    return {
        "user_id": "user_123",
        "session_id": "sess_xyz",
        "channel": "slack",
    }
