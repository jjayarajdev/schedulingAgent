"""
Intent classification schemas.

Defines:
- Intent types (hierarchical classification)
- Intent classification results
- Entity extraction
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """
    Intent types for scheduling agent.

    Hierarchical structure:
    - scheduling: All scheduling-related intents
    - information: Information requests
    - notes: Note management
    - chitchat: Conversational intents
    """

    # Scheduling intents
    LIST_PROJECTS = "list_projects"
    SELECT_PROJECT = "select_project"
    GET_AVAILABLE_DATES = "get_available_dates"
    SELECT_DATE = "select_date"
    GET_TIME_SLOTS = "get_time_slots"
    SELECT_TIME_SLOT = "select_time_slot"
    CONFIRM_APPOINTMENT = "confirm_appointment"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"

    # Information intents
    PROJECT_DETAILS = "project_details"
    APPOINTMENT_STATUS = "appointment_status"
    WORKING_HOURS = "working_hours"
    WEATHER = "weather"

    # Notes intents
    ADD_NOTE = "add_note"
    VIEW_NOTES = "view_notes"

    # Chitchat intents
    GREETING = "greeting"
    THANKS = "thanks"
    GOODBYE = "goodbye"
    HELP = "help"

    # Fallback
    UNKNOWN = "unknown"


class IntentDomain(str, Enum):
    """Top-level intent domains (for hierarchical classification)."""

    SCHEDULING = "scheduling"
    INFORMATION = "information"
    NOTES = "notes"
    CHITCHAT = "chitchat"
    UNKNOWN = "unknown"


# Intent domain mapping
INTENT_DOMAIN_MAPPING = {
    IntentType.LIST_PROJECTS: IntentDomain.SCHEDULING,
    IntentType.SELECT_PROJECT: IntentDomain.SCHEDULING,
    IntentType.GET_AVAILABLE_DATES: IntentDomain.SCHEDULING,
    IntentType.SELECT_DATE: IntentDomain.SCHEDULING,
    IntentType.GET_TIME_SLOTS: IntentDomain.SCHEDULING,
    IntentType.SELECT_TIME_SLOT: IntentDomain.SCHEDULING,
    IntentType.CONFIRM_APPOINTMENT: IntentDomain.SCHEDULING,
    IntentType.RESCHEDULE: IntentDomain.SCHEDULING,
    IntentType.CANCEL: IntentDomain.SCHEDULING,
    IntentType.PROJECT_DETAILS: IntentDomain.INFORMATION,
    IntentType.APPOINTMENT_STATUS: IntentDomain.INFORMATION,
    IntentType.WORKING_HOURS: IntentDomain.INFORMATION,
    IntentType.WEATHER: IntentDomain.INFORMATION,
    IntentType.ADD_NOTE: IntentDomain.NOTES,
    IntentType.VIEW_NOTES: IntentDomain.NOTES,
    IntentType.GREETING: IntentDomain.CHITCHAT,
    IntentType.THANKS: IntentDomain.CHITCHAT,
    IntentType.GOODBYE: IntentDomain.CHITCHAT,
    IntentType.HELP: IntentDomain.CHITCHAT,
    IntentType.UNKNOWN: IntentDomain.UNKNOWN,
}


class EntityType(str, Enum):
    """Entity types that can be extracted from user messages."""

    PROJECT_NAME = "project_name"
    PROJECT_ID = "project_id"
    DATE = "date"
    TIME = "time"
    LOCATION = "location"
    NOTE_TEXT = "note_text"
    CONFIRMATION = "confirmation"  # yes/no


class Entity(BaseModel):
    """
    Extracted entity from user message.

    Example:
        Entity(type="date", value="next Monday", normalized="2025-10-20")
    """

    type: EntityType = Field(..., description="Entity type")
    value: str = Field(..., description="Raw entity value from text")
    normalized: str | None = Field(
        default=None,
        description="Normalized entity value",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Extraction confidence",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "type": "date",
                "value": "next Monday",
                "normalized": "2025-10-20",
                "confidence": 0.9,
            }
        }


class IntentClassification(BaseModel):
    """
    Intent classification result.

    Includes:
    - Classified intent
    - Confidence score
    - Domain (top-level category)
    - Extracted entities
    - Alternative intents (with scores)
    """

    intent: IntentType = Field(
        ...,
        description="Classified intent",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence (0.0-1.0)",
    )

    domain: IntentDomain = Field(
        ...,
        description="Intent domain (top-level category)",
    )

    entities: list[Entity] = Field(
        default_factory=list,
        description="Extracted entities from message",
    )

    alternatives: list[tuple[IntentType, float]] = Field(
        default_factory=list,
        description="Alternative intents with scores",
    )

    needs_clarification: bool = Field(
        default=False,
        description="Whether clarification is needed",
    )

    clarification_reason: str | None = Field(
        default=None,
        description="Reason why clarification is needed",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "intent": "select_date",
                "confidence": 0.85,
                "domain": "scheduling",
                "entities": [
                    {
                        "type": "date",
                        "value": "next Monday",
                        "normalized": "2025-10-20",
                        "confidence": 0.9,
                    }
                ],
                "alternatives": [
                    ["get_available_dates", 0.12],
                    ["reschedule", 0.03],
                ],
                "needs_clarification": False,
                "clarification_reason": None,
                "metadata": {
                    "processing_time_ms": 120,
                    "model": "claude-3-5-sonnet",
                },
            }
        }

    def get_domain(self) -> IntentDomain:
        """Get domain for the classified intent."""
        return INTENT_DOMAIN_MAPPING.get(self.intent, IntentDomain.UNKNOWN)

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if confidence is above threshold."""
        return self.confidence >= threshold

    def is_low_confidence(self, threshold: float = 0.4) -> bool:
        """Check if confidence is below threshold."""
        return self.confidence < threshold

    def should_clarify(self, threshold: float = 0.7) -> bool:
        """Determine if clarification is needed based on confidence."""
        return self.confidence < threshold or self.needs_clarification
