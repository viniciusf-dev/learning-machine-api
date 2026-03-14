"""
Context recall service for retrieving user memories.

Handles recalling relevant context for new sessions.
"""

import logging
from agno.agent import Agent

from src.core.errors import LearningMachineError, LlmError
from src.domain.models import SessionContext
from src.infrastructure.prompts import get_recall_prompt

logger = logging.getLogger(__name__)


class ContextRecall:
    """
    Handles context recall for new sessions.
    
    Responsibilities:
    - Build recall prompts
    - Call the learning agent
    - Parse and validate responses
    - Handle errors
    """

    RECALL_SESSION_PREFIX = "recall"

    def __init__(self, agent: Agent):
        self.agent = agent
        logger.debug("ContextRecall initialized")

    def recall_context(self, context: SessionContext) -> str:
        """
        Recall relevant context for a user in a new session.
        
        Args:
            context: Session context (user_id, session_id, channel)
            
        Returns:
            Concise briefing of relevant user context and memory
            
        Raises:
            LearningMachineError: If recall operation fails
            LlmError: If LLM service fails
        """
        prompt = self._build_recall_prompt(context)

        try:
            logger.info(
                f"Recalling context for user={context.user_id}, "
                f"channel={context.channel}"
            )

            response = self.agent.run(
                prompt,
                user_id=context.user_id,
                session_id=self._make_recall_session_id(context.session_id),
            )

            context_text = self._extract_response_content(response)

            logger.info(
                f"Successfully recalled context for user={context.user_id}, "
                f"length={len(context_text)} chars"
            )

            return context_text

        except Exception as e:
            logger.error(
                f"Failed to recall context: {e}",
                extra={"user_id": context.user_id, "channel": context.channel},
                exc_info=True,
            )
            self._handle_agent_error(e)

    def _build_recall_prompt(self, context: SessionContext) -> str:
        """
        Build the prompt for context recall.
        
        Constructs the prompt that will be sent to Claude to produce a briefing
        of relevant user context and memories. Factored out to enable easy
        testing and prompt adjustments. Uses configured settings for token limit
        and relevance window.
        
        Args:
            context: Session context with channel for contextualized response
            
        Returns:
            Prompt string ready for Claude API
        """
        return get_recall_prompt(context.channel)

    @staticmethod
    def _make_recall_session_id(session_id: str) -> str:
        """
        Create a unique session ID for the recall request.
        
        Prevents conflicts with regular conversation sessions by prefixing
        the session ID with 'recall_'.
        
        Args:
            session_id: Original session identifier
            
        Returns:
            Prefixed session ID for recall operation
        """
        return f"{ContextRecall.RECALL_SESSION_PREFIX}_{session_id}"

    @staticmethod
    def _extract_response_content(response) -> str:
        """
        Extract content from agent response safely.
        
        Safely extracts content from agent response with multiple null checks
        and graceful degradation. Returns empty string if response is None,
        missing content attribute, or content is None.
        
        Args:
            response: Response object from agent.run()
            
        Returns:
            Extracted and stripped content string, empty string if no content found
        """
        if response is None:
            logger.warning("Agent returned None response")
            return ""

        if not hasattr(response, "content"):
            logger.warning(
                f"Agent response missing 'content' attribute: {type(response)}"
            )
            return ""

        content = response.content
        if content is None:
            logger.warning("Agent response.content is None")
            return ""

        return str(content).strip()

    @staticmethod
    def _handle_agent_error(exc: Exception) -> None:
        """
        Translate agent/LLM errors into typed API exceptions.
        
        Maps implementation errors from the Agno agent/Claude to domain-level
        exceptions that the API layer can handle appropriately. Checks error
        message for known patterns to determine exception type.
        
        Args:
            exc: Exception from agent.run() call
            
        Raises:
            LearningMachineError: If error is database/Postgres related
            LlmError: If error is Claude/timeout related
            LearningMachineError: For all other errors (fallback)
        """
        exc_type = type(exc).__name__
        exc_msg = str(exc)

        if "database" in exc_msg.lower() or "postgres" in exc_msg.lower():
            raise LearningMachineError(f"Database error: {exc_msg}") from exc

        if "timeout" in exc_msg.lower() or "claude" in exc_msg.lower():
            raise LlmError(f"LLM service error: {exc_msg}") from exc

        raise LearningMachineError(f"{exc_type}: {exc_msg}") from exc
