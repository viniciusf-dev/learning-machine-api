"""
Domain models and enums for the memory bridge API.

Provides core data structures representing users, sessions, and messages.
"""

from .models import Channel, Message, SessionContext, VALID_CHANNELS

__all__ = [
    "Channel",
    "Message",
    "SessionContext",
    "VALID_CHANNELS",
]
