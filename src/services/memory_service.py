"""
MemoryService — unified service for all memory operations.
"""

import asyncio
import logging
from typing import Optional

from agno.agent import Agent

from src.core.config import settings
from src.core.errors import BadRequestError, ServiceError, LlmError
from src.domain.models import Message, SessionContext
from src.infrastructure.prompts import get_extraction_prompt, get_recall_prompt

logger = logging.getLogger(__name__)

_RECALL_SESSION_ID = "__recall__"


class MemoryService:
    """
    Unified service for memory extraction, recall, and curation.

    All public methods are async. Blocking agent.run() calls are offloaded
    to a thread pool via asyncio.to_thread so the event loop stays free.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def process_messages(
        self,
        context: SessionContext,
        messages: list[Message],
    ) -> None:
        """
        Extract cross-session knowledge from a conversation.

        Args:
            context: Session context (user_id, session_id, channel)
            messages: List of conversation messages

        Raises:
            BadRequestError: If messages list is empty
            LlmError: If the LLM times out or returns an error
            ServiceError: For any other failure
        """
        if not messages:
            raise BadRequestError("No messages provided")

        conversation_text = "\n".join(str(m) for m in messages)
        prompt = get_extraction_prompt(context.channel, context.session_id, conversation_text)
        extraction_session_id = f"extract_{context.session_id}"

        logger.info(
            f"Processing {len(messages)} messages for user={context.user_id}, "
            f"channel={context.channel}"
        )

        try:
            await asyncio.to_thread(
                self._agent.run,
                prompt,
                user_id=context.user_id,
                session_id=extraction_session_id,
            )
            logger.info(f"Successfully processed messages for user={context.user_id}")
        except Exception as e:
            self._raise_agent_error(e)

    async def recall_context(self, context: SessionContext) -> Optional[str]:
        """
        Recall relevant context for a user in a new session.

        Uses a fixed recall session ID to avoid accumulating ghost sessions.

        Args:
            context: Session context (user_id, channel)

        Returns:
            Briefing string if memories exist, None otherwise

        Raises:
            LlmError: If the LLM times out or returns an error
            ServiceError: For any other failure
        """
        prompt = get_recall_prompt(context.channel)

        logger.info(f"Recalling context for user={context.user_id}, channel={context.channel}")

        try:
            response = await asyncio.to_thread(
                self._agent.run,
                prompt,
                user_id=context.user_id,
                session_id=_RECALL_SESSION_ID,
            )
        except Exception as e:
            self._raise_agent_error(e)

        content = self._extract_content(response)

        if content and content.strip().upper() == "NO_MEMORY":
            content = None

        logger.info(
            f"Recalled context for user={context.user_id}, length={len(content or '')} chars"
        )
        return content or None

    async def clear_memory(self, user_id: str) -> None:
        """
        Delete all memory for a given user.

        Note: max_age_days=0 behaviour depends on the Agno implementation.
        It may not delete records created today — verify against your Agno version.

        Args:
            user_id: User identifier

        Raises:
            ServiceError: If the curator is unavailable or the operation fails
        """
        logger.info(f"Clearing all memory for user={user_id}")

        try:
            lm = self._agent.get_learning_machine()
            if lm is None:
                raise ServiceError("Learning machine not available on agent")

            curator = lm.curator
            if curator is None:
                raise ServiceError("Memory curator not available on learning machine")

            await asyncio.to_thread(curator.prune, user_id=user_id, max_age_days=0)
            logger.info(f"Successfully cleared memory for user={user_id}")

        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to clear memory for user={user_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to clear memory: {e}") from e

    @staticmethod
    def _extract_content(response) -> Optional[str]:
        """Extract text content from an agent response, returning None if empty."""
        if response is None:
            logger.warning("Agent returned None response")
            return None

        if not hasattr(response, "content"):
            logger.warning(f"Agent response missing 'content' attribute: {type(response)}")
            return None

        content = response.content
        if not content:
            return None

        text = str(content).strip()
        return text if text else None

    @staticmethod
    def _raise_agent_error(exc: Exception) -> None:
        """Translate agent exceptions into typed API errors. Always raises."""
        msg = str(exc).lower()

        if "timeout" in msg or "timed out" in msg or "interrupted" in msg:
            raise LlmError(f"LLM timed out: {exc}") from exc

        if any(kw in msg for kw in ("database", "postgres", "psycopg")):
            raise ServiceError(f"Database error during agent call: {exc}") from exc

        raise ServiceError(f"{type(exc).__name__}: {exc}") from exc
