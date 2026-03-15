"""
Domain models for the memory bridge API.

Provides core data structures representing communication channels, messages, and sessions.
"""

import logging
from typing import Optional
from enum import Enum

from src.core.config import settings
from src.core.errors import (
    ValidationError,
    MessageTooLongError,
    InvalidSessionIdError,
    InvalidUserIdError,
    InvalidChannelError,
)

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
            raise InvalidUserIdError("user_id must be a non-empty string")
        if len(user_id) > 255:
            raise InvalidUserIdError("user_id too long (max 255)")

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
            raise InvalidSessionIdError("session_id must be a non-empty string")
        if len(session_id) > settings.max_session_id_length:
            raise InvalidSessionIdError("session_id too long")

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
            raise InvalidChannelError(
                f"Unsupported channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}"
            )
