"""
Error handling and exception types for the Agno Memory Bridge API.

Hierarchy (4 classes — collapsed from 11):
  BadRequestError  → 400  (validation, invalid fields, limits)
  ServiceError     → 500  (LLM, learning machine, database)
  UnavailableError → 503  (service not ready)
  ApiException     → base (arbitrary code, for edge cases)

ErrorResponse is a plain Pydantic model — no intermediate class.
"""

import logging
from enum import Enum
from typing import Optional

from fastapi import status
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Machine-readable error codes for client-side handling."""

    # 400 family
    BAD_REQUEST = "bad_request"

    # 500 family
    SERVICE_ERROR = "service_error"
    LLM_ERROR = "llm_error"

    # 503
    SERVICE_UNAVAILABLE = "service_unavailable"


class ErrorResponse(BaseModel):
    """
    Standard error response — serialized directly to JSON.

    Using Pydantic ensures consistent shape and automatic OpenAPI docs.
    """

    error: ErrorCode
    message: str
    detail: Optional[str] = None


class ApiException(Exception):
    """Base exception for all API-level errors."""

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
        self.internal_detail = internal_detail or message
        super().__init__(self.message)


class BadRequestError(ApiException):
    """
    Raised for any client-side validation failure (400).

    Replaces: ValidationError, MessageLimitError, MessageTooLongError,
    InvalidSessionIdError, InvalidUserIdError, InvalidChannelError.
    The caller passes a descriptive message — no need for separate subclasses.
    """

    def __init__(self, message: str, internal_detail: Optional[str] = None):
        super().__init__(
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            internal_detail=internal_detail or message,
        )


class ServiceError(ApiException):
    """
    Raised when internal services fail (500).

    Replaces: DatabaseError, LearningMachineError, InternalServerError.
    The public message is always generic; detail is logged internally only.
    """

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.SERVICE_ERROR,
            message="An internal error occurred. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


class LlmError(ApiException):
    """
    Raised when the LLM (Claude) fails or times out (500).

    Kept separate from ServiceError so callers can distinguish
    LLM failures from database/infra failures if needed.
    """

    def __init__(self, internal_detail: str):
        super().__init__(
            error_code=ErrorCode.LLM_ERROR,
            message="LLM service unavailable. Please try again later.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            internal_detail=internal_detail,
        )


class UnavailableError(ApiException):
    """
    Raised when the service is not yet ready to handle requests (503).

    Replaces: ServiceUnavailableError.
    """

    def __init__(self, internal_detail: str = "Service not initialized"):
        super().__init__(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Service temporarily unavailable. Please try again shortly.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            internal_detail=internal_detail,
        )


# ---------------------------------------------------------------------------
# Keep legacy aliases so existing service code doesn't need mass-rename
# ---------------------------------------------------------------------------
ValidationError = BadRequestError
MessageLimitError = BadRequestError
MessageTooLongError = BadRequestError
InvalidSessionIdError = BadRequestError
InvalidUserIdError = BadRequestError
InvalidChannelError = BadRequestError
DatabaseError = ServiceError
LearningMachineError = ServiceError
InternalServerError = ServiceError


def handle_api_exception(exc: ApiException) -> dict:
    """
    Log internal details and return a safe client-facing error dict.

    Internal detail is never included in the response body.
    """
    logger.error(
        f"API Error [{exc.error_code}] (HTTP {exc.status_code}): {exc.internal_detail}"
    )
    return ErrorResponse(error=exc.error_code, message=exc.message).model_dump(exclude_none=True)


def handle_unexpected_error(exc: Exception) -> dict:
    """
    Log full traceback and return a generic error dict.

    Never exposes implementation details to the client.
    """
    logger.error(f"Unexpected error: {type(exc).__name__}: {exc}", exc_info=True)
    return ErrorResponse(
        error=ErrorCode.SERVICE_ERROR,
        message="An internal error occurred. Please try again later.",
    ).model_dump(exclude_none=True)
