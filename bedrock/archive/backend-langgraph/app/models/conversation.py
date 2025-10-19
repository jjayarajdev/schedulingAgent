"""
Conversation message model for chat history.

Stores individual messages in conversations for audit trail and context.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Message(Base):
    """
    Individual message in a conversation.

    Stores all messages (user, assistant, system) with metadata for auditing.
    """

    __tablename__ = "messages"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """Auto-incrementing message ID"""

    # Session Reference
    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True
    )
    """Reference to session"""

    # Message Data
    role: Mapped[str] = mapped_column(String(20), index=True)
    """Role: user, assistant, system, function"""

    content: Mapped[str] = mapped_column(Text)
    """Message content/text"""

    # Metadata
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    """Content type: text, ssml, image, audio"""

    # Agent Information
    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Bedrock Agent ID that generated this message"""

    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Agent name: supervisor, scheduling, information, notes, chitchat"""

    # Action Tracking
    action_invoked: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    """Lambda action invoked (e.g., list_projects, get_time_slots)"""

    action_parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Action parameters (JSON)"""

    action_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Action result (JSON)"""

    # Sentiment & Classification (for analytics)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Sentiment: positive, negative, neutral (populated by Contact Lens or custom)"""

    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    """Detected intent (e.g., schedule_appointment, check_status)"""

    confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    """Intent confidence score (0.0 - 1.0)"""

    # Performance Metrics
    latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    """Response latency in milliseconds"""

    tokens_input: Mapped[Optional[int]] = mapped_column(nullable=True)
    """Input tokens (for LLM calls)"""

    tokens_output: Mapped[Optional[int]] = mapped_column(nullable=True)
    """Output tokens (for LLM calls)"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    """Message timestamp"""

    # Error Tracking
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Error message (if any)"""

    # Table Indexes
    __table_args__ = (
        Index('ix_messages_session_created', 'session_id', 'created_at'),
        Index('ix_messages_role_intent', 'role', 'intent'),
        Index('ix_messages_action', 'action_invoked'),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"Message(id={self.id}, session_id={self.session_id!r}, "
            f"role={self.role!r}, content={content_preview!r})"
        )


class ConversationSummary(Base):
    """
    Summary of completed conversations for analytics.

    Generated periodically or on session close for reporting.
    """

    __tablename__ = "conversation_summaries"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """Auto-incrementing summary ID"""

    # Session Reference
    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
        unique=True
    )
    """Reference to session (one summary per session)"""

    # Summary Data
    summary: Mapped[str] = mapped_column(Text)
    """AI-generated summary of conversation"""

    outcome: Mapped[str] = mapped_column(String(50))
    """Outcome: completed, abandoned, escalated, error"""

    # Metrics
    message_count: Mapped[int] = mapped_column(default=0)
    """Total messages in conversation"""

    duration_seconds: Mapped[int] = mapped_column(nullable=True)
    """Conversation duration"""

    actions_performed: Mapped[list] = mapped_column(JSON, default=list)
    """List of actions performed (e.g., ["list_projects", "confirm_appointment"])"""

    # Business Outcomes
    appointment_created: Mapped[bool] = mapped_column(default=False)
    """Whether an appointment was created"""

    appointment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Appointment ID (if created)"""

    customer_satisfied: Mapped[Optional[bool]] = mapped_column(nullable=True)
    """Customer satisfaction (from survey or sentiment)"""

    # Quality Metrics
    avg_response_time_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    """Average agent response time"""

    error_count: Mapped[int] = mapped_column(default=0)
    """Number of errors in conversation"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    """Summary creation timestamp"""

    # Table Indexes
    __table_args__ = (
        Index('ix_summaries_outcome', 'outcome'),
        Index('ix_summaries_appointment', 'appointment_created'),
    )

    def __repr__(self) -> str:
        return (
            f"ConversationSummary(id={self.id}, session_id={self.session_id!r}, "
            f"outcome={self.outcome!r}, messages={self.message_count})"
        )
