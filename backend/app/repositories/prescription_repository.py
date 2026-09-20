"""Prescription Persistence Repository."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuditEvent,
    MedicationResult,
    Prescription,
    PrescriptionImage,
    PrescriptionStatus,
    ValidationResult,
)
from app.schemas.prescription import ValidatedPrescription

logger = logging.getLogger("medication_accessibility.repository")


class PrescriptionRepository:
    """Encapsulates all database operations for Prescriptions and related entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, prescription_id: str) -> Prescription | None:
        """Fetch a Prescription with all related records (images, medications, validation)."""
        stmt = (
            select(Prescription)
            .where(Prescription.id == prescription_id)
            .options(
                selectinload(Prescription.images),
                selectinload(Prescription.medications),
                selectinload(Prescription.validation_result),
                selectinload(Prescription.audit_events),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Prescription | None:
        """Lookup an existing prescription by its unique idempotency key."""
        stmt = (
            select(Prescription)
            .where(Prescription.idempotency_key == idempotency_key)
            .options(
                selectinload(Prescription.images),
                selectinload(Prescription.medications),
                selectinload(Prescription.validation_result),
                selectinload(Prescription.audit_events),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_prescription(
        self,
        prescription_id: str,
        idempotency_key: str | None = None,
        status: PrescriptionStatus = PrescriptionStatus.UPLOADED,
    ) -> Prescription:
        """Create a new prescription record in UPLOADED state."""
        prescription = Prescription(
            id=prescription_id,
            status=status.value,
            idempotency_key=idempotency_key,
        )
        self.session.add(prescription)
        await self.session.flush()
        return prescription

    async def add_image(
        self,
        prescription_id: str,
        s3_object_key: str,
        file_name: str,
        mime_type: str,
        file_size_bytes: int,
    ) -> PrescriptionImage:
        """Persist metadata for an uploaded image stored in S3."""
        image = PrescriptionImage(
            id=str(uuid.uuid4()),
            prescription_id=prescription_id,
            s3_object_key=s3_object_key,
            file_name=file_name,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
        )
        self.session.add(image)
        await self.session.flush()
        return image

    async def save_extraction_results(
        self,
        prescription_id: str,
        validated_prescription: ValidatedPrescription,
        model_id: str,
    ) -> Prescription:
        """Save the safety evaluation and normalized medications onto the prescription record."""
        prescription = await self.get_by_id(prescription_id)
        if not prescription:
            raise ValueError(f"Prescription {prescription_id} not found")

        # 1. Update overall status based on Phase 1 safety gate & medication safety
        overall_safety = validated_prescription.overall_safety
        all_meds_verified = len(validated_prescription.medications) > 0 and all(
            m.is_verified_safe and not m.safety.requires_review
            for m in validated_prescription.medications
        )
        if overall_safety.is_safe and not overall_safety.requires_review and all_meds_verified:
            prescription.status = PrescriptionStatus.COMPLETED.value
        else:
            prescription.status = PrescriptionStatus.REQUIRES_REVIEW.value

        # 2. Persist ValidationResult
        validation_record = ValidationResult(
            id=str(uuid.uuid4()),
            prescription_id=prescription_id,
            is_safe=overall_safety.is_safe,
            decision_status=overall_safety.status.value,
            requires_review=overall_safety.requires_review,
            reasons=list(overall_safety.reasons),
            model_id=model_id,
        )
        prescription.validation_result = validation_record
        self.session.add(validation_record)

        # 3. Persist MedicationResults
        for med in validated_prescription.medications:
            norm = med.normalized
            raw = norm.raw_reference
            med_requires_review = (
                norm.requires_review
                or med.safety.requires_review
                or not med.is_verified_safe
                or raw.requires_review
            )
            med_record = MedicationResult(
                id=str(uuid.uuid4()),
                prescription_id=prescription_id,
                # Raw verbatim fields
                raw_drug_name=raw.raw_drug_name,
                drug_confidence=raw.drug_confidence,
                raw_strength=raw.raw_strength,
                raw_dose=raw.raw_dose,
                raw_timing_text=raw.raw_timing_text,
                raw_meal_instruction=raw.raw_meal_instruction,
                raw_duration=raw.raw_duration,
                is_legible=raw.is_legible,
                requires_review=med_requires_review,
                # Normalized fields
                drug_name=norm.drug_name,
                strength_value=norm.strength_value,
                strength_unit=norm.strength_unit,
                dose_value=norm.dose_value,
                dose_unit=norm.dose_unit,
                morning=norm.morning,
                afternoon=norm.afternoon,
                evening=norm.evening,
                night=norm.night,
                is_as_needed_sos=norm.is_as_needed_sos,
                before_meal=norm.before_meal,
                after_meal=norm.after_meal,
                duration_value=norm.duration_value,
                duration_unit=norm.duration_unit,
                is_verified_safe=med.is_verified_safe,
            )
            prescription.medications.append(med_record)

        await self.session.flush()
        return prescription

    async def record_failure(
        self,
        prescription_id: str,
        error_message: str,
    ) -> Prescription:
        """Mark a prescription session as FAILED with an error message."""
        prescription = await self.get_by_id(prescription_id)
        if not prescription:
            raise ValueError(f"Prescription {prescription_id} not found")
        prescription.status = PrescriptionStatus.FAILED.value
        prescription.error_message = error_message
        await self.session.flush()
        return prescription

    async def record_audit_event(
        self,
        prescription_id: str,
        event_type: str,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Record an immutable audit trail entry for tracking workflow progress."""
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            prescription_id=prescription_id,
            event_type=event_type,
            request_id=request_id,
            details=details,
        )
        self.session.add(audit)
        await self.session.flush()
        return audit
