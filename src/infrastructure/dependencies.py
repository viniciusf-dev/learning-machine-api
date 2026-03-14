"""
Initialization and dependency management for the Agno Memory Bridge API.

Handles database and agent initialization with proper error handling,
ensuring all dependencies are ready before the app starts serving requests.
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.learn import (
    LearningMachine,
    LearningMode,
    UserMemoryConfig,
    UserProfileConfig,
)
from agno.models.anthropic import Claude

from src.core.config import settings
from src.domain.schemas import CrossSessionProfile
from src.infrastructure.prompts import get_system_prompt


logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency container for all services.
    
    Ensures proper initialization order, handles cleanup, and provides
    singleton access to db and agent throughout the application lifetime.
    """

    _instance: Optional["ServiceContainer"] = None
    _db: Optional[PostgresDb] = None
    _agent: Optional[Agent] = None
    _is_initialized: bool = False

    def __new__(cls) -> "ServiceContainer":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def db(self) -> PostgresDb:
        """Get the database instance. Raises if not initialized."""
        if self._db is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() before accessing db."
            )
        return self._db

    @property
    def agent(self) -> Agent:
        """Get the learning agent instance. Raises if not initialized."""
        if self._agent is None:
            raise RuntimeError(
                "Agent not initialized. Call initialize() before accessing agent."
            )
        return self._agent

    @property
    def is_initialized(self) -> bool:
        """Check if all dependencies are initialized."""
        return self._is_initialized

    async def initialize(self) -> None:
        """
        Initialize all services in the correct order.
        
        Order is critical:
        1. Database (other services depend on it)
        2. Learning machine setup
        3. Agent creation
        
        Raises:
            ValueError: If database_url is invalid
            RuntimeError: If initialization fails
        """
        if self._is_initialized:
            logger.warning("ServiceContainer already initialized, skipping")
            return

        try:
            logger.info("Initializing database connection...")
            self._init_database()

            logger.info("Setting up learning machine and agent...")
            self._init_agent()

            self._is_initialized = True
            logger.info("ServiceContainer initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize ServiceContainer: {e}", exc_info=True)
            await self.shutdown()
            raise

    def _init_database(self) -> None:
        """Initialize PostgreSQL database connection."""
        try:
            self._db = PostgresDb(db_url=settings.database_url)
            logger.info("Database connection pool created")
        except Exception as e:
            raise RuntimeError(f"Database initialization failed: {e}") from e

    def _init_agent(self) -> None:
        """Initialize the learning agent with proper configuration."""
        if self._db is None:
            raise RuntimeError("Database must be initialized before agent")

        learning_mode = LearningMode[settings.learning_mode.upper()]

        self._agent = Agent(
            model=Claude(
                id=settings.llm_model_id,
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_request_timeout,
            ),
            db=self._db,
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
        logger.info(
            f"Learning agent initialized with model={settings.llm_model_id}, "
            f"learning_mode={settings.learning_mode}"
        )

    async def shutdown(self) -> None:
        """
        Clean up resources.
        
        Called during app shutdown. Closes database connections and
        cleans up the agent.
        """
        if not self._is_initialized:
            return

        try:
            logger.info("Shutting down ServiceContainer...")

            if self._db is not None:
                try:
                    
                    if hasattr(self._db, "close"):
                        self._db.close()  
                    logger.info("Database connection closed")
                except Exception as e:
                    logger.warning(f"Error closing database: {e}")

            self._db = None
            self._agent = None
            self._is_initialized = False
            logger.info("ServiceContainer shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


def get_service_container() -> ServiceContainer:
    """Get the singleton service container instance."""
    return ServiceContainer()


@asynccontextmanager
async def lifespan_context(app):
    """
    FastAPI lifespan context manager.
    
    Handles initialization on startup and cleanup on shutdown.
    """
    container = get_service_container()

    try:
        await container.initialize()
        logger.info("Application startup complete")
        yield
    finally:
        await container.shutdown()
        logger.info("Application shutdown complete")
