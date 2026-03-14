"""
Conversation processing service for memory extraction.

Handles validation and processing of conversations to extract cross-session knowledge.
"""

import logging
from agno.agent import Agent

from src.core.errors import LearningMachineError, LlmError, ValidationError, MessageLimitError
from src.domain.models import Message, SessionContext
from src.infrastructure.prompts import get_extraction_prompt
from src.core.config import settings

logger = logging.getLogger(__name__)


class ConversationProcessor:
    """
    Handles memory extraction from conversations.
    
    Responsibilities:
    - Validate and normalize conversation messages
    - Construct extraction prompts
    - Call the learning agent
    - Handle errors gracefully
    """

    EXTRACTION_SESSION_PREFIX = "extract"

    def __init__(self, agent: Agent):
        self.agent = agent
        logger.debug("ConversationProcessor initialized")

    def process_messages(
        self,
        context: SessionContext,
        messages: list[Message],
    ) -> None:
        """
        Process a conversation and extract cross-session knowledge.
        
        Args:
            context: Session context (user_id, session_id, channel)
            messages: List of messages in the conversation
            
        Raises:
            ValidationError: If messages are invalid
            LearningMachineError: If extraction fails
            LlmError: If LLM service fails
        """
        self._validate_messages(messages)

        conversation_text = self._format_conversation(messages)
        prompt = self._build_extraction_prompt(context, conversation_text)

        try:
            logger.info(
                f"Processing {len(messages)} messages for user={context.user_id}, "
                f"channel={context.channel}"
            )

            self.agent.run(
                prompt,
                user_id=context.user_id,
                session_id=self._make_extraction_session_id(context.session_id),
            )

            logger.info(
                f"Successfully processed messages for user={context.user_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process messages: {e}",
                extra={"user_id": context.user_id, "channel": context.channel},
                exc_info=True,
            )
            self._handle_agent_error(e)

    @staticmethod
    def _validate_messages(messages: list[Message]) -> None:
        """
        Validate message list.
        
        Ensures the list is not empty and doesn't exceed configured limit.
        
        Args:
            messages: List of Message objects to validate
            
        Raises:
            ValidationError: If messages list is empty
            MessageLimitError: If message count exceeds configured limit
        """
        if not messages:
            raise ValidationError("No messages provided")

        if len(messages) > settings.max_messages_per_request:
            raise MessageLimitError(
                settings.max_messages_per_request,
                len(messages),
            )

    @staticmethod
    def _format_conversation(messages: list[Message]) -> str:
        """
        Format messages into a readable conversation string.
        
        Converts list of Message objects into formatted text suitable
        for passing to the LLM.
        
        Args:
            messages: List of Message objects
            
        Returns:
            Clean conversation text with each message on new line
        """
        return "\n".join(str(m) for m in messages)

    @staticmethod
    def _build_extraction_prompt(context: SessionContext, conversation: str) -> str:
        """
        Build the prompt for memory extraction.
        
        Constructs the prompt that will be sent to Claude to extract
        cross-session knowledge from a conversation. Factored out to enable
        easy testing and prompt adjustments.
        
        Args:
            context: Session context with channel and session_id
            conversation: Formatted conversation text
            
        Returns:
            Prompt string ready for Claude API
        """
        return get_extraction_prompt(context.channel, context.session_id, conversation)

    @staticmethod
    def _make_extraction_session_id(session_id: str) -> str:
        """
        Create a unique session ID for the extraction request.
        
        Prevents conflicts with regular conversation sessions by prefixing
        the session ID with 'extract_'.
        
        Args:
            session_id: Original session identifier
            
        Returns:
            Prefixed session ID for extraction operation
        """
        return f"{ConversationProcessor.EXTRACTION_SESSION_PREFIX}_{session_id}"

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
