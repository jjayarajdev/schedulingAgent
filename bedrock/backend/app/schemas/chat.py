"""
Chat API request and response schemas.

Defines the structure for:
- Chat requests from clients
- Chat responses to clients
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """
    Chat request from client.

    Fields match current system (from api/routes.py).
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message",
        examples=["I want to schedule an appointment"],
    )

    session_id: str | UUID = Field(
        ...,
        description="Session ID (UUID or string)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    customer_id: int | str = Field(
        ...,
        description="Customer ID",
        examples=["1645975", 1645975],
    )

    client_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Client name",
        examples=["projectsforce-validation"],
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | UUID) -> str:
        """Convert session_id to string."""
        return str(v)

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: int | str) -> str:
        """Convert customer_id to string."""
        return str(v)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "message": "I want to schedule an appointment for next week",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "customer_id": "1645975",
                "client_name": "projectsforce-validation",
            }
        }


class ChatMetadata(BaseModel):
    """Metadata for chat response."""

    tools_executed: list[str] = Field(
        default_factory=list,
        description="List of tools executed during processing",
    )

    clarification_needed: bool = Field(
        default=False,
        description="Whether clarification was needed",
    )

    next_expected_intent: str | None = Field(
        default=None,
        description="Next expected intent in conversation flow",
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Intent classification confidence",
    )

    processing_time_ms: int | None = Field(
        default=None,
        description="Processing time in milliseconds",
    )


class ChatResponse(BaseModel):
    """
    Chat response to client.

    Includes:
    - Agent response text
    - Session ID
    - Intent classification
    - Metadata about processing
    """

    response: str = Field(
        ...,
        min_length=1,
        description="Agent response text",
        examples=["I'd be happy to help you schedule an appointment! Let me show you your available projects..."],
    )

    session_id: str = Field(
        ...,
        description="Session ID",
    )

    intent: str | None = Field(
        default=None,
        description="Classified intent",
        examples=["list_projects", "select_date", "confirm_appointment"],
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Intent classification confidence",
    )

    metadata: ChatMetadata = Field(
        default_factory=ChatMetadata,
        description="Additional metadata",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "response": "I'd be happy to help you schedule an appointment! Here are your available projects:\n\n1. Website Redesign\n2. Mobile App Development\n3. Database Migration\n\nWhich project would you like to schedule?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "intent": "list_projects",
                "confidence": 0.95,
                "metadata": {
                    "tools_executed": ["list_projects"],
                    "clarification_needed": False,
                    "next_expected_intent": "select_project",
                    "processing_time_ms": 850,
                },
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(
        ...,
        description="Health status",
        examples=["ok", "degraded", "unhealthy"],
    )

    timestamp: str = Field(
        ...,
        description="ISO timestamp",
    )

    checks: dict[str, Any] = Field(
        default_factory=dict,
        description="Individual health checks",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "ok",
                "timestamp": "2025-10-12T20:00:00Z",
                "checks": {
                    "database": "healthy",
                    "redis": "healthy",
                    "bedrock": "healthy",
                },
            }
        }
