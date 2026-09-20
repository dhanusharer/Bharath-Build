"""Prescription Ingestion Application Service.

Orchestrates the end-to-end ingestion pipeline:
Validation -> S3 Storage -> VisionExtractionPort -> Phase 1 Safety Gate
-> Phase 1 Normalization -> Persistence -> Response Mapping.
"""

import logging
import uuid

from app.core.config import get_settings
from app.db.models import Prescription, PrescriptionStatus
from app.ports.storage import ObjectStoragePort
from app.providers.storage.s3 import SUPPORTED_MIME_TYPES, generate_prescription_s3_key
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.ingestion import (
    IngestionDosage,
    IngestionDuration,
    IngestionMealInstruction,
    IngestionSchedule,
    IngestionStrength,
    PrescriptionIngestionResponse,
    PrescriptionMedicationItem,
)
from app.services.prescription_extraction import PrescriptionExtractionService

logger = logging.getLogger("medication_accessibility.service.ingestion")
settings = get_settings()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit as specified in PRD / contract


class IngestionValidationError(Exception):
    """Raised when input validation on uploaded image fails."""

    def __init__(self, message: str, code: str = "INVALID_IMAGE_PAYLOAD") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def map_prescription_to_response(
    prescription: Prescription,
    request_id: str,
) -> PrescriptionIngestionResponse:
    """Transform an ORM Prescription record into a stable contract-compliant API response."""
    status_enum = PrescriptionStatus(prescription.status)
    any_med_requires_review = any(
        med.requires_review or not med.is_verified_safe for med in prescription.medications
    )
    val_review = (
        prescription.validation_result.requires_review if prescription.validation_result else False
    )
    requires_review = (
        val_review or (status_enum == PrescriptionStatus.REQUIRES_REVIEW) or any_med_requires_review
    )
    if any_med_requires_review and status_enum == PrescriptionStatus.COMPLETED:
        status_enum = PrescriptionStatus.REQUIRES_REVIEW

    safety_reasons = (
        prescription.validation_result.reasons
        if prescription.validation_result and prescription.validation_result.reasons
        else []
    )

    items: list[PrescriptionMedicationItem] = []
    for med in prescription.medications:
        item = PrescriptionMedicationItem(
            medication_id=med.id,
            drug_name=med.drug_name or med.raw_drug_name,
            is_verified_safe=med.is_verified_safe,
            requires_review=med.requires_review,
            strength=IngestionStrength(
                value=med.strength_value,
                unit=med.strength_unit,
                raw_text=med.raw_strength,
            ),
            dose=IngestionDosage(
                value=med.dose_value,
                unit=med.dose_unit,
                raw_text=med.raw_dose,
            ),
            schedule=IngestionSchedule(
                morning=med.morning,
                afternoon=med.afternoon,
                evening=med.evening,
                night=med.night,
                is_as_needed_sos=med.is_as_needed_sos,
                raw_text=med.raw_timing_text,
            ),
            meal_instruction=IngestionMealInstruction(
                before_meal=med.before_meal,
                after_meal=med.after_meal,
                raw_text=med.raw_meal_instruction,
            ),
            duration=IngestionDuration(
                value=med.duration_value,
                unit=med.duration_unit,
                raw_text=med.raw_duration,
            ),
        )
        items.append(item)

    return PrescriptionIngestionResponse(
        success=(status_enum in (PrescriptionStatus.COMPLETED, PrescriptionStatus.REQUIRES_REVIEW)),
        request_id=request_id,
        prescription_id=prescription.id,
        status=status_enum,
        requires_review=requires_review,
        safety_reasons=safety_reasons,
        medications=items,
        created_at=prescription.created_at,
    )


class PrescriptionIngestionService:
    """Orchestrates upload, storage, extraction, safety gating, and persistence."""

    def __init__(
        self,
        storage_port: ObjectStoragePort,
        extraction_service: PrescriptionExtractionService,
        repository: PrescriptionRepository,
    ) -> None:
        self.storage = storage_port
        self.extraction_service = extraction_service
        self.repo = repository

    async def ingest_prescription(
        self,
        image_bytes: bytes,
        file_name: str,
        mime_type: str,
        request_id: str,
        idempotency_key: str | None = None,
    ) -> PrescriptionIngestionResponse:
        """Execute the end-to-end prescription ingestion flow."""
        # 1. Validation: file presence & non-empty
        if not image_bytes or len(image_bytes) == 0:
            logger.warning("Empty file rejected during ingestion", extra={"request_id": request_id})
            raise IngestionValidationError("Uploaded file is empty.", code="INVALID_IMAGE_PAYLOAD")

        # 2. Validation: file size
        if len(image_bytes) > MAX_FILE_SIZE_BYTES:
            logger.warning(
                "Oversized file rejected: %d bytes",
                len(image_bytes),
                extra={"request_id": request_id},
            )
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise IngestionValidationError(
                f"File size exceeds maximum allowed limit of {max_mb}MB.",
                code="FILE_SIZE_EXCEEDED",
            )

        # 3. Validation: MIME type
        normalized_mime = mime_type.lower().strip()
        if normalized_mime not in SUPPORTED_MIME_TYPES:
            logger.warning(
                "Unsupported MIME type rejected: %s",
                mime_type,
                extra={"request_id": request_id},
            )
            raise IngestionValidationError(
                f"Unsupported media type '{mime_type}'. Supported formats: JPEG, PNG, WebP.",
                code="UNSUPPORTED_MEDIA_TYPE",
            )

        # 4. Check idempotency
        if idempotency_key:
            existing = await self.repo.get_by_idempotency_key(idempotency_key)
            if existing:
                logger.info(
                    "Idempotent submission detected for key %s, returning existing prescription %s",
                    idempotency_key,
                    existing.id,
                    extra={"request_id": request_id},
                )
                return map_prescription_to_response(existing, request_id)

        # 5. Initialize Prescription in DB (State: UPLOADED)
        prescription_id = str(uuid.uuid4())
        await self.repo.create_prescription(
            prescription_id=prescription_id,
            idempotency_key=idempotency_key,
            status=PrescriptionStatus.UPLOADED,
        )
        await self.repo.record_audit_event(
            prescription_id=prescription_id,
            event_type="PRESCRIPTION_UPLOAD_INITIATED",
            request_id=request_id,
        )

        try:
            # 6. S3 Object Storage via Port
            s3_key = generate_prescription_s3_key(prescription_id, file_name)
            self.storage.put_object(
                key=s3_key,
                data=image_bytes,
                content_type=normalized_mime,
                metadata={"prescription_id": prescription_id, "request_id": request_id},
            )
            await self.repo.add_image(
                prescription_id=prescription_id,
                s3_object_key=s3_key,
                file_name=file_name,
                mime_type=normalized_mime,
                file_size_bytes=len(image_bytes),
            )
            await self.repo.record_audit_event(
                prescription_id=prescription_id,
                event_type="S3_IMAGE_STORED",
                request_id=request_id,
                details={"s3_key": s3_key},
            )

            # 7. Optical & Multimodal Extraction + Safety Gate + Normalization
            # (Uses existing Phase 2 VisionExtractionPort & Phase 1 Safety Gate)
            validated_prescription = self.extraction_service.process_image(
                image_bytes=image_bytes,
                mime_type=normalized_mime,
                request_id=request_id,
            )

            # 8. Persist results in Database
            updated_prescription = await self.repo.save_extraction_results(
                prescription_id=prescription_id,
                validated_prescription=validated_prescription,
                model_id=settings.BEDROCK_MODEL_ID,
            )
            await self.repo.record_audit_event(
                prescription_id=prescription_id,
                event_type="EXTRACTION_PIPELINE_COMPLETED",
                request_id=request_id,
                details={
                    "status": updated_prescription.status,
                    "medications_count": len(updated_prescription.medications),
                },
            )
            await self.repo.session.commit()

            return map_prescription_to_response(updated_prescription, request_id)

        except Exception as exc:
            # Fail safely: record failure status in DB if possible, rollback partial transaction
            logger.error(
                "Prescription ingestion failed for %s: %s",
                prescription_id,
                str(exc),
                extra={"request_id": request_id},
                exc_info=True,
            )
            try:
                await self.repo.record_failure(prescription_id, str(exc))
                await self.repo.session.commit()
            except Exception:
                await self.repo.session.rollback()
            raise

    async def get_prescription(
        self,
        prescription_id: str,
        request_id: str,
    ) -> PrescriptionIngestionResponse | None:
        """Fetch latest persisted prescription state and normalized data."""
        prescription = await self.repo.get_by_id(prescription_id)
        if not prescription:
            return None
        return map_prescription_to_response(prescription, request_id)
