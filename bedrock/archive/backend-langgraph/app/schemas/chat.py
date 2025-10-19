"""
Chat API request and response schemas.

Defines the structure for:
- Chat requests from clients
- Chat responses to clients
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClientLocation(BaseModel):
    """
    B2B Client location information.

    For multi-client customers (B2B), represents each location/office.
    """

    client_id: str = Field(
        ...,
        description="Client ID (location identifier)",
        examples=["09PF05VD"],
    )

    client_name: str = Field(
        ...,
        description="Client name (location name)",
        examples=["Tampa Office", "Miami Office"],
    )

    is_primary: bool = Field(
        default=False,
        description="Whether this is the user's primary location",
    )


class ChatRequest(BaseModel):
    """
    Chat request from client.

    Supports both B2C (single customer) and B2B (multi-client customer) scenarios.

    B2C Example:
        customer_id: "CUST001"
        client_id: None
        available_clients: None

    B2B Example:
        customer_id: "CUST_BIGCORP"
        client_id: "09PF05VD"  (default/primary location)
        available_clients: [Tampa, Miami, Orlando locations]
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
        description="Customer ID from ProjectsForce authentication",
        examples=["1645975", "CUST001", "CUST_BIGCORP"],
    )

    client_id: str | None = Field(
        default=None,
        description="Client ID (B2B only) - Default/primary location for multi-client customers",
        examples=["09PF05VD", None],
    )

    client_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Client name - for B2C, customer name; for B2B, location name",
        examples=["projectsforce-validation", "Tampa Office"],
    )

    available_clients: list[ClientLocation] | None = Field(
        default=None,
        description="Available client locations (B2B only) - All locations user can access",
        examples=[[
            {"client_id": "09PF05VD", "client_name": "Tampa Office", "is_primary": True},
            {"client_id": "09PF05WE", "client_name": "Miami Office", "is_primary": False}
        ]],
    )

    customer_type: str | None = Field(
        default=None,
        description="Customer type: B2C or B2B (auto-detected if not provided)",
        examples=["B2C", "B2B"],
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

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: str | None, info) -> str:
        """Auto-detect customer type if not provided."""
        if v:
            return v
        # Auto-detect based on available_clients
        available_clients = info.data.get("available_clients")
        if available_clients and len(available_clients) > 0:
            return "B2B"
        return "B2C"

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "examples": [
                {
                    "title": "B2C Customer Request",
                    "value": {
                        "message": "Show me my projects",
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "customer_id": "CUST001",
                        "client_id": None,
                        "client_name": "John Smith",
                        "available_clients": None,
                        "customer_type": "B2C"
                    }
                },
                {
                    "title": "B2B Customer Request (Multi-Location)",
                    "value": {
                        "message": "Show me Tampa projects",
                        "session_id": "550e8400-e29b-41d4-a716-446655440001",
                        "customer_id": "CUST_BIGCORP",
                        "client_id": "09PF05VD",
                        "client_name": "Tampa Office",
                        "available_clients": [
                            {"client_id": "09PF05VD", "client_name": "Tampa Office", "is_primary": True},
                            {"client_id": "09PF05WE", "client_name": "Miami Office", "is_primary": False},
                            {"client_id": "09PF05XF", "client_name": "Orlando Office", "is_primary": False}
                        ],
                        "customer_type": "B2B"
                    }
                }
            ]
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
