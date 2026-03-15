"""
Custom Agno schemas for the OpenClaw cross-session memory bridge.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from agno.learn.schemas import UserProfile


@dataclass
class CrossSessionProfile(UserProfile):
    """Extended user profile for cross-channel assistant context."""

    preferred_channel: Optional[str] = field(
        default=None,
        metadata={"description": "User's preferred channel: whatsapp | slack | telegram | discord | teams"},
    )
    language: Optional[str] = field(
        default=None,
        metadata={"description": "User's preferred language, e.g. 'portuguese', 'english'"},
    )
    timezone: Optional[str] = field(
        default=None,
        metadata={"description": "User's timezone in IANA format, e.g. 'America/Sao_Paulo'"},
    )
    role: Optional[str] = field(
        default=None,
        metadata={"description": "Job title or role, e.g. 'Software Engineer', 'Product Manager'"},
    )
    company: Optional[str] = field(
        default=None,
        metadata={"description": "Company or organization the user works at"},
    )
    department: Optional[str] = field(
        default=None,
        metadata={"description": "Department: engineering | sales | marketing | product | etc."},
    )
    communication_style: Optional[str] = field(
        default=None,
        metadata={"description": "Preferred response style: formal | casual | technical | brief | detailed"},
    )
    topics_of_interest: Optional[List[str]] = field(
        default=None,
        metadata={"description": "List of recurring topics or domains the user frequently discusses"},
    )

