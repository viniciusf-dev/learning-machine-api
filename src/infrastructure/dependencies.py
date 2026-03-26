"""
Initialization and dependency management for the Agno Memory Bridge API.

Handles database and agent initialization with proper error handling,
ensuring all dependencies are ready before the app starts serving requests.
Uses app.state for dependency storage instead of manual singleton pattern.
"""

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.learn import (
    LearningMachine,
    LearningMode,
    UserMemoryConfig,
    UserProfileConfig,
)
from agno.models.anthropic import Claude
from fastapi import FastAPI, Request

from src.core.config import settings
from src.domain.schemas import CrossSessionProfile
from src.infrastructure.prompts import get_system_prompt
from src.services.memory_service import MemoryService


logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """
    Application state stored in app.state.

    Holds initialized db, agent, and service instances. Stored directly on the
    FastAPI app instance to avoid global state and simplify testing —
    each test can create a fresh app with its own AppState.
    """

    db: PostgresDb
    agent: Agent
    service: MemoryService


def _build_agent(db: PostgresDb) -> Agent:
    """Create and configure the learning agent with cross-channel memory."""
    learning_mode = LearningMode[settings.learning_mode.upper()]

    return Agent(
        model=Claude(
            id=settings.llm_model_id,
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_request_timeout,
        ),
        db=db,
        learning=LearningMachine(
            user_profile=UserProfileConfig(
                mode=learning_mode,
                schema=CrossSessionProfile,
            ),
            user_memory=UserMemoryConfig(
                mode=learning_mode,
            ),
            entity_memory=settings.enable_entity_memory,
        ),
        instructions=get_system_prompt(),
    )


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Initializes db and agent on startup, stores them in app.state,
    and cleans up on shutdown. No global state — all state lives on the app.
    """
    logger.info("Initializing database connection...")
    try:
        db = PostgresDb(db_url=settings.database_url)
    except Exception as e:
        raise RuntimeError(f"Database initialization failed: {e}") from e

    logger.info("Setting up learning machine and agent...")
    try:
        agent = _build_agent(db)
    except Exception as e:
        raise RuntimeError(f"Agent initialization failed: {e}") from e

    app.state.services = AppState(db=db, agent=agent, service=MemoryService(agent))
    logger.info(
        f"Application startup complete — model={settings.llm_model_id}, "
        f"learning_mode={settings.learning_mode}"
    )

    yield

    logger.info("Shutting down...")
    if hasattr(db, "close"):
        try:
            db.close()
        except Exception as e:
            logger.warning(f"Error closing database: {e}")
    logger.info("Application shutdown complete")


def get_agent(request: Request) -> Agent:
    """
    FastAPI dependency: returns the initialized Agent from app.state.

    Raises RuntimeError if called before lifespan initialization.
    """
    services: AppState = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Services not initialized — lifespan may not have run")
    return services.agent


def get_service(request: Request) -> MemoryService:
    """
    FastAPI dependency: returns the singleton MemoryService from app.state.

    The service is created once at startup and reused for every request,
    avoiding unnecessary object churn and allowing safe future state.

    Raises RuntimeError if called before lifespan initialization.
    """
    services: AppState = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Services not initialized — lifespan may not have run")
    return services.service
