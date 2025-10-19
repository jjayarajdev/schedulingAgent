"""
Configuration management using pydantic-settings.

Loads configuration from environment variables with validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # Application Settings
    # ============================================================================

    app_name: str = Field(default="scheduling-agent-bedrock", description="Application name")
    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev", description="Environment name"
    )
    debug: bool = Field(default=False, description="Debug mode")
    port: int = Field(default=8000, description="Application port")
    host: str = Field(default="0.0.0.0", description="Application host")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    workers: int = Field(default=1, description="Number of worker processes")

    # ============================================================================
    # Database Settings (PostgreSQL - Aurora Serverless v2)
    # ============================================================================

    database_url: str = Field(
        description="PostgreSQL connection URL (async driver)",
        examples=["postgresql+asyncpg://user:pass@localhost:5432/db"],
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(
        default=10, description="Max overflow connections in pool"
    )
    database_echo: bool = Field(default=False, description="Echo SQL queries")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses async driver."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use asyncpg driver (postgresql+asyncpg://)")
        return v

    # ============================================================================
    # Redis Settings (ElastiCache)
    # ============================================================================

    redis_url: str = Field(
        description="Redis connection URL",
        examples=["redis://localhost:6379/0"],
    )
    redis_session_ttl: int = Field(
        default=1800, description="Session TTL in seconds (30 minutes)"
    )
    redis_max_connections: int = Field(
        default=50, description="Max Redis connections in pool"
    )

    # ============================================================================
    # AWS Settings
    # ============================================================================

    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(
        default=None, description="AWS secret access key"
    )

    # AWS Bedrock
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20240620-v1:0",
        description="Bedrock model ID",
    )
    bedrock_agent_id: str | None = Field(default=None, description="Bedrock agent ID")
    bedrock_agent_alias_id: str | None = Field(
        default=None, description="Bedrock agent alias ID"
    )

    # AWS Secrets Manager
    aws_secrets_name: str = Field(
        default="scheduling-agent/secrets", description="Secrets Manager secret name"
    )

    # ============================================================================
    # PF360 API Settings
    # ============================================================================

    customer_scheduler_api_url: str = Field(
        description="PF360 API base URL",
        examples=["https://api.projectsforce.com"],
    )
    pf360_api_timeout: int = Field(default=30, description="PF360 API timeout in seconds")
    pf360_max_retries: int = Field(default=3, description="Max retries for PF360 API calls")
    confirm_schedule_flag: int = Field(default=1, description="Enable schedule confirmation")
    cancel_schedule_flag: int = Field(default=1, description="Enable schedule cancellation")

    # ============================================================================
    # Authentication & Security
    # ============================================================================

    jwt_secret_key: str = Field(description="JWT secret key for token signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=30, description="JWT expiration in minutes")
    secret_key: str = Field(description="Application secret key")

    # ============================================================================
    # Multi-Agent System Configuration
    # ============================================================================

    # Intent Classification
    intent_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for intent classification",
    )
    intent_fallback_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Fallback threshold for low confidence",
    )

    # Clarifier Agent
    max_clarification_attempts: int = Field(
        default=3, description="Max clarification attempts per session"
    )
    clarification_timeout_seconds: int = Field(
        default=300, description="Timeout for clarification in seconds"
    )

    # Session Management
    session_ttl_seconds: int = Field(
        default=1800, description="Session TTL in seconds (30 minutes)"
    )
    max_conversation_turns: int = Field(
        default=50, description="Max conversation turns per session"
    )

    # LLM Configuration
    max_tokens: int = Field(default=2000, description="Max tokens for LLM generation")
    llm_temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="LLM temperature"
    )
    llm_top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="LLM top-p sampling")
    llm_max_retries: int = Field(default=3, description="Max retries for LLM calls")

    # Tool Execution
    tool_timeout_seconds: int = Field(
        default=30, description="Timeout for tool execution in seconds"
    )
    tool_max_retries: int = Field(default=2, description="Max retries for tool execution")

    # ============================================================================
    # Logging & Observability
    # ============================================================================

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "console"] = Field(
        default="json", description="Log format"
    )
    enable_structured_logging: bool = Field(
        default=True, description="Enable structured logging"
    )

    # Tracing
    enable_tracing: bool = Field(default=True, description="Enable AWS X-Ray tracing")
    xray_sampling_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="X-Ray sampling rate"
    )

    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics endpoint port")

    # ============================================================================
    # Feature Flags
    # ============================================================================

    enable_conversation_history: bool = Field(
        default=True, description="Enable conversation history storage"
    )
    enable_intent_caching: bool = Field(
        default=True, description="Enable intent classification caching"
    )
    enable_response_streaming: bool = Field(
        default=False, description="Enable streaming responses"
    )
    enable_weather_tool: bool = Field(default=True, description="Enable weather tool")

    # ============================================================================
    # Rate Limiting & Performance
    # ============================================================================

    api_rate_limit_per_minute: int = Field(
        default=60, description="API rate limit per minute"
    )
    api_burst_size: int = Field(default=10, description="API burst size")
    max_concurrent_requests: int = Field(
        default=100, description="Max concurrent requests"
    )

    # ============================================================================
    # Testing Settings
    # ============================================================================

    test_database_url: str | None = Field(
        default=None, description="Test database URL"
    )
    test_redis_url: str | None = Field(default=None, description="Test Redis URL")

    # ============================================================================
    # Computed Properties
    # ============================================================================

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "dev"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "prod"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings (cached).

    Returns:
        Settings: Application settings instance
    """
    return Settings()
