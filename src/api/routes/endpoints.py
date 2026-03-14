"""
API endpoints for the Agno Memory Bridge API.

Exposes REST endpoints for:
- /process: Extract and persist cross-session knowledge from conversations
- /recall: Retrieve relevant context for multi-channel sessions
- /memory/{user_id}: Clear user memory
- /health: Health check
"""

import logging
from fastapi import HTTPException, status

from src.core.errors import ApiException, handle_api_exception, handle_unexpected_error
from src.core.config import settings
from src.infrastructure.dependencies import get_service_container
from src.validation.schemas import (
    ProcessRequest,
    ProcessResponse,
    RecallRequest,
    RecallResponse,
    HealthResponse,
    ClearMemoryResponse,
    MessageRequest,
)
from src.domain.models import Message, SessionContext
from src.services import ConversationProcessor, ContextRecall, MemoryCurator

logger = logging.getLogger(__name__)


async def health() -> HealthResponse:
    """
    Simple health check endpoint.
    
    Returns 200 OK if the service is running and responding.
    Does not validate database connectivity.
    """
    return HealthResponse(status="ok")


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
