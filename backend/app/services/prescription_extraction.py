"""Prescription Extraction Application Service.

Coordinates the end-to-end extraction pipeline:
Image -> VisionExtractionPort -> Raw Extraction -> Safety Gate -> Normalization -> Validated Result.
"""

import logging

from app.ports.prescription_extractor import VisionExtractionPort
from app.schemas.prescription import ValidatedPrescription
from app.services.normalization import process_prescription
from app.services.safety import DEFAULT_CONFIDENCE_THRESHOLD

logger = logging.getLogger("medication_accessibility.service")


class PrescriptionExtractionService:
    """Application service for end-to-end prescription extraction and validation."""

    def __init__(self, extractor: VisionExtractionPort) -> None:
        self.extractor = extractor

    def process_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        request_id: str | None = None,
    ) -> ValidatedPrescription:
        """Execute end-to-end extraction, safety gating, and normalization.

        Args:
            image_bytes: Raw binary image data.
            mime_type: MIME type of the image.
            confidence_threshold: Engineering threshold for confidence evaluation.
            request_id: Optional correlation tracking identifier.

        Returns:
            ValidatedPrescription: Gated and verified prescription with normalized posology.
        """
        logger.info(
            "Initiating prescription extraction workflow",
            extra={"request_id": request_id, "mime_type": mime_type},
        )

        # 1. Optical/multimodal extraction via abstract provider port
        raw_prescription = self.extractor.extract(
            image_bytes=image_bytes,
            mime_type=mime_type,
            request_id=request_id,
        )

        # 2. Deterministic safety gating & posology normalization (Phase 1 engine)
        validated_prescription = process_prescription(
            raw_prescription=raw_prescription,
            confidence_threshold=confidence_threshold,
        )

        logger.info(
            "Prescription extraction workflow completed",
            extra={
                "request_id": request_id,
                "is_safe": validated_prescription.overall_safety.is_safe,
                "status": validated_prescription.overall_safety.status.value,
                "medications_count": len(validated_prescription.medications),
            },
        )
        return validated_prescription
