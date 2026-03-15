"""
Tests for src/core/errors.py

Covers: all 4 exception classes, error codes, aliases, handler functions.
"""

import pytest
from fastapi import status

from src.core.errors import (
    ErrorCode,
    ErrorResponse,
    ApiException,
    BadRequestError,
    ServiceError,
    LlmError,
    UnavailableError,
    # Aliases
    ValidationError,
    MessageLimitError,
    MessageTooLongError,
    InvalidSessionIdError,
    InvalidUserIdError,
    InvalidChannelError,
    DatabaseError,
    LearningMachineError,
    InternalServerError,
    # Handlers
    handle_api_exception,
    handle_unexpected_error,
)


class TestErrorCode:
    def test_values(self):
        assert ErrorCode.BAD_REQUEST == "bad_request"
        assert ErrorCode.SERVICE_ERROR == "service_error"
        assert ErrorCode.LLM_ERROR == "llm_error"
        assert ErrorCode.SERVICE_UNAVAILABLE == "service_unavailable"


class TestErrorResponse:
    def test_serialization(self):
        resp = ErrorResponse(error=ErrorCode.BAD_REQUEST, message="bad")
        d = resp.model_dump(exclude_none=True)
        assert d == {"error": "bad_request", "message": "bad"}

    def test_serialization_with_detail(self):
        resp = ErrorResponse(error=ErrorCode.SERVICE_ERROR, message="err", detail="stack")
        d = resp.model_dump()
        assert d["detail"] == "stack"


class TestBadRequestError:
    def test_defaults(self):
        err = BadRequestError("invalid field")
        assert err.status_code == status.HTTP_400_BAD_REQUEST
        assert err.error_code == ErrorCode.BAD_REQUEST
        assert err.message == "invalid field"
        assert err.internal_detail == "invalid field"

    def test_custom_internal_detail(self):
        err = BadRequestError("bad", internal_detail="field X is null")
        assert err.internal_detail == "field X is null"


class TestServiceError:
    def test_defaults(self):
        err = ServiceError("db crashed")
        assert err.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert err.error_code == ErrorCode.SERVICE_ERROR
        assert "internal error" in err.message.lower()
        assert err.internal_detail == "db crashed"


class TestLlmError:
    def test_defaults(self):
        err = LlmError("timeout after 30s")
        assert err.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert err.error_code == ErrorCode.LLM_ERROR
        assert "llm" in err.message.lower()
        assert err.internal_detail == "timeout after 30s"


class TestUnavailableError:
    def test_defaults(self):
        err = UnavailableError()
        assert err.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert err.error_code == ErrorCode.SERVICE_UNAVAILABLE
        assert "unavailable" in err.message.lower()

    def test_custom_detail(self):
        err = UnavailableError("postgres not ready")
        assert err.internal_detail == "postgres not ready"


class TestAliases:
    """Legacy aliases must resolve to the collapsed classes."""

    def test_validation_aliases_are_bad_request(self):
        assert ValidationError is BadRequestError
        assert MessageLimitError is BadRequestError
        assert MessageTooLongError is BadRequestError
        assert InvalidSessionIdError is BadRequestError
        assert InvalidUserIdError is BadRequestError
        assert InvalidChannelError is BadRequestError

    def test_service_aliases(self):
        assert DatabaseError is ServiceError
        assert LearningMachineError is ServiceError
        assert InternalServerError is ServiceError


class TestHandleApiException:
    def test_returns_safe_response(self):
        exc = BadRequestError("bad input")
        result = handle_api_exception(exc)
        assert result["error"] == "bad_request"
        assert result["message"] == "bad input"
        assert "detail" not in result  # internal detail is NOT exposed

    def test_service_error_hides_detail(self):
        exc = ServiceError("secret stack trace")
        result = handle_api_exception(exc)
        assert "secret" not in result["message"]
        assert result["error"] == "service_error"


class TestHandleUnexpectedError:
    def test_returns_generic_response(self):
        exc = RuntimeError("something blew up")
        result = handle_unexpected_error(exc)
        assert result["error"] == "service_error"
        assert "something blew up" not in result["message"]
        assert "internal error" in result["message"].lower()
