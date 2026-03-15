"""
Core module with configuration, logging, and error handling.

Provides foundational services used throughout the application.
"""

from .config import settings, Settings
from .logging_config import setup_logging, get_logger, StructuredFormatter
from .errors import (
    ErrorCode,
    ErrorResponse,
    ApiException,
    BadRequestError,
    ServiceError,
    LlmError,
    UnavailableError,
    handle_api_exception,
    handle_unexpected_error,
)

__all__ = [
    "settings",
    "Settings",
    "setup_logging",
    "get_logger",
    "StructuredFormatter",
    "ErrorCode",
    "ErrorResponse",
    "ApiException",
    "BadRequestError",
    "ServiceError",
    "LlmError",
    "UnavailableError",
    "handle_api_exception",
    "handle_unexpected_error",
]
