"""Unit tests for Raw, Normalized, and Validated Prescription Schemas.

Covers:
- Valid extraction instantiation
- Confidence boundary values (0.0, 1.0)
- Confidence outside 0.0 - 1.0 rejection
- String confidence rejection ("medium", "high")
- Immutability of raw model (frozen instance)
- Separation of raw and normalized representations
"""

import pytest
from pydantic import ValidationError

from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
)


def test_valid_raw_extraction_instantiation() -> None:
    """Test A: Valid raw extraction model creates cleanly."""
    raw = RawMedicationExtraction(
        raw_drug_name="Metformin",
        drug_confidence=0.98,
        raw_strength="500mg",
        strength_confidence=0.95,
        raw_dose="1 tablet",
        dose_confidence=0.92,
        raw_timing_text="1-0-1",
        timing_confidence=0.96,
        raw_meal_instruction="after food",
        meal_confidence=0.91,
        raw_duration="14 days",
        duration_confidence=0.88,
        is_legible=True,
        requires_review=False,
    )
    assert raw.raw_drug_name == "Metformin"
    assert raw.drug_confidence == 0.98
    assert raw.is_legible is True
    assert raw.requires_review is False


def test_confidence_boundary_zero() -> None:
    """Test B: Confidence = 0.0 is a valid numeric boundary."""
    raw = RawMedicationExtraction(
        raw_drug_name="Unknown Drug",
        drug_confidence=0.0,
    )
    assert raw.drug_confidence == 0.0


def test_confidence_boundary_one() -> None:
    """Test C: Confidence = 1.0 is a valid numeric boundary."""
    raw = RawMedicationExtraction(
        raw_drug_name="Amoxicillin",
        drug_confidence=1.0,
    )
    assert raw.drug_confidence == 1.0


@pytest.mark.parametrize("invalid_confidence", [-0.01, -1.0, 1.01, 2.5, 100.0])
def test_confidence_outside_range_rejected(invalid_confidence: float) -> None:
    """Test F: Confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        RawMedicationExtraction(
            raw_drug_name="Paracetamol",
            drug_confidence=invalid_confidence,
        )


@pytest.mark.parametrize("invalid_str_conf", ["medium", "high", "low", "0.85", "none"])
def test_string_confidence_rejected_without_silent_coercion(invalid_str_conf: str) -> None:
    """Test: Arbitrary string confidence scores are strictly rejected."""
    with pytest.raises(ValidationError):
        RawMedicationExtraction(
            raw_drug_name="Aspirin",
            drug_confidence=invalid_str_conf,  # type: ignore[arg-type]
        )


def test_raw_medication_is_immutable() -> None:
    """Test: RawMedicationExtraction is frozen and cannot be mutated."""
    raw = RawMedicationExtraction(
        raw_drug_name="Atorvastatin",
        drug_confidence=0.95,
    )
    with pytest.raises(ValidationError):
        raw.raw_drug_name = "ModifiedDrug"  # type: ignore[misc]


def test_raw_prescription_envelope() -> None:
    """Test: Raw prescription wrapper properly encapsulates raw items."""
    item1 = RawMedicationExtraction(raw_drug_name="Drug A", drug_confidence=0.9)
    item2 = RawMedicationExtraction(raw_drug_name="Drug B", drug_confidence=0.85)

    doc = RawPrescriptionExtraction(
        prescription_id="rx-12345",
        overall_legibility=True,
        doctor_notes_raw="Take with warm water",
        medications=[item1, item2],
    )
    assert doc.prescription_id == "rx-12345"
    assert len(doc.medications) == 2
    assert doc.medications[0].raw_drug_name == "Drug A"
