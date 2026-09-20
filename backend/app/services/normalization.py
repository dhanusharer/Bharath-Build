"""Deterministic Normalization Service.

Converts explicit raw extracted strings into canonical medical data structures.
Strict Invariants:
1. Never guess drug names, dosages, timings, or durations.
2. If raw data is missing, normalized output remains None.
3. Unsupported or ambiguous patterns fail closed and require human review.
4. Raw extraction models are immutable and never mutated.
"""

import re

from app.schemas.prescription import (
    NormalizedMedication,
    RawMedicationExtraction,
    RawPrescriptionExtraction,
    SafetyCheckResult,
    SafetyDecisionStatus,
    ValidatedMedication,
    ValidatedPrescription,
)
from app.services.safety import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    evaluate_medication_safety,
    evaluate_prescription_safety,
)

# ------------------------------------------------------------------------------
# DETERMINISTIC TIMING DICTIONARY & REGEX PATTERNS
# Maps explicit timing shorthands to canonical (morning, afternoon, evening, night, SOS)
# ------------------------------------------------------------------------------
TimingTuple = tuple[bool | None, bool | None, bool | None, bool | None, bool]

_EXPLICIT_TIMING_MAP: dict[str, TimingTuple] = {
    # 3-Slot canonical (Morning, Afternoon, Evening=False, Night, SOS=False)
    "1-0-0": (True, False, False, False, False),
    "0-1-0": (False, True, False, False, False),
    "0-0-1": (False, False, False, True, False),
    "1-0-1": (True, False, False, True, False),
    "1-1-1": (True, True, False, True, False),
    "1-1-0": (True, True, False, False, False),
    "0-1-1": (False, True, False, True, False),
    # 4-Slot canonical (Morning, Afternoon, Evening, Night, SOS=False)
    "1-1-1-1": (True, True, True, True, False),
    # Fractional slot shorthand
    "1/2-0-1/2": (True, False, False, True, False),
    "0.5-0-0.5": (True, False, False, True, False),
    "1/2-0-0": (True, False, False, False, False),
    "0-0-1/2": (False, False, False, True, False),
    # Latin / Clinical Abbreviations
    "OD": (True, False, False, False, False),
    "QD": (True, False, False, False, False),
    "BD": (True, False, False, True, False),
    "BID": (True, False, False, True, False),
    "TDS": (True, True, False, True, False),
    "TID": (True, True, False, True, False),
    "QID": (True, True, True, True, False),
    "HS": (False, False, False, True, False),
    "BT": (False, False, False, True, False),
    "STAT": (True, False, False, False, False),
    # As needed / SOS
    "SOS": (False, False, False, False, True),
    "PRN": (False, False, False, False, True),
}

# ------------------------------------------------------------------------------
# REGEX PATTERNS FOR MEAL, DOSE, STRENGTH, DURATION
# ------------------------------------------------------------------------------
_BEFORE_MEAL_REGEX = re.compile(
    r"^(?:before\s+(?:food|meal|meals|eating)|empty\s+stomach|ac|bbf)$",
    re.IGNORECASE,
)
_AFTER_MEAL_REGEX = re.compile(
    r"^(?:after\s+(?:food|meal|meals|eating)|pc|post\s+lunch|post\s+dinner)$",
    re.IGNORECASE,
)
_WITH_MEAL_REGEX = re.compile(
    r"^(?:with\s+(?:food|meal|meals))$",
    re.IGNORECASE,
)

_STRENGTH_REGEX = re.compile(
    r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|g|gm|ml|iu|puffs?|drops?)?$",
    re.IGNORECASE,
)

_DOSE_REGEX = re.compile(
    r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)?$",
    re.IGNORECASE,
)

_DURATION_REGEX = re.compile(
    r"^(?:(?:x|for|\*)\s*)?(?P<value>\d+)\s*(?P<unit>days?|d|weeks?|w|months?|m)\.?$",
    re.IGNORECASE,
)

_DURATION_FRACTION_REGEX = re.compile(
    r"^(?:(?:x|for|\*)\s*)?(?P<value>\d+)\s*/\s*(?P<scale>7|52|12)\.?$",
    re.IGNORECASE,
)


def normalize_timing(
    raw_timing: str | None,
) -> tuple[bool | None, bool | None, bool | None, bool | None, bool, list[str], bool]:
    """Deterministically parse timing shorthand into morning, afternoon, evening, night.

    Returns:
    (morning, afternoon, evening, night, is_as_needed_sos, notes, requires_review)
    """
    if raw_timing is None:
        # Rule 3: Never infer missing timing.
        return None, None, None, None, False, [], False

    clean_timing = raw_timing.strip().upper()
    if not clean_timing:
        return None, None, None, None, False, [], False

    if clean_timing in _EXPLICIT_TIMING_MAP:
        m, a, e, n, sos = _EXPLICIT_TIMING_MAP[clean_timing]
        return m, a, e, n, sos, [], False

    # Unsupported timing pattern - Fail Closed, Never Guess
    note = f"Unsupported timing pattern: '{raw_timing}'. Preserving nulls; manual review required."
    return None, None, None, None, False, [note], True


def normalize_meal_instruction(
    raw_meal: str | None,
) -> tuple[bool | None, bool | None, list[str], bool]:
    """Deterministically parse meal relation into (before_meal, after_meal).

    Returns:
    (before_meal, after_meal, notes, requires_review)
    """
    if raw_meal is None:
        # Rule 4: Never infer missing meal instructions.
        return None, None, [], False

    clean_meal = raw_meal.strip()
    if not clean_meal:
        return None, None, [], False

    if _BEFORE_MEAL_REGEX.match(clean_meal):
        return True, False, [], False

    if _AFTER_MEAL_REGEX.match(clean_meal):
        return False, True, [], False

    if _WITH_MEAL_REGEX.match(clean_meal):
        return False, False, [], False

    # Check for explicitly unstated values
    if clean_meal.lower() in ("null", "none", "unspecified"):
        return None, None, [], False

    note = f"Unsupported meal instruction: '{raw_meal}'. Manual review required."
    return None, None, [note], True


def normalize_dose(
    raw_dose: str | None,
) -> tuple[float | None, str | None, list[str], bool]:
    """Deterministically parse raw dosage into numeric value and canonical unit.

    Returns:
    (dose_value, dose_unit, notes, requires_review)
    """
    if raw_dose is None:
        # Rule 2: Never infer missing dosage.
        return None, None, [], False

    clean_dose = raw_dose.strip()
    if not clean_dose:
        return None, None, [], False

    match = _DOSE_REGEX.match(clean_dose)
    if match:
        val = float(match.group("value"))
        raw_unit = match.group("unit")
        unit = raw_unit.lower() if raw_unit else None
        return val, unit, [], False

    note = f"Unparseable dosage expression: '{raw_dose}'."
    return None, None, [note], True


def normalize_strength(
    raw_strength: str | None,
) -> tuple[float | None, str | None, list[str], bool]:
    """Deterministically parse raw strength into numeric value and canonical metric unit."""
    if raw_strength is None:
        return None, None, [], False

    clean_str = raw_strength.strip()
    if not clean_str:
        return None, None, [], False

    match = _STRENGTH_REGEX.match(clean_str)
    if match:
        val = float(match.group("value"))
        raw_unit = match.group("unit")
        if raw_unit:
            unit_lower = raw_unit.lower()
            # Standardize 'gm' to canonical 'g'
            unit = "g" if unit_lower == "gm" else unit_lower
            return val, unit, [], False
        return val, None, ["Strength unit missing from raw extraction."], False

    note = f"Unparseable strength expression: '{raw_strength}'."
    return None, None, [note], True


def normalize_duration(
    raw_duration: str | None,
) -> tuple[int | None, str | None, list[str], bool]:
    """Deterministically parse raw duration into integer value and canonical unit.

    Strict Invariants:
    - Never infer missing duration.
    - '1 month' is preserved as value=1, unit='month' rather than converting to 30 days.
    - Raw duration remains unchanged on raw_reference.
    """
    if raw_duration is None:
        # Rule 5: Never infer duration when raw duration is missing.
        return None, None, [], False

    clean_dur = raw_duration.strip()
    if not clean_dur:
        return None, None, [], False

    match = _DURATION_REGEX.match(clean_dur)
    if match:
        value = int(match.group("value"))
        unit_str = match.group("unit").lower()

        if unit_str in ("month", "months", "m"):
            unit = "month" if value == 1 else "months"
            return value, unit, [], False
        if unit_str in ("day", "days", "d"):
            unit = "day" if value == 1 else "days"
            return value, unit, [], False
        if unit_str in ("week", "weeks", "w"):
            return value * 7, "days", [], False

        return None, None, [f"Unrecognized duration unit: '{unit_str}'."], True

    frac_match = _DURATION_FRACTION_REGEX.match(clean_dur)
    if frac_match:
        value = int(frac_match.group("value"))
        scale = frac_match.group("scale")
        if scale == "7":
            unit = "day" if value == 1 else "days"
            return value, unit, [], False
        if scale == "52":
            return value * 7, "days", [], False
        if scale == "12":
            unit = "month" if value == 1 else "months"
            return value, unit, [], False

    note = f"Unparseable duration text: '{raw_duration}'."
    return None, None, [note], True


def normalize_medication(raw: RawMedicationExtraction) -> NormalizedMedication:
    """Deterministically normalize raw medication extraction into canonical structure.

    Pure function: Does NOT mutate raw input.
    """
    all_notes: list[str] = []
    requires_review = False

    # Rule 1: Never infer or fuzzy-match drug names in Phase 1
    drug_name = raw.raw_drug_name

    # Parse Strength
    s_val, s_unit, s_notes, s_rev = normalize_strength(raw.raw_strength)
    all_notes.extend(s_notes)
    requires_review = requires_review or s_rev

    # Parse Dose
    d_val, d_unit, d_notes, d_rev = normalize_dose(raw.raw_dose)
    all_notes.extend(d_notes)
    requires_review = requires_review or d_rev

    # Parse Timing
    m, a, e, n, sos, t_notes, t_rev = normalize_timing(raw.raw_timing_text)
    all_notes.extend(t_notes)
    requires_review = requires_review or t_rev

    # Parse Meal Instruction
    bm, am, m_notes, m_rev = normalize_meal_instruction(raw.raw_meal_instruction)
    all_notes.extend(m_notes)
    requires_review = requires_review or m_rev

    # Parse Duration
    dur_val, dur_unit, dur_notes, dur_rev = normalize_duration(raw.raw_duration)
    all_notes.extend(dur_notes)
    requires_review = requires_review or dur_rev

    return NormalizedMedication(
        raw_reference=raw,
        drug_name=drug_name,
        strength_value=s_val,
        strength_unit=s_unit,
        dose_value=d_val,
        dose_unit=d_unit,
        morning=m,
        afternoon=a,
        evening=e,
        night=n,
        is_as_needed_sos=sos,
        before_meal=bm,
        after_meal=am,
        duration_value=dur_val,
        duration_unit=dur_unit,
        normalization_notes=all_notes,
        requires_review=requires_review,
    )


def process_prescription(
    raw_prescription: RawPrescriptionExtraction,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ValidatedPrescription:
    """Run full deterministic validation and normalization pipeline on a prescription extraction."""
    overall_safety = evaluate_prescription_safety(
        raw_prescription,
        confidence_threshold=confidence_threshold,
    )

    validated_meds: list[ValidatedMedication] = []
    for med in raw_prescription.medications:
        # 1. Safety Gate Evaluation
        med_safety = evaluate_medication_safety(med, confidence_threshold=confidence_threshold)

        # 2. Deterministic Normalization
        norm_med = normalize_medication(med)

        # 3. Reconcile safety with normalization errors
        final_safety = med_safety
        if norm_med.requires_review and med_safety.is_safe:
            # Downgrade to REQUIRES_REVIEW if normalization found unparseable critical tokens
            reasons = list(med_safety.reasons) + norm_med.normalization_notes
            final_safety = SafetyCheckResult(
                is_safe=False,
                status=SafetyDecisionStatus.REQUIRES_REVIEW,
                requires_review=True,
                reasons=reasons,
                confidence_signals=med_safety.confidence_signals,
            )

        is_verified_safe = final_safety.is_safe and not norm_med.requires_review

        validated_meds.append(
            ValidatedMedication(
                normalized=norm_med,
                safety=final_safety,
                is_verified_safe=is_verified_safe,
            )
        )

    # 4. Reconcile overall prescription safety with medication safety and normalization
    has_unsafe_med = any(
        vm.safety.status == SafetyDecisionStatus.REJECTED_UNSAFE
        or (not vm.safety.is_safe and not vm.safety.requires_review)
        for vm in validated_meds
    )
    has_review_med = any(
        vm.safety.requires_review
        or not vm.is_verified_safe
        or vm.normalized.requires_review
        for vm in validated_meds
    )

    if has_unsafe_med:
        reasons = list(overall_safety.reasons)
        for vm in validated_meds:
            if vm.safety.status == SafetyDecisionStatus.REJECTED_UNSAFE:
                for r in vm.safety.reasons:
                    if r not in reasons:
                        reasons.append(r)
        overall_safety = SafetyCheckResult(
            is_safe=False,
            status=SafetyDecisionStatus.REJECTED_UNSAFE,
            requires_review=False,
            reasons=reasons,
            confidence_signals=overall_safety.confidence_signals,
        )
    elif has_review_med and overall_safety.is_safe:
        reasons = list(overall_safety.reasons)
        for vm in validated_meds:
            if vm.safety.requires_review or not vm.is_verified_safe:
                for r in vm.safety.reasons:
                    if r not in reasons:
                        reasons.append(r)
        overall_safety = SafetyCheckResult(
            is_safe=False,
            status=SafetyDecisionStatus.REQUIRES_REVIEW,
            requires_review=True,
            reasons=reasons,
            confidence_signals=overall_safety.confidence_signals,
        )

    return ValidatedPrescription(
        raw=raw_prescription,
        overall_safety=overall_safety,
        medications=validated_meds,
    )
