"""Unit tests for Deterministic Normalization Service.

Covers:
- Supported timing patterns (Slot shorthands & Clinical abbreviations)
- Unsupported timing patterns fail-closed (preserve nulls, require review)
- Missing timing remains null (Rule 3)
- Missing dosage remains null (Rule 2)
- Missing meal instruction remains null (Rule 4)
- Missing duration remains null (Rule 5)
- Preserving raw extraction without mutation (Rule 1 & Immuntability)
- Full deterministic prescription pipeline
"""

import pytest

from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
)
from app.services.normalization import (
    normalize_dose,
    normalize_duration,
    normalize_meal_instruction,
    normalize_medication,
    normalize_strength,
    normalize_timing,
    process_prescription,
)

# ------------------------------------------------------------------------------
# Timing Normalization Tests
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_input,expected_m,expected_a,expected_e,expected_n,expected_sos",
    [
        ("1-0-0", True, False, False, False, False),
        ("0-1-0", False, True, False, False, False),
        ("0-0-1", False, False, False, True, False),
        ("1-0-1", True, False, False, True, False),
        ("1-1-1", True, True, False, True, False),
        ("1-1-0", True, True, False, False, False),
        ("0-1-1", False, True, False, True, False),
        ("1-1-1-1", True, True, True, True, False),
        ("1/2-0-1/2", True, False, False, True, False),
        ("OD", True, False, False, False, False),
        ("od", True, False, False, False, False),
        ("BD", True, False, False, True, False),
        ("bid", True, False, False, True, False),
        ("TDS", True, True, False, True, False),
        ("tid", True, True, False, True, False),
        ("QID", True, True, True, True, False),
        ("HS", False, False, False, True, False),
        ("SOS", False, False, False, False, True),
        ("PRN", False, False, False, False, True),
        ("STAT", True, False, False, False, False),
    ],
)
def test_supported_timing_patterns(
    raw_input: str,
    expected_m: bool,
    expected_a: bool,
    expected_e: bool,
    expected_n: bool,
    expected_sos: bool,
) -> None:
    """Test O: Supported timing patterns normalize into exact canonical booleans."""
    m, a, e, n, sos, notes, rev = normalize_timing(raw_input)
    assert m == expected_m
    assert a == expected_a
    assert e == expected_e
    assert n == expected_n
    assert sos == expected_sos
    assert rev is False
    assert len(notes) == 0


@pytest.mark.parametrize("unsupported_timing", ["xyz", "1-2", "1-?-1", "alternate day", "random"])
def test_unsupported_timing_pattern_fails_closed(unsupported_timing: str) -> None:
    """Test P: Unsupported timing pattern preserves nulls and triggers requires_review."""
    m, a, e, n, sos, notes, rev = normalize_timing(unsupported_timing)
    assert m is None
    assert a is None
    assert e is None
    assert n is None
    assert sos is False
    assert rev is True
    assert any("Unsupported timing pattern" in note for note in notes)


def test_missing_timing_must_remain_null() -> None:
    """Test Q: Missing timing must remain null (Rule 3: Never infer missing timing)."""
    m, a, e, n, sos, notes, rev = normalize_timing(None)
    assert m is None
    assert a is None
    assert e is None
    assert n is None
    assert sos is False
    assert rev is False
    assert len(notes) == 0


# ------------------------------------------------------------------------------
# Meal Instruction Tests
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_meal,expected_bm,expected_am",
    [
        ("after food", False, True),
        ("after meal", False, True),
        ("PC", False, True),
        ("post lunch", False, True),
        ("before food", True, False),
        ("empty stomach", True, False),
        ("AC", True, False),
        ("BBF", True, False),
        ("with food", False, False),
        ("with meal", False, False),
    ],
)
def test_supported_meal_instructions(
    raw_meal: str,
    expected_bm: bool,
    expected_am: bool,
) -> None:
    """Verify deterministic meal relation mapping."""
    bm, am, notes, rev = normalize_meal_instruction(raw_meal)
    assert bm == expected_bm
    assert am == expected_am
    assert rev is False


def test_missing_meal_instruction_remains_null() -> None:
    """Test K: Missing meal instruction remains null (Rule 4: Never infer meal timing)."""
    bm, am, notes, rev = normalize_meal_instruction(None)
    assert bm is None
    assert am is None
    assert rev is False


def test_unsupported_meal_instruction_triggers_review() -> None:
    """Unsupported meal string preserves null and flags review."""
    bm, am, notes, rev = normalize_meal_instruction("whenever convenient")
    assert bm is None
    assert am is None
    assert rev is True


# ------------------------------------------------------------------------------
# Dose & Strength Tests
# ------------------------------------------------------------------------------


def test_missing_dosage_must_remain_null() -> None:
    """Test R: Missing dosage must remain null (Rule 2: Never infer missing dosage)."""
    val, unit, notes, rev = normalize_dose(None)
    assert val is None
    assert unit is None
    assert rev is False


@pytest.mark.parametrize(
    "raw_dose,expected_val,expected_unit",
    [
        ("1 tablet", 1.0, "tablet"),
        ("2 tablets", 2.0, "tablets"),
        ("5 ml", 5.0, "ml"),
        ("2 drops", 2.0, "drops"),
        ("0.5 puff", 0.5, "puff"),
    ],
)
def test_supported_dosage_parsing(
    raw_dose: str,
    expected_val: float,
    expected_unit: str,
) -> None:
    """Verify parsing of explicit numerical dosage quantities."""
    val, unit, notes, rev = normalize_dose(raw_dose)
    assert val == expected_val
    assert unit == expected_unit
    assert rev is False


@pytest.mark.parametrize(
    "raw_str,expected_val,expected_unit",
    [
        ("500mg", 500.0, "mg"),
        ("650 mg", 650.0, "mg"),
        ("10 mcg", 10.0, "mcg"),
        ("1 g", 1.0, "g"),
        ("1 gm", 1.0, "g"),  # 'gm' normalized to 'g'
        ("100 iu", 100.0, "iu"),
    ],
)
def test_supported_strength_parsing(
    raw_str: str,
    expected_val: float,
    expected_unit: str,
) -> None:
    """Verify parsing and unit standardization for drug strength."""
    val, unit, notes, rev = normalize_strength(raw_str)
    assert val == expected_val
    assert unit == expected_unit


# ------------------------------------------------------------------------------
# Duration Tests
# ------------------------------------------------------------------------------


def test_missing_duration_must_remain_null() -> None:
    """Test L: Missing duration must remain null (Rule 5: Never infer duration)."""
    days, unit, notes, rev = normalize_duration(None)
    assert days is None
    assert unit is None
    assert rev is False


@pytest.mark.parametrize(
    "raw_dur,expected_val,expected_unit",
    [
        ("5 days", 5, "days"),
        ("1 day", 1, "day"),
        ("10 d", 10, "days"),
        ("1 week", 7, "days"),
        ("2 weeks", 14, "days"),
        ("1 month", 1, "month"),
        ("2 months", 2, "months"),
        ("1 m", 1, "month"),
        ("3 m", 3, "months"),
    ],
)
def test_supported_duration_parsing(
    raw_dur: str,
    expected_val: int,
    expected_unit: str,
) -> None:
    """Verify duration normalization preserves calendar units and values without guessing."""
    val, unit, notes, rev = normalize_duration(raw_dur)
    assert val == expected_val
    assert unit == expected_unit
    assert rev is False


def test_month_duration_preserved_and_raw_duration_unchanged() -> None:
    """Verify '1 month' is normalized to value=1, unit='month' and raw_duration is unchanged."""
    raw = RawMedicationExtraction(
        raw_drug_name="Atorvastatin",
        drug_confidence=0.95,
        raw_strength="20mg",
        raw_timing_text="HS",
        raw_duration="1 month",
    )
    norm = normalize_medication(raw)

    assert norm.duration_value == 1
    assert norm.duration_unit == "month"
    # Preserves raw_duration unchanged
    assert norm.raw_reference.raw_duration == "1 month"
    assert raw.raw_duration == "1 month"


# ------------------------------------------------------------------------------
# Medication & Preservation Tests
# ------------------------------------------------------------------------------


def test_never_guess_drug_name_and_preserve_raw() -> None:
    """Test S & Rule 1: Never guess drug name, preserve exact raw text and raw reference."""
    raw = RawMedicationExtraction(
        raw_drug_name="Lisi negoil",  # ambiguous / misspelled
        drug_confidence=0.88,
        raw_strength="10mg",
        raw_timing_text="1-0-0",
    )
    norm = normalize_medication(raw)

    # Must NOT become 'Lisinopril'
    assert norm.drug_name == "Lisi negoil"
    assert norm.raw_reference == raw
    assert norm.morning is True
    assert norm.night is False


def test_normalization_does_not_mutate_raw_data() -> None:
    """Test T: Normalization does not mutate raw data in any way."""
    raw = RawMedicationExtraction(
        raw_drug_name="Paracetamol",
        drug_confidence=0.98,
        raw_strength="650mg",
        raw_dose="1 tablet",
        raw_timing_text="1-0-1",
        raw_meal_instruction="after food",
        raw_duration="5 days",
    )
    # Deep copy representation before normalization
    initial_dict = raw.model_dump()

    norm = normalize_medication(raw)

    assert norm.raw_reference.model_dump() == initial_dict
    assert raw.model_dump() == initial_dict


def test_full_pipeline_prescription_processing() -> None:
    """Verify process_prescription produces valid ValidatedPrescription."""
    item1 = RawMedicationExtraction(
        raw_drug_name="Metformin",
        drug_confidence=0.95,
        raw_strength="500mg",
        raw_dose="1 tablet",
        raw_timing_text="1-0-1",
        raw_meal_instruction="after meals",
        raw_duration="30 days",
    )
    item2 = RawMedicationExtraction(
        raw_drug_name="Amoxicillin",
        drug_confidence=0.92,
        raw_strength="500mg",
        raw_timing_text="unsupported_timing",
    )

    raw_doc = RawPrescriptionExtraction(
        prescription_id="rx-test-01",
        overall_legibility=True,
        medications=[item1, item2],
    )

    validated = process_prescription(raw_doc)

    assert len(validated.medications) == 2
    # First med: safe & verified
    assert validated.medications[0].is_verified_safe is True
    assert validated.medications[0].normalized.morning is True
    assert validated.medications[0].normalized.after_meal is True
    assert validated.medications[0].normalized.duration_value == 30

    # Second med: unsupported timing -> requires_review, not verified safe
    assert validated.medications[1].is_verified_safe is False
    assert validated.medications[1].safety.requires_review is True
