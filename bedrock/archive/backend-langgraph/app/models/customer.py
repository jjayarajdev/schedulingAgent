"""
Customer model for user information.

Stores customer profile data and preferences.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, Boolean, Integer, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Customer(Base):
    """
    Customer information and preferences.

    Stores customer profile data synchronized with PF360 API.
    """

    __tablename__ = "customers"

    # Primary Key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    """PF360 customer ID"""

    # Contact Information
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    """Primary phone number (E.164 format: +1XXXXXXXXXX or +91XXXXXXXXXX)"""

    email: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    """Email address"""

    secondary_phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    """Secondary phone number"""

    # Personal Information
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """First name"""

    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Last name"""

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Address line 1"""

    address_line2: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Address line 2"""

    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """City"""

    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """State/Province"""

    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """ZIP/Postal code"""

    country: Mapped[str] = mapped_column(String(50), default="US")
    """Country code (US, IN, etc.)"""

    # Preferences
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    """
    Customer preferences (JSON):
    {
        "preferred_time": "morning",
        "preferred_day": ["monday", "tuesday"],
        "contact_method": "sms",
        "language": "en",
        "needs_advance_call": true,
        "appointment_duration_preference": 60,
        ...
    }
    """

    communication_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    """
    Communication preferences (JSON):
    {
        "sms_enabled": true,
        "email_enabled": true,
        "voice_enabled": true,
        "reminders_enabled": true,
        "marketing_enabled": false,
        ...
    }
    """

    # TCPA Compliance (SMS consent)
    sms_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    """SMS consent given (TCPA compliance)"""

    sms_consent_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    """Date SMS consent was given"""

    sms_opt_out: Mapped[bool] = mapped_column(Boolean, default=False)
    """Customer opted out of SMS"""

    sms_opt_out_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    """Date customer opted out"""

    # Account Status
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    """Status: active, inactive, suspended, deleted"""

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    """Phone/email verified"""

    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """Verification timestamp"""

    # Loyalty & History
    total_appointments: Mapped[int] = mapped_column(Integer, default=0)
    """Total appointments (lifetime)"""

    completed_appointments: Mapped[int] = mapped_column(Integer, default=0)
    """Completed appointments"""

    cancelled_appointments: Mapped[int] = mapped_column(Integer, default=0)
    """Cancelled appointments"""

    no_show_appointments: Mapped[int] = mapped_column(Integer, default=0)
    """No-show appointments"""

    customer_since: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """First appointment date"""

    last_appointment_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    """Most recent appointment date"""

    # Tags & Segmentation
    tags: Mapped[list] = mapped_column(JSON, default=list)
    """Customer tags (e.g., ["vip", "repeat_customer", "high_value"])"""

    segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """Customer segment (for marketing/targeting)"""

    # PF360 Sync
    pf360_sync_status: Mapped[str] = mapped_column(String(20), default="pending")
    """Sync status: synced, pending, error"""

    pf360_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """Last sync with PF360"""

    pf360_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Raw PF360 customer data (for reference)"""

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Customer notes"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    """Customer creation timestamp"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    """Last update timestamp"""

    # Table Indexes
    __table_args__ = (
        Index('ix_customers_name', 'first_name', 'last_name'),
        Index('ix_customers_status_verified', 'status', 'is_verified'),
        Index('ix_customers_sms_consent', 'sms_consent', 'sms_opt_out'),
    )

    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown"

    def can_send_sms(self) -> bool:
        """Check if customer can receive SMS."""
        return self.sms_consent and not self.sms_opt_out and self.phone

    def get_preference(self, key: str, default: any = None) -> any:
        """Get a customer preference."""
        return self.preferences.get(key, default) if self.preferences else default

    def set_preference(self, key: str, value: any) -> None:
        """Set a customer preference."""
        if self.preferences is None:
            self.preferences = {}
        self.preferences[key] = value

    def __repr__(self) -> str:
        return (
            f"Customer(id={self.id!r}, name={self.full_name!r}, "
            f"phone={self.phone!r}, status={self.status!r})"
        )
