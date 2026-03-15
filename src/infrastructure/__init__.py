"""
Infrastructure layer for the memory bridge API.

Provides dependencies, prompts, and external service integration.
"""

from .dependencies import AppState, lifespan_context, get_agent
from .prompts import (
    get_extraction_prompt,
    get_recall_prompt,
    get_system_prompt,
)

__all__ = [
    "AppState",
    "lifespan_context",
    "get_agent",
    "get_extraction_prompt",
    "get_recall_prompt",
    "get_system_prompt",
]
