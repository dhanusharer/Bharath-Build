"""SQLAlchemy Database Models for Prescription Ingestion and Audit Trail."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""
    pass


# Use JSONB if PostgreSQL dialect, standard JSON as portable fallback
PortableJSON = JSON().with_variant(JSONB, "postgresql")


class PrescriptionStatus(StrEnum):
    """Prescription processing state machine."""

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    FAILED = "FAILED"


class Prescription(Base):
    """Master record for a prescription processing session."""

    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=PrescriptionStatus.UPLOADED,
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0.0")
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    images: Mapped[list["PrescriptionImage"]] = relationship(
        "PrescriptionImage",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )
    medications: Mapped[list["MedicationResult"]] = relationship(
        "MedicationResult",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )
    validation_result: Mapped["ValidationResult | None"] = relationship(
        "ValidationResult",
        back_populates="prescription",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )


class PrescriptionImage(Base):
    """Metadata for uploaded prescription image artifacts stored in S3."""

    __tablename__ = "prescription_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prescription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        index=True,
    )
    s3_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    prescription: Mapped["Prescription"] = relationship(
        "Prescription",
        back_populates="images",
    )


class MedicationResult(Base):
    """Extracted and normalized medication posology record."""

    __tablename__ = "medication_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prescription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        index=True,
    )

    # Raw extracted fields (Verbatim observation)
    raw_drug_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drug_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_timing_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_meal_instruction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_legible: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)

    # Normalized fields
    drug_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    strength_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dose_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dose_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    morning: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    afternoon: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    evening: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    night: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_as_needed_sos: Mapped[bool] = mapped_column(Boolean, default=False)
    before_meal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    after_meal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    duration_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_verified_safe: Mapped[bool] = mapped_column(Boolean, default=False)

    prescription: Mapped["Prescription"] = relationship(
        "Prescription",
        back_populates="medications",
    )


class ValidationResult(Base):
    """Evaluation record from the Phase 1 safety gate."""

    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prescription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    is_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decision_status: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(PortableJSON, default=list)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    prescription: Mapped["Prescription"] = relationship(
        "Prescription",
        back_populates="validation_result",
    )


class AuditEvent(Base):
    """Audit log entry capturing state transitions and service interactions."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prescription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    prescription: Mapped["Prescription"] = relationship(
        "Prescription",
        back_populates="audit_events",
    )
