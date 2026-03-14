"""
Business logic layer for memory extraction and recall operations.

Separates core application logic from FastAPI request/response handling.
This enables easier testing, reuse, and changes without touching the API layer.
"""

import logging
from typing import Optional
from enum import Enum

from agno.agent import Agent

from errors import (
    ValidationError,
    MessageLimitError,
    MessageTooLongError,
    InvalidSessionIdError,
    InvalidUserIdError,
    InvalidChannelError,
    LearningMachineError,
    LlmError,
)
from config import settings
from prompts import get_extraction_prompt, get_recall_prompt


logger = logging.getLogger(__name__)


class Channel(str, Enum):
    """Supported communication channels."""

    WHATSAPP = "whatsapp"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    TEAMS = "teams"


VALID_CHANNELS = [ch.value for ch in Channel]


class Message:
    """Represents a single message in a conversation."""

    def __init__(self, role: str, content: str):
        self._validate(role, content)
        self.role = role
        self.content = content

    @staticmethod
    def _validate(role: str, content: str) -> None:
        """
        Validate message structure.
        
        Checks that role and content are non-empty strings and that
        content doesn't exceed configured maximum length.
        
        Args:
            role: Message sender role
            content: Message text content
            
        Raises:
            ValidationError: If role is empty or not a string
            ValidationError: If content is empty or not a string
            MessageTooLongError: If content exceeds max_message_length
        """
        if not role or not isinstance(role, str):
            raise ValidationError("Message role must be a non-empty string")

        if not content or not isinstance(content, str):
            raise ValidationError("Message content must be a non-empty string")

        if len(content) > settings.max_message_length:
            raise MessageTooLongError(settings.max_message_length, len(content))

    def __str__(self) -> str:
        """
        Format message for inclusion in conversation text.
        
        Returns a formatted string with role in uppercase and content.
        
        Returns:
            Formatted string like "[USER] Hello world"
        """
        return f"[{self.role.upper()}] {self.content}"


class SessionContext:
    """
    Represents a user session context.
    
    Encapsulates session identification and validation logic.
    """

    def __init__(
        self,
        user_id: str,
        session_id: str,
        channel: str,
    ):
        self._validate_user_id(user_id)
        self._validate_session_id(session_id)
        self._validate_channel(channel)

        self.user_id = user_id
        self.session_id = session_id
        self.channel = channel

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        """
        Validate user_id format.
        
        Ensures user_id is a non-empty string and doesn't exceed length limit.
        
        Args:
            user_id: User identifier to validate
            
        Raises:
            InvalidUserIdError: If user_id is empty, not a string, or too long
        """
        if not user_id or not isinstance(user_id, str):
            raise InvalidUserIdError(
                user_id or "null",
                reason="user_id must be a non-empty string",
            )
        if len(user_id) > 255:
            raise InvalidUserIdError(user_id, reason="user_id too long (max 255)")

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        """
        Validate session_id format.
        
        Ensures session_id is a non-empty string and doesn't exceed configured limit.
        
        Args:
            session_id: Session identifier to validate
            
        Raises:
            InvalidSessionIdError: If session_id is empty, not a string, or too long
        """
        if not session_id or not isinstance(session_id, str):
            raise InvalidSessionIdError(
                session_id or "null",
                reason="session_id must be a non-empty string",
            )
        if len(session_id) > settings.max_session_id_length:
            raise InvalidSessionIdError(
                session_id, reason="session_id too long"
            )

    @staticmethod
    def _validate_channel(channel: str) -> None:
        """
        Validate channel is in supported list.
        
        Ensures only known communication channels are processed.
        
        Args:
            channel: Channel name to validate
            
        Raises:
            InvalidChannelError: If channel not in {whatsapp, slack, telegram, discord, teams}
        """
        if channel not in VALID_CHANNELS:
            raise InvalidChannelError(channel, valid_channels=VALID_CHANNELS)


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


class MemoryCurator:
    """
    Handles memory management operations.
    
    Responsibilities:
    - Clearing user memories
    - Pruning old data
    - Error handling
    """

    def __init__(self, agent: Agent):
        self.agent = agent
        logger.debug("MemoryCurator initialized")

    def clear_user_memory(self, user_id: str) -> None:
        """
        Clear all memory for a user.
        
        Args:
            user_id: User identifier
            
        Raises:
            InvalidUserIdError: If user_id is invalid
            LearningMachineError: If operation fails
        """
        SessionContext._validate_user_id(user_id)

        try:
            logger.info(f"Clearing all memory for user={user_id}")

            lm = self.agent.get_learning_machine()
            if lm is None:
                raise LearningMachineError(
                    "Learning machine not available on agent"
                )

            curator = lm.curator
            if curator is None:
                raise LearningMachineError(
                    "Memory curator not available on learning machine"
                )

            curator.prune(user_id=user_id, max_age_days=0)

            logger.info(f"Successfully cleared memory for user={user_id}")

        except LearningMachineError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to clear memory for user={user_id}: {e}",
                exc_info=True,
            )
            raise LearningMachineError(f"Failed to clear memory: {str(e)}") from e
