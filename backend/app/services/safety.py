"""Deterministic Safety Gate Service.

Enforces fail-closed clinical safety invariants.
AI extraction is strictly treated as UNTRUSTED input.
Confidence scores are treated as heuristic indicators, never as proof of medical correctness.
"""

import re
from typing import Final

from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
    SafetyCheckResult,
    SafetyDecisionStatus,
)

# ------------------------------------------------------------------------------
# CONFIGURABLE ENGINEERING PARAMETER (NOT CLINICALLY VALIDATED / NO MEDICAL GUARANTEE)
# DEFAULT_CONFIDENCE_THRESHOLD is a configurable engineering heuristic parameter.
# It is explicitly NOT clinically validated and is NOT a medical safety guarantee.
# It must NOT be treated as proof of diagnostic or clinical correctness.
# ------------------------------------------------------------------------------
DEFAULT_CONFIDENCE_THRESHOLD: Final[float] = 0.85

# Marker patterns representing ambiguous or unconfirmed characters in extracted text
AMBIGUOUS_TEXT_PATTERNS: Final[tuple[str, ...]] = (
    r"\?",
    r"\[unclear\]",
    r"\[illegible\]",
    r"\.{3,}",  # ellipsis or trailing dots
    r"unreadable",
    r"unknown",
)
_AMBIGUITY_REGEX = re.compile(
    "|".join(AMBIGUOUS_TEXT_PATTERNS),
    re.IGNORECASE,
)


def is_text_ambiguous(text: str | None) -> bool:
    """Check if text contains ambiguous tokens, question marks, or unconfirmed markers."""
    if not text:
        return False
    return bool(_AMBIGUITY_REGEX.search(text))


def evaluate_medication_safety(
    raw: RawMedicationExtraction,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> SafetyCheckResult:
    """Evaluate a single raw medication extraction against deterministic safety invariants.

    Returns a SafetyCheckResult indicating:
    - SAFE_TO_PROCESS: All required fields present, confidence acceptable, no ambiguity.
    - REQUIRES_REVIEW: Missing non-fatal info, confidence below threshold, or ambiguous token.
    - REJECTED_UNSAFE: Unreadable/illegible line or completely missing drug name.
    """
    reasons: list[str] = []
    is_rejected = False
    needs_review = False

    # 1. Legibility check (Fatal)
    if not raw.is_legible:
        is_rejected = True
        reasons.append("Prescription line marked illegible: handwriting unreadable or smudged.")

    # 2. Upstream explicit review flag
    if raw.requires_review:
        needs_review = True
        reasons.append("Extraction explicitly flagged for human review by vision extractor.")

    # 3. Drug Name verification (Fatal if missing, review if ambiguous)
    if not raw.raw_drug_name or not raw.raw_drug_name.strip():
        is_rejected = True
        reasons.append("Missing drug name: raw medication name is absent.")
    elif is_text_ambiguous(raw.raw_drug_name):
        needs_review = True
        reasons.append(
            f"Ambiguous drug name: token '{raw.raw_drug_name}' contains uncertain markers."
        )

    # 4. Drug Confidence Gate
    # Model confidence is ONE deterministic signal, NOT proof of correctness.
    if raw.drug_confidence is None:
        needs_review = True
        reasons.append("Missing drug name confidence score.")
    elif raw.drug_confidence < confidence_threshold:
        needs_review = True
        reasons.append(
            f"Drug confidence ({raw.drug_confidence:.2f}) "
            f"below threshold ({confidence_threshold:.2f})."
        )

    # 5. Dosage / Strength presence check
    # A prescription line missing both strength (e.g. 500mg) and dose (e.g. 1 tab) is unsafe
    has_dose = bool(raw.raw_dose and raw.raw_dose.strip())
    has_strength = bool(raw.raw_strength and raw.raw_strength.strip())
    if not has_dose and not has_strength:
        needs_review = True
        reasons.append("Missing dosage: neither dose quantity nor strength is specified.")

    # 6. Timing presence check
    # Missing timing instructions cannot be safely guessed
    if not raw.raw_timing_text or not raw.raw_timing_text.strip():
        needs_review = True
        reasons.append("Missing timing: no dosage schedule or timing shorthand provided.")
    elif is_text_ambiguous(raw.raw_timing_text):
        needs_review = True
        reasons.append(
            f"Ambiguous timing: token '{raw.raw_timing_text}' contains uncertain markers."
        )

    # 7. Field-level confidence checks
    if raw.timing_confidence is not None and raw.timing_confidence < confidence_threshold:
        needs_review = True
        reasons.append(
            f"Timing confidence ({raw.timing_confidence:.2f}) "
            f"below threshold ({confidence_threshold:.2f})."
        )

    if raw.dose_confidence is not None and raw.dose_confidence < confidence_threshold:
        needs_review = True
        reasons.append(
            f"Dose confidence ({raw.dose_confidence:.2f}) "
            f"below threshold ({confidence_threshold:.2f})."
        )

    # Compile audit dictionary of evaluated confidence signals
    confidence_signals = {
        "drug_confidence": raw.drug_confidence,
        "strength_confidence": raw.strength_confidence,
        "dose_confidence": raw.dose_confidence,
        "timing_confidence": raw.timing_confidence,
        "meal_confidence": raw.meal_confidence,
        "duration_confidence": raw.duration_confidence,
    }

    # Final deterministic classification
    if is_rejected:
        status = SafetyDecisionStatus.REJECTED_UNSAFE
        is_safe = False
        requires_review = True
    elif needs_review:
        status = SafetyDecisionStatus.REQUIRES_REVIEW
        is_safe = False
        requires_review = True
    else:
        status = SafetyDecisionStatus.SAFE_TO_PROCESS
        is_safe = True
        requires_review = False

    return SafetyCheckResult(
        is_safe=is_safe,
        status=status,
        requires_review=requires_review,
        reasons=reasons,
        confidence_signals=confidence_signals,
    )


def evaluate_prescription_safety(
    raw_prescription: RawPrescriptionExtraction,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> SafetyCheckResult:
    """Evaluate document-level prescription safety."""
    reasons: list[str] = []

    if not raw_prescription.overall_legibility:
        return SafetyCheckResult(
            is_safe=False,
            status=SafetyDecisionStatus.REJECTED_UNSAFE,
            requires_review=True,
            reasons=["Overall prescription document marked illegible or unreadable."],
            confidence_signals={},
        )

    if not raw_prescription.medications:
        return SafetyCheckResult(
            is_safe=False,
            status=SafetyDecisionStatus.REQUIRES_REVIEW,
            requires_review=True,
            reasons=["No medications found in prescription extraction."],
            confidence_signals={},
        )

    # Check each medication's safety
    has_rejected = False
    has_review = False
    for idx, med in enumerate(raw_prescription.medications):
        med_result = evaluate_medication_safety(med, confidence_threshold=confidence_threshold)
        if med_result.status == SafetyDecisionStatus.REJECTED_UNSAFE:
            has_rejected = True
            reasons.extend([f"Medication [{idx}]: {r}" for r in med_result.reasons])
        elif med_result.status == SafetyDecisionStatus.REQUIRES_REVIEW:
            has_review = True
            reasons.extend([f"Medication [{idx}]: {r}" for r in med_result.reasons])

    if has_rejected:
        status = SafetyDecisionStatus.REJECTED_UNSAFE
        is_safe = False
        requires_review = True
    elif has_review:
        status = SafetyDecisionStatus.REQUIRES_REVIEW
        is_safe = False
        requires_review = True
    else:
        status = SafetyDecisionStatus.SAFE_TO_PROCESS
        is_safe = True
        requires_review = False

    return SafetyCheckResult(
        is_safe=is_safe,
        status=status,
        requires_review=requires_review,
        reasons=reasons,
        confidence_signals={},
    )
