"""Unit tests for Deterministic Safety Gate Service.

Covers:
- Confidence < threshold vs >= threshold
- Missing drug name (Fatal rejection)
- Ambiguous drug name (Requires review)
- Missing dosage (Requires review)
- Missing timing (Requires review)
- Illegible prescription (Fatal rejection)
- requires_review flag propagation
- Document-level safety evaluation
"""

from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
    SafetyDecisionStatus,
)
from app.services.safety import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    evaluate_medication_safety,
    evaluate_prescription_safety,
)


def test_safe_medication_evaluation() -> None:
    """Verify clean, complete, high-confidence medication passes as SAFE_TO_PROCESS."""
    raw = RawMedicationExtraction(
        raw_drug_name="Paracetamol",
        drug_confidence=0.95,
        raw_strength="650mg",
        raw_dose="1 tablet",
        raw_timing_text="1-0-1",
        is_legible=True,
        requires_review=False,
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is True
    assert result.status == SafetyDecisionStatus.SAFE_TO_PROCESS
    assert result.requires_review is False
    assert len(result.reasons) == 0


def test_confidence_below_threshold_triggers_review() -> None:
    """Test D: Confidence < threshold triggers REQUIRES_REVIEW."""
    raw = RawMedicationExtraction(
        raw_drug_name="Metformin",
        drug_confidence=0.75,  # below default 0.85
        raw_strength="500mg",
        raw_timing_text="1-0-1",
    )
    result = evaluate_medication_safety(raw, confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert result.requires_review is True
    assert any("below threshold" in r for r in result.reasons)


def test_confidence_equal_or_above_threshold_passes() -> None:
    """Test E: Confidence >= threshold passes confidence gate."""
    raw = RawMedicationExtraction(
        raw_drug_name="Metformin",
        drug_confidence=DEFAULT_CONFIDENCE_THRESHOLD,
        raw_strength="500mg",
        raw_timing_text="1-0-1",
    )
    result = evaluate_medication_safety(raw, confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    assert result.is_safe is True
    assert result.status == SafetyDecisionStatus.SAFE_TO_PROCESS


def test_missing_drug_name_triggers_rejection() -> None:
    """Test G: Missing drug name is a fatal safety violation (REJECTED_UNSAFE)."""
    raw = RawMedicationExtraction(
        raw_drug_name=None,
        drug_confidence=None,
        raw_strength="500mg",
        raw_timing_text="1-0-1",
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REJECTED_UNSAFE
    assert any("Missing drug name" in r for r in result.reasons)


def test_ambiguous_drug_name_triggers_review() -> None:
    """Test H: Ambiguous drug name tokens trigger REQUIRES_REVIEW."""
    raw = RawMedicationExtraction(
        raw_drug_name="Lisi?negoil",
        drug_confidence=0.90,
        raw_strength="10mg",
        raw_timing_text="1-0-0",
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert any("Ambiguous drug name" in r for r in result.reasons)


def test_missing_dosage_triggers_review() -> None:
    """Test I: Missing dosage and strength triggers REQUIRES_REVIEW."""
    raw = RawMedicationExtraction(
        raw_drug_name="Azithromycin",
        drug_confidence=0.95,
        raw_dose=None,
        raw_strength=None,
        raw_timing_text="OD",
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert any("Missing dosage" in r for r in result.reasons)


def test_missing_timing_triggers_review() -> None:
    """Test J: Missing timing shorthand triggers REQUIRES_REVIEW."""
    raw = RawMedicationExtraction(
        raw_drug_name="Pantoprazole",
        drug_confidence=0.95,
        raw_strength="40mg",
        raw_timing_text=None,
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert any("Missing timing" in r for r in result.reasons)


def test_unreadable_prescription_line_triggers_rejection() -> None:
    """Test M: Unreadable handwriting (is_legible=False) is a fatal REJECTED_UNSAFE state."""
    raw = RawMedicationExtraction(
        raw_drug_name="Amoxicillin",
        drug_confidence=0.90,
        raw_strength="500mg",
        raw_timing_text="1-1-1",
        is_legible=False,
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REJECTED_UNSAFE
    assert any("illegible" in r for r in result.reasons)


def test_upstream_requires_review_flag_preserved() -> None:
    """Test N: requires_review=True from upstream vision model is strictly respected."""
    raw = RawMedicationExtraction(
        raw_drug_name="Ciprofloxacin",
        drug_confidence=0.92,
        raw_strength="500mg",
        raw_timing_text="BD",
        requires_review=True,
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert result.requires_review is True
    assert any("explicitly flagged" in r for r in result.reasons)


def test_subfield_low_timing_confidence_triggers_review() -> None:
    """Verify subfield confidence threshold enforcement."""
    raw = RawMedicationExtraction(
        raw_drug_name="Paracetamol",
        drug_confidence=0.95,
        raw_strength="650mg",
        raw_timing_text="1-0-1",
        timing_confidence=0.50,  # below threshold
    )
    result = evaluate_medication_safety(raw)
    assert result.is_safe is False
    assert result.status == SafetyDecisionStatus.REQUIRES_REVIEW
    assert any("Timing confidence" in r for r in result.reasons)


def test_prescription_level_safety_evaluation() -> None:
    """Verify document-level prescription safety aggregation."""
    # Test document illegibility
    unreadable_doc = RawPrescriptionExtraction(
        overall_legibility=False,
        medications=[],
    )
    result_doc = evaluate_prescription_safety(unreadable_doc)
    assert result_doc.status == SafetyDecisionStatus.REJECTED_UNSAFE
    assert result_doc.is_safe is False

    # Test empty medications list
    empty_doc = RawPrescriptionExtraction(
        overall_legibility=True,
        medications=[],
    )
    result_empty = evaluate_prescription_safety(empty_doc)
    assert result_empty.status == SafetyDecisionStatus.REQUIRES_REVIEW

    # Test doc with one safe and one unsafe medication
    safe_med = RawMedicationExtraction(
        raw_drug_name="Paracetamol",
        drug_confidence=0.95,
        raw_strength="650mg",
        raw_timing_text="1-0-1",
    )
    unsafe_med = RawMedicationExtraction(
        raw_drug_name=None,  # missing drug name
        raw_strength="500mg",
        raw_timing_text="1-0-1",
    )
    mixed_doc = RawPrescriptionExtraction(
        medications=[safe_med, unsafe_med],
    )
    mixed_result = evaluate_prescription_safety(mixed_doc)
    assert mixed_result.status == SafetyDecisionStatus.REJECTED_UNSAFE
    assert mixed_result.is_safe is False
