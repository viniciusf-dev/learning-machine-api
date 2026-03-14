"""
Agno Memory Bridge API — Main application entry point.

Exposes REST endpoints for the OpenClaw bot to:
- /process: Extract and persist cross-session knowledge from conversations
- /recall: Retrieve relevant context for multi-channel sessions
- /memory/{user_id}: Clear user memory

This module coordinates dependency initialization, request routing,
and error handling. Business logic is delegated to service layer.
"""

import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from logging_config import setup_logging, get_logger
from config import settings
from dependencies import lifespan_context, get_service_container
from api_schemas import (
    ProcessRequest,
    ProcessResponse,
    RecallRequest,
    RecallResponse,
    HealthResponse,
    ClearMemoryResponse,
    ErrorDetail,
    MessageRequest,
)
from service import (
    Message,
    SessionContext,
    ConversationProcessor,
    ContextRecall,
    MemoryCurator,
)
from errors import ApiException, handle_api_exception, handle_unexpected_error


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
    """
    Simple health check endpoint.
    
    Returns 200 OK if the service is running and responding.
    Does not validate database connectivity.
    """
    return HealthResponse(status="ok")


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
async def process_messages(req: ProcessRequest) -> ProcessResponse:
    """
    Process a conversation and extract knowledge for cross-session recall.
    
    Args:
        req: ProcessRequest containing user_id, session_id, channel, and messages
        
    Returns:
        ProcessResponse with status (processed or skipped)
        
    Raises:
        ValidationError: If request is invalid
        MessageLimitError: If message count exceeds limit
        MessageTooLongError: If any message is too long
        InvalidUserIdError: If user_id is invalid
        InvalidSessionIdError: If session_id is invalid
        InvalidChannelError: If channel is not supported
        LearningMachineError: If memory extraction fails
        LlmError: If LLM service fails
    """
    
    if not req.messages:
        logger.debug(f"Skipping process request: no messages for {req.user_id}")
        return ProcessResponse(status="skipped", reason="no messages")

    
    try:
        context = SessionContext(
            user_id=req.user_id,
            session_id=req.session_id,
            channel=req.channel,
        )

        messages = [
            Message(role=m.role, content=m.content)
            for m in req.messages
        ]
    except ApiException:
        raise

    
    container = get_service_container()
    if not container.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    processor = ConversationProcessor(container.agent)
    processor.process_messages(context, messages)

    return ProcessResponse(status="processed")

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
async def recall_context(req: RecallRequest) -> RecallResponse:
    """
    Recall relevant context for a user session.
    
    Args:
        req: RecallRequest containing user_id, session_id, and channel
        
    Returns:
        RecallResponse with recalled context and has_memory flag
        
    Raises:
        ValidationError: If request is invalid
        InvalidUserIdError: If user_id is invalid
        InvalidSessionIdError: If session_id is invalid
        InvalidChannelError: If channel is not supported
        LearningMachineError: If memory recall fails
        LlmError: If LLM service fails
    """
    
    try:
        context = SessionContext(
            user_id=req.user_id,
            session_id=req.session_id,
            channel=req.channel,
        )
    except ApiException:
        raise

   
    container = get_service_container()
    if not container.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    recall_service = ContextRecall(container.agent)
    recalled_context = recall_service.recall_context(context)

    return RecallResponse(
        user_id=req.user_id,
        context=recalled_context,
        has_memory=bool(recalled_context),
    )


@app.delete(
    "/memory/{user_id}",
    response_model=ClearMemoryResponse,
    status_code=status.HTTP_200_OK,
    tags=["memory"],
    summary="Clear user memory",
    description="Delete all stored memories for a user. This operation is irreversible.",
)
async def clear_memory(user_id: str) -> ClearMemoryResponse:
    """
    Clear all memories for a user.
    
    Permanently deletes all user profile data, memories, and entity information.
    This operation cannot be undone.
    
    Args:
        user_id: User identifier
        
    Returns:
        ClearMemoryResponse confirming the operation
        
    Raises:
        InvalidUserIdError: If user_id is invalid
        LearningMachineError: If clearing fails
    """
    
    try:
        SessionContext._validate_user_id(user_id)
    except ApiException:
        raise

    container = get_service_container()
    if not container.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )

    curator = MemoryCurator(container.agent)
    curator.clear_user_memory(user_id)

    logger.info(f"Memory cleared for user={user_id}")
    return ClearMemoryResponse(status="cleared", user_id=user_id)


@app.on_event("startup")
async def on_startup() -> None:
    """Log successful startup."""
    logger.info(
        f"Application started: {settings.api_title} v{settings.api_version}"
    )
    logger.info(f"Configuration: log_level={settings.log_level}, "
                f"llm_model={settings.llm_model_id}, "
                f"learning_mode={settings.learning_mode}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Log graceful shutdown."""
    logger.info("Application shutdown")