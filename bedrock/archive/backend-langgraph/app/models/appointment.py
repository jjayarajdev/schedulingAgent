"""
Appointment model for scheduled visits.

Stores customer appointments with project details and status tracking.
"""

from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import String, DateTime, Date, Time, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Appointment(Base):
    """
    Customer appointment for project work.

    Tracks scheduled appointments with full details and status.
    """

    __tablename__ = "appointments"

    # Primary Key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    """Appointment ID (format: APPT-{timestamp}-{random})"""

    # Customer & Project References
    customer_id: Mapped[str] = mapped_column(String(100), index=True)
    """PF360 customer ID"""

    project_id: Mapped[str] = mapped_column(String(100), index=True)
    """PF360 project ID"""

    project_type: Mapped[str] = mapped_column(String(50), index=True)
    """Project type: Flooring Installation, HVAC Service, etc."""

    # Appointment Details
    appointment_date: Mapped[date] = mapped_column(Date, index=True)
    """Appointment date"""

    appointment_time: Mapped[time] = mapped_column(Time)
    """Appointment time"""

    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    """Expected duration in minutes"""

    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    """Timezone (e.g., America/New_York, Asia/Kolkata)"""

    # Status Tracking
    status: Mapped[str] = mapped_column(String(20), default="scheduled", index=True)
    """Status: scheduled, confirmed, in_progress, completed, cancelled, rescheduled, no_show"""

    confirmation_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    """Unique confirmation code (e.g., CONF-1760378566)"""

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """When customer confirmed the appointment"""

    # Location
    location_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Service location address"""

    location_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """City"""

    location_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """State/Province"""

    location_zip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """ZIP/Postal code"""

    location_country: Mapped[str] = mapped_column(String(50), default="US")
    """Country code"""

    # Technician Assignment
    technician_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Assigned technician ID"""

    technician_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Assigned technician name"""

    # Notes & Instructions
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Appointment notes (customer requests, special instructions)"""

    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Internal notes (for office use only)"""

    # Reminders
    reminder_sent_24h: Mapped[bool] = mapped_column(default=False)
    """24-hour reminder sent"""

    reminder_sent_2h: Mapped[bool] = mapped_column(default=False)
    """2-hour reminder sent"""

    # Cancellation/Rescheduling
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """Cancellation timestamp"""

    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Reason for cancellation"""

    rescheduled_from: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    """Previous appointment ID (if rescheduled)"""

    rescheduled_to: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    """New appointment ID (if rescheduled)"""

    # Source Tracking
    booking_channel: Mapped[str] = mapped_column(String(20), default="agent")
    """Booking channel: agent (AI), web, phone, manual"""

    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Session ID that created this appointment"""

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    """Appointment creation timestamp"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    """Last update timestamp"""

    # Table Indexes
    __table_args__ = (
        Index('ix_appointments_customer_status', 'customer_id', 'status'),
        Index('ix_appointments_date_status', 'appointment_date', 'status'),
        Index('ix_appointments_project_date', 'project_id', 'appointment_date'),
    )

    def is_upcoming(self) -> bool:
        """Check if appointment is in the future."""
        return self.appointment_date >= date.today() and self.status in [
            "scheduled",
            "confirmed",
        ]

    def can_cancel(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in ["scheduled", "confirmed"]

    def can_reschedule(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.status in ["scheduled", "confirmed"]

    def __repr__(self) -> str:
        return (
            f"Appointment(id={self.id!r}, customer_id={self.customer_id!r}, "
            f"date={self.appointment_date}, time={self.appointment_time}, "
            f"status={self.status!r})"
        )
