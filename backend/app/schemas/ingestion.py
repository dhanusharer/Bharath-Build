"""Prescription Ingestion and Response API Schemas.

Adheres strictly to Phase 3 Response Contract (Section 6) and PRD specifications:
- success: bool
- request_id: str
- prescription_id: str
- status: PrescriptionStatus
- requires_review: bool
- safety_reasons: list[str]
- medications: list[PrescriptionMedicationItem]
- created_at: datetime
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import PrescriptionStatus


class IngestionStrength(BaseModel):
    """Normalized strength component."""

    model_config = ConfigDict(frozen=True)

    value: float | None = Field(None, description="Numeric strength (e.g., 500.0)")
    unit: str | None = Field(None, description="Metric unit (e.g., 'mg', 'ml')")
    raw_text: str | None = Field(None, description="Verbatim raw text transcribed from image")


class IngestionDosage(BaseModel):
    """Normalized dosage quantity component."""

    model_config = ConfigDict(frozen=True)

    value: float | None = Field(None, description="Numeric dose amount (e.g., 1.0)")
    unit: str | None = Field(None, description="Dose unit (e.g., 'tablet', 'capsule')")
    raw_text: str | None = Field(None, description="Verbatim raw text transcribed from image")


class IngestionSchedule(BaseModel):
    """Posology intake schedule across canonical intervals."""

    model_config = ConfigDict(frozen=True)

    morning: bool | None = Field(None, description="Scheduled morning intake")
    afternoon: bool | None = Field(None, description="Scheduled afternoon intake")
    evening: bool | None = Field(None, description="Scheduled evening intake")
    night: bool | None = Field(None, description="Scheduled night / bedtime intake")
    is_as_needed_sos: bool = Field(False, description="True if PRN / SOS as-needed")
    raw_text: str | None = Field(None, description="Verbatim timing text (e.g. '1-0-1')")


class IngestionMealInstruction(BaseModel):
    """Meal timing relation."""

    model_config = ConfigDict(frozen=True)

    before_meal: bool | None = Field(None, description="True if before food / empty stomach")
    after_meal: bool | None = Field(None, description="True if after food / post-prandial")
    raw_text: str | None = Field(None, description="Verbatim meal instruction (e.g. 'after food')")


class IngestionDuration(BaseModel):
    """Course duration."""

    model_config = ConfigDict(frozen=True)

    value: int | None = Field(None, description="Duration numeric count")
    unit: str | None = Field(None, description="Standardized unit (e.g. 'days', 'month')")
    raw_text: str | None = Field(None, description="Verbatim duration text (e.g. '10 days')")


class PrescriptionMedicationItem(BaseModel):
    """Structured medication item in the public API contract."""

    model_config = ConfigDict(frozen=True)

    medication_id: str = Field(..., description="Unique ID for this medication item")
    drug_name: str | None = Field(None, description="Verbatim canonical drug name")
    is_verified_safe: bool = Field(..., description="True if certified safe by Phase 1 safety gate")
    requires_review: bool = Field(..., description="True if human pharmacist review required")
    strength: IngestionStrength
    dose: IngestionDosage
    schedule: IngestionSchedule
    meal_instruction: IngestionMealInstruction
    duration: IngestionDuration


class PrescriptionIngestionResponse(BaseModel):
    """Contract-compliant API response envelope for POST and GET /api/v1/prescriptions."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(..., description="True if ingestion and safety workflow completed without system error")
    request_id: str = Field(..., description="Unique request tracing correlation ID")
    prescription_id: str = Field(..., description="Unique identifier for the prescription")
    status: PrescriptionStatus = Field(..., description="Current processing state")
    requires_review: bool = Field(..., description="True if clinical or human pharmacist review is needed")
    safety_reasons: list[str] = Field(default_factory=list, description="Safety or review reasons flagged")
    medications: list[PrescriptionMedicationItem] = Field(default_factory=list, description="Extracted medications")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Prescription registration timestamp",
    )
