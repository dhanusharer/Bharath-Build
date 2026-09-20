"""Prescription Pydantic Schemas.

Enforces strict separation between:
1. Raw AI Extraction (Untrusted, verbatim observation, immutable)
2. Normalized Data (Deterministic parsing, canonical formats)
3. Validated Data (Gated, verified safe for display or voice delivery)
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Strict numeric confidence score between 0.0 and 1.0.
# Rejects arbitrary strings (e.g. "medium", "0.8") and values out of range.
ConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        strict=True,
        description="Confidence score strictly bounded between 0.0 and 1.0.",
    ),
]


class SafetyDecisionStatus(StrEnum):
    """Deterministic safety gate classification."""

    SAFE_TO_PROCESS = "SAFE_TO_PROCESS"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    REJECTED_UNSAFE = "REJECTED_UNSAFE"


class RawMedicationExtraction(BaseModel):
    """Raw extraction model representing ONLY what the vision/LLM layer observed.

    This model is frozen/immutable to guarantee the raw observation is never
    overwritten or mutated during downstream normalization or validation.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    raw_drug_name: str | None = Field(
        default=None,
        description="Exact verbatim medication name transcribed from the image.",
    )
    drug_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for drug name extraction (0.0 to 1.0).",
    )
    raw_strength: str | None = Field(
        default=None,
        description="Raw strength notation (e.g., '500mg', '10 mcg').",
    )
    strength_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for strength extraction (0.0 to 1.0).",
    )
    raw_dose: str | None = Field(
        default=None,
        description="Raw dosage quantity (e.g., '1 tablet', '2 drops', '5 ml').",
    )
    dose_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for dose quantity extraction (0.0 to 1.0).",
    )
    raw_timing_text: str | None = Field(
        default=None,
        description="Raw timing shorthand (e.g., '1-0-1', 'OD', 'TDS', 'SOS').",
    )
    timing_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for timing extraction (0.0 to 1.0).",
    )
    raw_meal_instruction: str | None = Field(
        default=None,
        description="Raw meal instruction (e.g., 'after food', 'empty stomach', 'AC').",
    )
    meal_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for meal instruction extraction (0.0 to 1.0).",
    )
    raw_duration: str | None = Field(
        default=None,
        description="Raw duration text (e.g., '5 days', '2 weeks', '1 month').",
    )
    duration_confidence: ConfidenceScore | None = Field(
        default=None,
        description="Model confidence score for duration extraction (0.0 to 1.0).",
    )
    is_legible: bool = Field(
        default=True,
        description="False if handwriting or line token is smudged, clipped, or ambiguous.",
    )
    requires_review: bool = Field(
        default=False,
        description="True if model or extractor flagged ambiguity requiring human review.",
    )
    raw_notes: str | None = Field(
        default=None,
        description="Verbatim extractor notes or ambiguity reason.",
    )


class RawPrescriptionExtraction(BaseModel):
    """Raw prescription extraction envelope containing one or more medications."""

    model_config = ConfigDict(strict=True, frozen=True)

    prescription_id: str | None = Field(
        default=None,
        description="Unique identifier for the prescription session.",
    )
    overall_legibility: bool = Field(
        default=True,
        description="True if the general prescription document is decipherable.",
    )
    doctor_notes_raw: str | None = Field(
        default=None,
        description="Verbatim general doctor notes or clinical instructions.",
    )
    medications: list[RawMedicationExtraction] = Field(
        default_factory=list,
        description="List of raw medication items extracted from the document.",
    )


class NormalizedMedication(BaseModel):
    """Canonical normalized medication data derived purely from deterministic rules.

    Values are populated ONLY when deterministically parseable.
    Missing or unrecognized input leaves fields as None (unknown stays unknown).
    """

    model_config = ConfigDict(frozen=True)

    # Immutable link to the unadulterated raw extraction
    raw_reference: RawMedicationExtraction

    # Canonical drug name (verbatim string in Phase 1, never guessed or autocorrected)
    drug_name: str | None = Field(
        default=None,
        description="Preserved raw drug name. Never fuzzy-matched or inferred in Phase 1.",
    )

    # Metric strength
    strength_value: float | None = Field(
        default=None,
        description="Normalized numeric strength (e.g., 500.0).",
    )
    strength_unit: str | None = Field(
        default=None,
        description="Standardized unit (e.g., 'mg', 'g', 'mcg', 'ml', 'iu').",
    )

    # Dosage quantity
    dose_value: float | None = Field(
        default=None,
        description="Normalized numeric quantity (e.g., 1.0 tablet).",
    )
    dose_unit: str | None = Field(
        default=None,
        description="Standardized dose unit (e.g., 'tablet', 'capsule', 'ml', 'drops').",
    )

    # Canonical timing intervals (None = unstated/unknown)
    morning: bool | None = Field(
        default=None,
        description="Intake scheduled in morning.",
    )
    afternoon: bool | None = Field(
        default=None,
        description="Intake scheduled in afternoon.",
    )
    evening: bool | None = Field(
        default=None,
        description="Intake scheduled in evening.",
    )
    night: bool | None = Field(
        default=None,
        description="Intake scheduled at night / bedtime.",
    )
    is_as_needed_sos: bool = Field(
        default=False,
        description="True if medication is taken PRN / SOS (as needed).",
    )

    # Meal relationship (None = unstated/unknown)
    before_meal: bool | None = Field(
        default=None,
        description="True if taken before food / empty stomach.",
    )
    after_meal: bool | None = Field(
        default=None,
        description="True if taken after food / post-prandial.",
    )

    # Duration in standard days
    duration_value: int | None = Field(
        default=None,
        description="Normalized duration in calendar days.",
    )
    duration_unit: str | None = Field(
        default=None,
        description="Standard unit, canonicalized to 'days'.",
    )

    # Normalization audit trail
    normalization_notes: list[str] = Field(
        default_factory=list,
        description="Audit notes explaining any unparsed or unsupported tokens.",
    )
    requires_review: bool = Field(
        default=False,
        description="True if normalization encountered ambiguous or unsupported patterns.",
    )


class SafetyCheckResult(BaseModel):
    """Deterministic evaluation outcome from the safety gate."""

    model_config = ConfigDict(frozen=True)

    is_safe: bool = Field(
        ...,
        description="True ONLY if certified safe for downstream presentation or speech synthesis.",
    )
    status: SafetyDecisionStatus = Field(
        ...,
        description="Classification: SAFE_TO_PROCESS, REQUIRES_REVIEW, or REJECTED_UNSAFE.",
    )
    requires_review: bool = Field(
        ...,
        description="True if clinical human or pharmacist review is required.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Deterministic rejection or review reasons.",
    )
    confidence_signals: dict[str, float | None] = Field(
        default_factory=dict,
        description="Audit record of evaluated model confidence scores.",
    )


class ValidatedMedication(BaseModel):
    """Final gated entity pairing normalized data with authoritative safety decisions."""

    model_config = ConfigDict(frozen=True)

    normalized: NormalizedMedication
    safety: SafetyCheckResult
    is_verified_safe: bool = Field(
        ...,
        description="True only if both normalized without error and passed all safety gates.",
    )


class ValidatedPrescription(BaseModel):
    """Top-level validated prescription containing all verified medications."""

    model_config = ConfigDict(frozen=True)

    raw: RawPrescriptionExtraction
    overall_safety: SafetyCheckResult
    medications: list[ValidatedMedication] = Field(default_factory=list)
