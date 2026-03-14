"""
Error handling and exception types for the Agno Memory Bridge API.

Defines custom exceptions and provides structured error responses
with proper logging and safe error disclosure.
"""

import logging
from typing import Any, Optional
from enum import Enum

from fastapi import status


logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """
    Enumeration of internal error codes for structured error reporting.
    
    Clients can use these to determine root cause without exposing
    implementation details.
    """

    INVALID_REQUEST = "invalid_request"
    VALIDATION_FAILED = "validation_failed"
    MESSAGE_LIMIT_EXCEEDED = "message_limit_exceeded"
    MESSAGE_TOO_LONG = "message_too_long"
    INVALID_SESSION_ID = "invalid_session_id"
    INVALID_USER_ID = "invalid_user_id"
    INVALID_CHANNEL = "invalid_channel"

    DATABASE_ERROR = "database_error"
    LEARNING_MACHINE_ERROR = "learning_machine_error"
    LLM_ERROR = "llm_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse:
    """
    Standard error response structure.
    
    Provides consistent error format across all endpoints with:
    - error_code: machine-readable code for client-side handling
    - message: user-facing message (safe to display)
    - detail: internal details (only in debug mode, excluded in production)
    - request_id: for correlation in logs (TODO: implement request tracking)
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int,
        detail: Optional[str] = None,
        include_detail: bool = False,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = detail if include_detail else None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error response to JSON-serializable dictionary.
        
        Includes error code and message. Detail field is only included
        if explicitly set during initialization.
        
        Returns:
            Dictionary with keys: 'error', 'message', and optionally 'detail'
        """
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.detail:
            result["detail"] = self.detail
        return result


class ApiException(Exception):
    """Base exception for API-level errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int,
        internal_detail: Optional[str] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.internal_detail = internal_detail or str(self)
        super().__init__(self.message)


class ValidationError(ApiException):
    """Raised when request validation fails."""

    def __init__(self, message: str, internal_detail: Optional[str] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_FAILED,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=internal_detail,
        )


class MessageLimitError(ApiException):
    """Raised when message count exceeds limit."""

    def __init__(self, limit: int, received: int):
        super().__init__(
            error_code=ErrorCode.MESSAGE_LIMIT_EXCEEDED,
            message=f"Request contains {received} messages, maximum allowed is {limit}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=f"Message limit exceeded: {received} > {limit}",
        )


class MessageTooLongError(ApiException):
    """Raised when individual message exceeds length limit."""

    def __init__(self, limit: int, received: int):
        super().__init__(
            error_code=ErrorCode.MESSAGE_TOO_LONG,
            message=f"Message is too long ({received} chars), maximum is {limit}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=f"Message length exceeded: {received} > {limit}",
        )


class InvalidSessionIdError(ApiException):
    """Raised when session_id is invalid."""

    def __init__(self, session_id: str, reason: str = "Invalid format"):
        super().__init__(
            error_code=ErrorCode.INVALID_SESSION_ID,
            message="Invalid session_id format",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=f"Invalid session_id '{session_id}': {reason}",
        )


class InvalidUserIdError(ApiException):
    """Raised when user_id is invalid."""

    def __init__(self, user_id: str, reason: str = "Invalid format"):
        super().__init__(
            error_code=ErrorCode.INVALID_USER_ID,
            message="Invalid user_id format",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=f"Invalid user_id '{user_id}': {reason}",
        )


class InvalidChannelError(ApiException):
    """Raised when channel is invalid."""

    def __init__(self, channel: str, valid_channels: Optional[list[str]] = None):
        channels_str = ", ".join(valid_channels) if valid_channels else "unknown"
        super().__init__(
            error_code=ErrorCode.INVALID_CHANNEL,
            message=f"Invalid channel. Supported: {channels_str}",
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=f"Unsupported channel: {channel}",
        )


class DatabaseError(ApiException):
    """Raised when database operations fail."""

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message="Database operation failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


class LearningMachineError(ApiException):
    """Raised when learning machine operations fail."""

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.LEARNING_MACHINE_ERROR,
            message="Learning machine operation failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


class LlmError(ApiException):
    """Raised when LLM (Claude) operations fail."""

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.LLM_ERROR,
            message="LLM service operation failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


class ServiceUnavailableError(ApiException):
    """Raised when a required service is temporarily unavailable."""

    def __init__(self, service: str, internal_detail: Optional[str] = None):
        super().__init__(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message=f"Service temporarily unavailable: {service}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            internal_detail=internal_detail or f"{service} is not responding",
        )


class InternalServerError(ApiException):
    """Raised for unexpected internal errors."""

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An internal error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


def handle_api_exception(exc: ApiException) -> dict[str, Any]:
    """
    Handle an ApiException and return a safe error response.
    
    Logs the full internal details for debugging while returning
    a safe message to the client. Internal details are never exposed
    in the response to prevent information leakage.
    
    Args:
        exc: The ApiException to handle
        
    Returns:
        Safe error response dictionary suitable for JSON response
    """
    logger.error(
        f"API Error [{exc.error_code}]: {exc.internal_detail}",
        extra={"error_code": exc.error_code, "status_code": exc.status_code},
    )

    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        detail=None,
    )

    return error_response.to_dict()


def handle_unexpected_error(exc: Exception) -> dict[str, Any]:
    """
    Handle an unexpected exception that isn't an ApiException.
    
    Logs full traceback for debugging while returning a generic error
    message to the client. Never exposes implementation details.
    
    Args:
        exc: The unexpected exception
        
    Returns:
        Generic error response dictionary suitable for JSON response
    """
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )

    error_response = ErrorResponse(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=None,
    )

    return error_response.to_dict()
