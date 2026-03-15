"""
Agno Memory Bridge API — Main application entry point.

Exposes REST endpoints for the OpenClaw bot to:
- /process: Extract and persist cross-session knowledge from conversations
- /recall: Retrieve relevant context for multi-channel sessions
- /memory/{user_id}: Clear user memory

This module coordinates dependency initialization, request routing,
and error handling.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.logging_config import setup_logging, get_logger
from src.core.config import settings
from src.infrastructure.dependencies import lifespan_context
from src.validation.schemas import (
    ProcessRequest,
    ProcessResponse,
    RecallRequest,
    RecallResponse,
    HealthResponse,
    ClearMemoryResponse,
    ErrorDetail,
)
from src.api.routes import endpoints
from src.core.errors import ApiException, handle_api_exception, handle_unexpected_error


setup_logging(settings.log_level)
logger = get_logger(__name__)


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan_context,
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
)

@app.exception_handler(ApiException)
async def api_exception_handler(request, exc: ApiException):
    """
    Handle domain exceptions (validation, business logic errors).
    
    Returns structured error response with safe message.
    """
    error_data = handle_api_exception(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_data,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    Handle unexpected exceptions.
    
    Logs full error and returns generic message to client.
    """
    error_data = handle_unexpected_error(exc)
    return JSONResponse(
        status_code=500,
        content=error_data,
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Returns service status. Use for liveness probes.",
)
async def health() -> HealthResponse:
    """Simple health check endpoint."""
    return await endpoints.health()


@app.post(
    "/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_200_OK,
    tags=["memory"],
    summary="Process conversation",
    description=(
        "Extract and persist cross-session knowledge from a conversation. "
        "This should be called after each user interaction to capture relevant facts."
    ),
)
async def process_messages(req: ProcessRequest, request: Request) -> ProcessResponse:
    """Process a conversation and extract knowledge for cross-session recall."""
    return await endpoints.process_messages(req, request)


@app.post(
    "/recall",
    response_model=RecallResponse,
    status_code=status.HTTP_200_OK,
    tags=["memory"],
    summary="Recall context",
    description=(
        "Retrieve relevant context and memories for a user in a new or continuing session. "
        "Returns concise briefing notes of facts that would be useful in the new channel."
    ),
)
async def recall_context(req: RecallRequest, request: Request) -> RecallResponse:
    """Recall relevant context for a user session."""
    return await endpoints.recall_context(req, request)


@app.delete(
    "/memory/{user_id}",
    response_model=ClearMemoryResponse,
    status_code=status.HTTP_200_OK,
    tags=["memory"],
    summary="Clear user memory",
    description="Delete all stored memories for a user. This operation is irreversible.",
)
async def clear_memory(user_id: str, request: Request) -> ClearMemoryResponse:
    """Clear all memories for a user."""
    return await endpoints.clear_memory(user_id, request)


