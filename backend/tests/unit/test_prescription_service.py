"""Unit tests for PrescriptionExtractionService Application Service.

Verifies end-to-end integration across the port boundary:
Image -> VisionExtractionPort Mock -> RawPrescriptionExtraction
      -> Phase 1 Safety Gate -> Normalization.
Ensures zero provider SDK types leak into service outputs.
"""

from unittest.mock import MagicMock

from app.ports.prescription_extractor import VisionExtractionPort
from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
    SafetyDecisionStatus,
    ValidatedPrescription,
)
from app.services.prescription_extraction import PrescriptionExtractionService

DUMMY_IMAGE = b"FAKE_PRESCRIPTION_IMAGE_BYTES"


def test_service_successful_extraction_to_safety_and_normalization() -> None:
    """Test 13: Successful image extraction passed through Phase 1 safety gate & normalizer."""
    mock_extractor = MagicMock(spec=VisionExtractionPort)
    raw_prescription = RawPrescriptionExtraction(
        prescription_id="rx-service-01",
        overall_legibility=True,
        medications=[
            RawMedicationExtraction(
                raw_drug_name="Metformin",
                drug_confidence=0.96,
                raw_strength="500mg",
                raw_dose="1 tablet",
                raw_timing_text="1-0-1",
                raw_meal_instruction="after food",
                raw_duration="1 month",
                is_legible=True,
                requires_review=False,
            )
        ],
    )
    mock_extractor.extract.return_value = raw_prescription

    service = PrescriptionExtractionService(extractor=mock_extractor)
    validated: ValidatedPrescription = service.process_image(
        image_bytes=DUMMY_IMAGE,
        mime_type="image/jpeg",
        request_id="req-srv-01",
    )

    # 1. Extractor called with correct arguments
    mock_extractor.extract.assert_called_once_with(
        image_bytes=DUMMY_IMAGE,
        mime_type="image/jpeg",
        request_id="req-srv-01",
    )

    # 2. Safety Gate evaluated
    assert validated.overall_safety.is_safe is True
    assert validated.overall_safety.status == SafetyDecisionStatus.SAFE_TO_PROCESS

    # 3. Posology normalized
    assert len(validated.medications) == 1
    med = validated.medications[0]
    assert med.is_verified_safe is True
    assert med.normalized.drug_name == "Metformin"
    assert med.normalized.morning is True
    assert med.normalized.afternoon is False
    assert med.normalized.night is True
    assert med.normalized.after_meal is True
    assert med.normalized.duration_value == 1
    assert med.normalized.duration_unit == "month"

    # 4. Raw reference preserved unchanged
    assert med.normalized.raw_reference.raw_duration == "1 month"
    assert med.normalized.raw_reference.raw_drug_name == "Metformin"


def test_service_flags_uncertain_extraction_for_review() -> None:
    """Verify that uncertain extraction from provider is strictly gated to REQUIRES_REVIEW."""
    mock_extractor = MagicMock(spec=VisionExtractionPort)
    raw_prescription = RawPrescriptionExtraction(
        prescription_id="rx-service-uncertain",
        overall_legibility=True,
        medications=[
            RawMedicationExtraction(
                raw_drug_name="Lisi?negoil",  # Ambiguous drug name
                drug_confidence=0.70,  # Below threshold
                raw_strength="10mg",
                raw_timing_text="1-0-0",
                is_legible=True,
                requires_review=True,
            )
        ],
    )
    mock_extractor.extract.return_value = raw_prescription

    service = PrescriptionExtractionService(extractor=mock_extractor)
    validated = service.process_image(
        image_bytes=DUMMY_IMAGE,
        mime_type="image/png",
    )

    assert validated.overall_safety.is_safe is False
    assert validated.overall_safety.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert validated.medications[0].is_verified_safe is False
    assert validated.medications[0].safety.requires_review is True
    # Preserves verbatim drug name without guessing
    assert validated.medications[0].normalized.drug_name == "Lisi?negoil"
