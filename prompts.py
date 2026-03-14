"""
Centralized prompt templates for the Agno Memory Bridge API.

All LLM prompts are defined here for easy management, versioning, and A/B testing.
Prompts use Python f-strings to include dynamic variables from config or context.
"""

from config import settings


class SystemPrompts:
    """System prompts that define agent behavior."""

    @staticmethod
    def memory_extractor() -> str:
        """
        System prompt for the learning agent during memory extraction.
        
        Instructs Claude to identify and persist only valuable cross-session facts.
        Used in ConversationProcessor.
        """
        return """You are a memory extraction engine for cross-session user assistance.

Your PRIMARY job is to identify and persistently store ONLY facts that would be 
VALUABLE TO ANOTHER SESSION of the same user on a DIFFERENT COMMUNICATION CHANNEL 
(WhatsApp, Slack, Telegram, Discord, Teams, etc.).

=== SAVE ===
✓ Names and preferred contact info
✓ Explicit preferences ("I prefer X over Y", "I hate Z")
✓ Decisions made ("I decided to...", "We agreed to...")
✓ Plans, projects, and upcoming milestones
✓ Meetings scheduled with dates/times
✓ Deadlines and important dates
✓ Facts about people (role, team, company)
✓ Facts about projects, companies, or tools they use
✓ Communication style preferences ("be more formal", "casual tone")

=== DO NOT SAVE ===
✗ Greetings, farewells, pleasantries
✗ Acknowledgments ("ok", "got it", "lol", "👍", "thanks")
✗ Questions without answers
✗ Vague statements ("sounds good", "interesting", "cool")
✗ Anything clearly temporary or session-specific
✗ Redundant updates of existing facts (only update if NEW information)

=== OUTPUT FORMAT ===
When recalling, return a CONCISE, STRUCTURED SUMMARY — not raw conversation history.
Think of it as "briefing notes" for a new session, organized by relevance.

Be selective: only surface facts that have material impact on the new conversation.
"""


class UserPrompts:
    """User-facing prompts for agent operations."""

    @staticmethod
    def extract_from_conversation(channel: str, session_id: str, conversation: str) -> str:
        """
        Build prompt for extracting knowledge from a conversation.
        
        Args:
            channel: Communication channel (whatsapp, slack, etc.)
            session_id: Unique session identifier
            conversation: Formatted conversation text
            
        Returns:
            Prompt for Claude to extract cross-session knowledge
        """
        return (
            f"Channel: {channel}\n"
            f"Session: {session_id}\n\n"
            f"Extract any cross-session knowledge from this conversation:\n\n"
            f"{conversation}"
        )

    @staticmethod
    def recall_user_context(
        channel: str,
        max_tokens: int = None,
        min_relevance_days: int = None,
    ) -> str:
        """
        Build prompt for recalling relevant context for a user.
        
        Args:
            channel: Communication channel the user is joining
            max_tokens: Maximum response length (from settings if None)
            min_relevance_days: Exclude memories older than this (from settings if None)
            
        Returns:
            Prompt for Claude to produce context briefing
        """
        max_tokens = max_tokens or settings.recall_max_tokens
        min_relevance_days = min_relevance_days or settings.recall_min_relevance_days

        return (
            f"The user is starting or continuing a session on {channel}. "
            f"Produce a concise briefing (max {max_tokens} tokens) "
            f"of everything you know about this user that might be relevant: "
            f"profile facts, recent decisions, upcoming events, entity relationships. "
            f"Omit anything older than {min_relevance_days} days "
            f"unless it is a standing preference. "
            f"Format: short bullet points, present tense."
        )


def get_extraction_prompt(channel: str, session_id: str, conversation: str) -> str:
    """Get prompt for conversation analysis."""
    return UserPrompts.extract_from_conversation(channel, session_id, conversation)


def get_recall_prompt(channel: str) -> str:
    """Get prompt for context recall."""
    return UserPrompts.recall_user_context(channel)


def get_system_prompt() -> str:
    """Get system prompt for the learning agent."""
    return SystemPrompts.memory_extractor()
