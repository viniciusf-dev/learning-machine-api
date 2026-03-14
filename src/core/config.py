"""
Configuration management for Agno Memory Bridge API.

Centralizes all environment variables, model parameters, and service settings
with strong typing and validation through Pydantic.
"""

from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Database configuration
    postgres_user: str = Field(default="agno_user", description="PostgreSQL user")
    postgres_password: str = Field(default="agno_password", description="PostgreSQL password")
    postgres_db: str = Field(default="agno_memory", description="PostgreSQL database name")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")

    api_host: str = Field(default="0.0.0.0", description="API bind host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API bind port")
    api_title: str = Field(
        default="OpenClaw <> Agno Memory Bridge",
        description="API title for OpenAPI docs"
    )
    api_version: str = Field(default="1.0.0", description="API semantic version")

    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude model access"
    )
    llm_model_id: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model ID to use for extraction and recall"
    )
    llm_request_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds for LLM calls"
    )

    learning_mode: Literal["always", "never", "smart"] = Field(
        default="always",
        description="Learning mode for user profile and memory updates"
    )
    enable_entity_memory: bool = Field(
        default=True,
        description="Enable entity (people, projects, etc.) memory tracking"
    )

    recall_max_tokens: int = Field(
        default=300,
        ge=50,
        le=2000,
        description="Maximum tokens in recall response"
    )
    recall_min_relevance_days: int = Field(
        default=30,
        ge=1,
        le=3650,
        description="Exclude memories older than this unless they are standing preferences"
    )

    max_messages_per_request: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of messages allowed in a single /process request"
    )
    max_message_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum characters per message"
    )
    max_session_id_length: int = Field(
        default=255,
        ge=10,
        le=1000,
        description="Maximum session_id length"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling (for development)"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable prometheus-style metrics"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Build database URL from components."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @field_validator("llm_model_id")
    @classmethod
    def validate_llm_model(cls, v: str) -> str:
        """Validate LLM model ID."""
        if not v or not v.strip():
            raise ValueError("llm_model_id cannot be empty")
        return v.strip()


settings = Settings()
