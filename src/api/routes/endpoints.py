"""
API endpoints for the Agno Memory Bridge API.

All endpoints are async. I/O-bound work (Postgres + Claude) is offloaded
to threads inside MemoryService via asyncio.to_thread.
"""

import asyncio
import logging
from fastapi import Request

from src.core.errors import ApiException, UnavailableError, handle_api_exception, handle_unexpected_error
from src.infrastructure.dependencies import get_agent
from src.validation.schemas import (
    ProcessRequest,
    ProcessResponse,
    RecallRequest,
    RecallResponse,
    HealthResponse,
    ClearMemoryResponse,
)
from src.domain.models import Message, SessionContext
from src.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 120


async def health() -> HealthResponse:
    """Liveness probe. Returns 200 if the service is running."""
    return HealthResponse(status="ok")


async def process_messages(req: ProcessRequest, request: Request) -> ProcessResponse:
    """
    Process a conversation and extract knowledge for cross-session recall.

    Args:
        req: ProcessRequest with user_id, session_id, channel, and messages
        request: FastAPI request (used to access app.state)

    Returns:
        ProcessResponse with status
    """
    if not req.messages:
        return ProcessResponse(status="skipped", reason="no messages")

    agent = get_agent(request)
    context = SessionContext(
        user_id=req.user_id,
        session_id=req.session_id,
        channel=req.channel,
    )
    messages = [Message(role=m.role, content=m.content) for m in req.messages]

    service = MemoryService(agent)
    await asyncio.wait_for(
        service.process_messages(context, messages),
        timeout=_REQUEST_TIMEOUT,
    )

    return ProcessResponse(status="processed")


async def recall_context(req: RecallRequest, request: Request) -> RecallResponse:
    """
    Recall relevant context for a user session.

    Args:
        req: RecallRequest with user_id, session_id, and channel
        request: FastAPI request (used to access app.state)

    Returns:
        RecallResponse with optional context and has_memory flag
    """
    agent = get_agent(request)
    context = SessionContext(
        user_id=req.user_id,
        session_id=req.session_id,
        channel=req.channel,
    )

    service = MemoryService(agent)
    recalled = await asyncio.wait_for(
        service.recall_context(context),
        timeout=_REQUEST_TIMEOUT,
    )

    return RecallResponse(
        user_id=req.user_id,
        context=recalled,
        has_memory=recalled is not None,
    )


async def clear_memory(user_id: str, request: Request) -> ClearMemoryResponse:
    """
    Clear all memories for a user.

    user_id comes as a path parameter without Pydantic validation, so we
    validate it explicitly here via SessionContext.

    Args:
        user_id: User identifier (path parameter — validated manually)
        request: FastAPI request (used to access app.state)

    Returns:
        ClearMemoryResponse confirming the operation
    """
    
    SessionContext._validate_user_id(user_id)

    agent = get_agent(request)
    service = MemoryService(agent)
    await asyncio.wait_for(
        service.clear_memory(user_id),
        timeout=_REQUEST_TIMEOUT,
    )

    logger.info(f"Memory cleared for user={user_id}")
    return ClearMemoryResponse(status="cleared", user_id=user_id)
