"""
Tests for src/infrastructure/dependencies.py

Covers: AppState, _build_agent (via mock), lifespan_context, get_agent.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass

from fastapi import FastAPI

from src.infrastructure.dependencies import AppState, get_agent


class TestAppState:
    def test_stores_db_and_agent(self):
        db = MagicMock()
        agent = MagicMock()
        state = AppState(db=db, agent=agent)
        assert state.db is db
        assert state.agent is agent


class TestGetAgent:
    def test_returns_agent_from_state(self):
        app = FastAPI()
        mock_agent = MagicMock()
        app.state.services = AppState(db=MagicMock(), agent=mock_agent)

        request = MagicMock()
        request.app = app

        result = get_agent(request)
        assert result is mock_agent

    def test_raises_when_services_not_set(self):
        app = FastAPI()
        request = MagicMock()
        request.app = app
        # Don't set app.state.services

        with pytest.raises(RuntimeError, match="Services not initialized"):
            get_agent(request)


class TestLifespanContext:
    @pytest.mark.asyncio
    async def test_lifespan_sets_and_cleans_state(self):
        """Lifespan should set app.state.services on startup and clean up on shutdown."""
        from src.infrastructure.dependencies import lifespan_context

        app = FastAPI()

        with patch("src.infrastructure.dependencies.PostgresDb") as MockDb, \
             patch("src.infrastructure.dependencies._build_agent") as mock_build:
            mock_db = MagicMock()
            MockDb.return_value = mock_db
            mock_build.return_value = MagicMock()

            async with lifespan_context(app):
                # During lifespan, services should be set
                assert hasattr(app.state, "services")
                assert app.state.services is not None
                assert app.state.services.db is mock_db

    @pytest.mark.asyncio
    async def test_lifespan_db_failure_raises_runtime_error(self):
        from src.infrastructure.dependencies import lifespan_context

        app = FastAPI()

        with patch("src.infrastructure.dependencies.PostgresDb", side_effect=Exception("connection refused")):
            with pytest.raises(RuntimeError, match="Database initialization failed"):
                async with lifespan_context(app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_agent_failure_raises_runtime_error(self):
        from src.infrastructure.dependencies import lifespan_context

        app = FastAPI()

        with patch("src.infrastructure.dependencies.PostgresDb") as MockDb, \
             patch("src.infrastructure.dependencies._build_agent", side_effect=Exception("bad config")):
            MockDb.return_value = MagicMock()

            with pytest.raises(RuntimeError, match="Agent initialization failed"):
                async with lifespan_context(app):
                    pass
