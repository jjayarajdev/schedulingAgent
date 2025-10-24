"""
Session model for conversation tracking.

Stores customer conversation sessions across all channels (SMS, voice, chat).
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import String, DateTime, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Session(Base):
    """
    Customer conversation session.

    Tracks active conversations across channels with context and expiration.
    """

    __tablename__ = "sessions"

    # Primary Key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    """Session ID (format: channel-phone-timestamp)"""

    # Customer Identification
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    """PF360 customer ID (if known)"""

    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )
    """Customer phone number (E.164 format)"""

    customer_email: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    """Customer email"""

    # Channel Information
    channel: Mapped[str] = mapped_column(String(20), index=True)
    """Channel: sms, voice, chat"""

    # Session Status
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    """Status: active, completed, expired, abandoned"""

    # Context Data
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    """
    Session context (JSON):
    {
        "current_intent": "schedule_appointment",
        "project_id": "12345",
        "selected_date": "2025-10-20",
        "selected_time": "10:00",
        "last_action": "get_time_slots",
        "pending_confirmation": true,
        ...
    }
    """

    # Bedrock Agent Data
    bedrock_session_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Bedrock Agent session ID for continuity"""

    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Last Bedrock Agent ID that handled this session"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    """Session creation timestamp"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    """Last activity timestamp"""

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    """Session expiration (default: 24 hours from last activity)"""

    # Metadata
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """User agent (for web chat)"""

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    """IP address (for web chat, supports IPv6)"""

    # Table Indexes
    __table_args__ = (
        Index('ix_sessions_customer_status', 'customer_id', 'status'),
        Index('ix_sessions_phone_channel', 'customer_phone', 'channel'),
        Index('ix_sessions_expires_status', 'expires_at', 'status'),
    )

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def extend_expiration(self, hours: int = 24) -> None:
        """Extend session expiration by specified hours."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.updated_at = datetime.utcnow()

    def update_context(self, key: str, value: any) -> None:
        """Update a single context key."""
        if self.context is None:
            self.context = {}
        self.context[key] = value
        self.updated_at = datetime.utcnow()

    def get_context(self, key: str, default: any = None) -> any:
        """Get a context value."""
        if self.context is None:
            return default
        return self.context.get(key, default)

    def __repr__(self) -> str:
        return (
            f"Session(id={self.id!r}, channel={self.channel!r}, "
            f"status={self.status!r}, customer_phone={self.customer_phone!r})"
        )
