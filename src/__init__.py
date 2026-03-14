"""
Agno Memory Bridge API - Cross-session memory management for multi-channel assistance.

This package provides REST endpoints for:
- Processing conversations to extract cross-session knowledge
- Recalling relevant context for new sessions
- Managing user memory

Architecture:
- domain: Data models (Channel, Message, SessionContext)
- services: Business logic (ConversationProcessor, ContextRecall, MemoryCurator)
- validation: Request/response schemas
- infrastructure: Dependencies, prompts, database
- api: FastAPI routes and endpoints
- core: Configuration, logging, error handling
"""
