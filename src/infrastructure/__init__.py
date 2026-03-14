"""
Infrastructure layer for the memory bridge API.

Provides dependencies, prompts, and external service integration.
"""

from .dependencies import ServiceContainer, get_service_container, lifespan_context
from .prompts import (
    SystemPrompts,
    UserPrompts,
    get_extraction_prompt,
    get_recall_prompt,
    get_system_prompt,
)

__all__ = [
    "ServiceContainer",
    "get_service_container",
    "lifespan_context",
    "SystemPrompts",
    "UserPrompts",
    "get_extraction_prompt",
    "get_recall_prompt",
    "get_system_prompt",
]
