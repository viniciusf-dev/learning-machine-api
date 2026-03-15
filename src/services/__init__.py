"""
Business logic services for the memory bridge API.

MemoryService is the single entry point for all memory operations
(process, recall, clear).
"""

from .memory_service import MemoryService

__all__ = ["MemoryService"]
