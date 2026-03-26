"""
API request and response schemas.
"""

from src.core.config import settings
from src.domain.models import Channel

from typing import Optional, List

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    ValidationInfo,
)


class MessageRequest(BaseModel):
    """
    A single message in a conversation.
    
    Constraints:
    - role: non-empty string (e.g., "user", "assistant")
    - content: non-empty string, validated against max_message_length in config
    """

    role: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Message sender role (e.g. 'user', 'assistant', 'system')",
        examples=["user", "assistant"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Message content (validated against max_message_length in config)",
        examples=["Hello, how are you?"],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Normalize role to lowercase."""
        return v.strip().lower()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str, info: ValidationInfo) -> str:
        """
        Validate content length against config.
        
        This ensures runtime validation regardless of Pydantic config.
        """
        from src.core.config import settings

        if len(v) > settings.max_message_length:
            raise ValueError(
                f"Content exceeds maximum length of {settings.max_message_length} characters"
            )
        return v.strip()


class ProcessRequest(BaseModel):
    """
    Request to process and extract knowledge from a conversation.
    
    Constraints:
    - user_id: non-empty string, max 255 chars
    - session_id: non-empty string, max 255 chars
    - channel: one of {whatsapp, slack, telegram, discord, teams}
    - messages: 1-100 message objects (configurable)
    """

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique user identifier",
        examples=["user_12345"],
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique session identifier",
        examples=["session_abc123"],
    )
    channel: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Communication channel (whatsapp, slack, telegram, discord, teams)",
        examples=["whatsapp"],
    )
    messages: List[MessageRequest] = Field(
        ...,
        min_length=1,
        description="List of messages in the conversation",
    )

    @field_validator("user_id", "session_id", "channel", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """
        Normalize string fields by stripping whitespace.
        
        Applied before other validators to ensure clean input for validation.
        
        Args:
            v: String value from request
            
        Returns:
            Stripped string or original value if not a string
        """
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages_count(cls, v: List[MessageRequest]) -> List[MessageRequest]:
        """
        Validate message count against configured limit.
        
        Prevents DoS attacks by limiting messages per request.
        
        Args:
            v: List of messages from request
            
        Returns:
            Same list if valid
            
        Raises:
            ValueError: If message count exceeds limit
        """

        if len(v) > settings.max_messages_per_request:
            raise ValueError(
                f"Request contains {len(v)} messages, "
                f"maximum allowed is {settings.max_messages_per_request}"
            )
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """Validate channel is in supported list."""
        valid_channels = {ch.value for ch in Channel}
        v_lower = v.lower()
        if v_lower not in valid_channels:
            raise ValueError(
                f"Unsupported channel '{v}'. "
                f"Must be one of: {', '.join(sorted(valid_channels))}"
            )
        return v_lower


class ProcessResponse(BaseModel):
    """
    Response from processing a conversation.
    
    Indicates successful processing without revealing internal details.
    """

    status: str = Field(
        ...,
        description="Operation status: processed or skipped",
        examples=["processed"],
    )
    reason: Optional[str] = Field(
        default=None,
        description="If status=skipped, reason for skipping",
        examples=["no messages"],
    )


class RecallRequest(BaseModel):
    """
    Request to recall context for a new or continuing session.
    
    Constraints:
    - user_id: non-empty string, max 255 chars
    - session_id: non-empty string, max 255 chars
    - channel: one of {whatsapp, slack, telegram, discord, teams}
    """

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique user identifier",
        examples=["user_12345"],
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique session identifier",
        examples=["session_xyz789"],
    )
    channel: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Communication channel (whatsapp, slack, telegram, discord, teams)",
        examples=["slack"],
    )

    @field_validator("user_id", "session_id", "channel", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """
        Normalize string fields by stripping whitespace.
        
        Applied before other validators to ensure clean input for validation.
        
        Args:
            v: String value from request
            
        Returns:
            Stripped string or original value if not a string
        """
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        """
        Validate channel is in supported list.
        
        Ensures only known communication channels are processed.
        Normalizes to lowercase for consistency.
        
        Args:
            v: Channel name from request
            
        Returns:
            Normalized (lowercase) channel name
            
        Raises:
            ValueError: If channel not in Channel enum values
        """
        valid_channels = {ch.value for ch in Channel}
        v_lower = v.lower()
        if v_lower not in valid_channels:
            raise ValueError(
                f"Unsupported channel '{v}'. "
                f"Must be one of: {', '.join(sorted(valid_channels))}"
            )
        return v_lower


class RecallResponse(BaseModel):
    """
    Response containing recalled context for a user session.

    - user_id: echoed back for correlation
    - context: concise briefing of relevant memories, or null when has_memory=False
    - has_memory: boolean indicating if any memories were found

    context is Optional[str] (not str) so that has_memory=False is semantically
    consistent: when there are no memories, context is None, not an empty string.
    """

    user_id: str = Field(
        ...,
        description="User identifier (echoed from request)",
        examples=["user_12345"],
    )
    context: Optional[str] = Field(
        default=None,
        description="Concise briefing of user context and memories, or null if none found",
        examples=["• Prefers Slack for quick updates\n• Working on Project X"],
    )
    has_memory: bool = Field(
        ...,
        description="Whether any memories were found for this user",
        examples=[True],
    )


class HealthResponse(BaseModel):
    """
    Health check response.
    
    Simple status indicator for liveness probes.
    """

    status: str = Field(
        ...,
        description="Service status",
        examples=["ok"],
    )


class ClearMemoryResponse(BaseModel):
    """
    Response from clearing user memory.
    
    Confirms the operation and echoes the user_id.
    """

    status: str = Field(
        ...,
        description="Operation status",
        examples=["cleared"],
    )
    user_id: str = Field(
        ...,
        description="User identifier (echoed from request)",
        examples=["user_12345"],
    )


class ErrorDetail(BaseModel):
    """
    Standard error response format.
    
    Provides error code and message without exposing internal details.
    """

    error: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["validation_failed"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Invalid session_id format"],
    )
    detail: Optional[str] = Field(
        default=None,
        description="Additional technical details (debug only)",
    )
