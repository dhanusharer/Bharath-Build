"""Unit tests for BedrockPrescriptionExtractor Adapter.

All tests are strictly mocked and deterministic. Zero calls to real AWS services.
Covers:
- Valid image extraction
- Multiple medications
- Uncertain drug name
- Null dosage & null timing
- Unreadable prescription
- Malformed model responses
- Schema validation failure
- Unsupported MIME type & empty image
- Bedrock timeout, access denied, auth failure, throttling
- Realistic handwritten prescription fixture
"""

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError, ConnectTimeoutError, NoCredentialsError

from app.providers.bedrock.config import BedrockProviderConfig
from app.providers.bedrock.exceptions import (
    BedrockAccessDeniedError,
    BedrockAuthError,
    BedrockModelUnavailableError,
    BedrockThrottlingError,
    BedrockTimeoutError,
    EmptyImageError,
    MalformedResponseError,
    SchemaValidationError,
    UnsupportedImageTypeError,
)
from app.providers.bedrock.prescription_extractor import BedrockPrescriptionExtractor

SAMPLE_IMAGE_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # Valid JPEG magic bytes stub


def make_converse_response(payload: dict) -> dict:
    """Helper creating standard Bedrock Converse API tool-use response."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tooluse_abc123",
                            "name": "record_prescription_extraction",
                            "input": payload,
                        }
                    }
                ],
            }
        },
        "stopReason": "tool_use",
        "usage": {"inputTokens": 150, "outputTokens": 80, "totalTokens": 230},
    }


def make_text_json_response(payload: dict) -> dict:
    """Helper creating Bedrock Converse response with JSON text block."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "text": json.dumps(payload),
                    }
                ],
            }
        },
        "stopReason": "end_turn",
    }


# ------------------------------------------------------------------------------
# 1. Valid Image Extraction Tests
# ------------------------------------------------------------------------------


def test_valid_image_extraction() -> None:
    """Test 1: Valid single medication extraction via Bedrock tool-use."""
    mock_client = MagicMock()
    payload = {
        "prescription_id": "rx-bedrock-001",
        "overall_legibility": True,
        "doctor_notes_raw": "Review in 2 weeks",
        "medications": [
            {
                "raw_drug_name": "Metformin",
                "drug_confidence": 0.96,
                "raw_strength": "500mg",
                "strength_confidence": 0.94,
                "raw_dose": "1 tablet",
                "dose_confidence": 0.92,
                "raw_timing_text": "1-0-1",
                "timing_confidence": 0.95,
                "raw_meal_instruction": "after food",
                "meal_confidence": 0.90,
                "raw_duration": "30 days",
                "duration_confidence": 0.88,
                "is_legible": True,
                "requires_review": False,
            }
        ],
    }
    mock_client.converse.return_value = make_converse_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg", request_id="req-1")

    assert result.prescription_id == "rx-bedrock-001"
    assert result.overall_legibility is True
    assert len(result.medications) == 1
    med = result.medications[0]
    assert med.raw_drug_name == "Metformin"
    assert med.drug_confidence == 0.96
    assert med.raw_strength == "500mg"
    assert med.raw_timing_text == "1-0-1"
    assert med.is_legible is True


def test_multiple_medications_extraction() -> None:
    """Test 2: Multiple medications parsed from single prescription image."""
    mock_client = MagicMock()
    payload = {
        "prescription_id": "rx-multi-002",
        "overall_legibility": True,
        "medications": [
            {"raw_drug_name": "Paracetamol", "drug_confidence": 0.95, "raw_timing_text": "1-0-1"},
            {"raw_drug_name": "Amoxicillin", "drug_confidence": 0.90, "raw_timing_text": "TDS"},
            {"raw_drug_name": "Pantoprazole", "drug_confidence": 0.92, "raw_timing_text": "OD"},
        ],
    }
    mock_client.converse.return_value = make_converse_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/png")

    assert len(result.medications) == 3
    assert [m.raw_drug_name for m in result.medications] == [
        "Paracetamol",
        "Amoxicillin",
        "Pantoprazole",
    ]


def test_text_block_json_fallback() -> None:
    """Verify fallback parsing when model returns structured JSON in a text block."""
    mock_client = MagicMock()
    payload = {
        "prescription_id": "rx-fallback-003",
        "overall_legibility": True,
        "medications": [
            {"raw_drug_name": "Cetirizine", "drug_confidence": 0.95, "raw_timing_text": "HS"}
        ],
    }
    mock_client.converse.return_value = make_text_json_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/webp")

    assert result.prescription_id == "rx-fallback-003"
    assert len(result.medications) == 1
    assert result.medications[0].raw_drug_name == "Cetirizine"


# ------------------------------------------------------------------------------
# 2. Raw Uncertainty & Missing Fields Handling
# ------------------------------------------------------------------------------


def test_uncertain_drug_name_extracted_verbatim() -> None:
    """Test 3: Uncertain or misspelled handwriting is preserved as verbatim text."""
    mock_client = MagicMock()
    payload = {
        "overall_legibility": True,
        "medications": [
            {
                "raw_drug_name": "Lisi?negoil",
                "drug_confidence": 0.65,
                "raw_timing_text": "1-0-0",
                "requires_review": True,
                "raw_notes": "Middle characters smeared",
            }
        ],
    }
    mock_client.converse.return_value = make_converse_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")

    med = result.medications[0]
    assert med.raw_drug_name == "Lisi?negoil"
    assert med.drug_confidence == 0.65
    assert med.requires_review is True


def test_null_dosage_and_null_timing() -> None:
    """Tests 4 & 5: Unstated dosage and timing correctly output nulls."""
    mock_client = MagicMock()
    payload = {
        "overall_legibility": True,
        "medications": [
            {
                "raw_drug_name": "Azithromycin",
                "drug_confidence": 0.94,
                "raw_strength": None,
                "raw_dose": None,
                "raw_timing_text": None,
                "raw_meal_instruction": None,
                "raw_duration": None,
            }
        ],
    }
    mock_client.converse.return_value = make_converse_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")

    med = result.medications[0]
    assert med.raw_strength is None
    assert med.raw_dose is None
    assert med.raw_timing_text is None
    assert med.raw_meal_instruction is None
    assert med.raw_duration is None


def test_unreadable_prescription() -> None:
    """Test 6: Illegible or severely smudged prescription document."""
    mock_client = MagicMock()
    payload = {
        "overall_legibility": False,
        "doctor_notes_raw": "Entire page water damaged",
        "medications": [],
    }
    mock_client.converse.return_value = make_converse_response(payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")

    assert result.overall_legibility is False
    assert len(result.medications) == 0


# ------------------------------------------------------------------------------
# 3. Input Validation & Error Handling Tests
# ------------------------------------------------------------------------------


def test_empty_image_payload_raises_error() -> None:
    """Verify empty image bytes payload is rejected immediately."""
    extractor = BedrockPrescriptionExtractor()
    with pytest.raises(EmptyImageError) as exc_info:
        extractor.extract(b"", "image/jpeg")
    assert "empty" in exc_info.value.message.lower()


@pytest.mark.parametrize(
    "invalid_mime", ["image/gif", "application/pdf", "text/plain", "image/bmp"]
)
def test_unsupported_mime_type_rejected(invalid_mime: str) -> None:
    """Test 9: Non-supported MIME formats are rejected cleanly."""
    extractor = BedrockPrescriptionExtractor()
    with pytest.raises(UnsupportedImageTypeError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, invalid_mime)
    assert invalid_mime in exc_info.value.message


def test_malformed_response_raises_error() -> None:
    """Test 7: Response missing valid tool input raises MalformedResponseError."""
    mock_client = MagicMock()
    # Response without toolUse or JSON text
    mock_client.converse.return_value = {
        "output": {"message": {"role": "assistant", "content": [{"text": "Hello, I am Claude."}]}}
    }

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(MalformedResponseError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.error_code == "MALFORMED_MODEL_RESPONSE"


def test_schema_validation_failure_raises_error() -> None:
    """Test 8: Model payload violating Pydantic schema constraints fails safely."""
    mock_client = MagicMock()
    # Confidence > 1.0 violates ConfidenceScore constraint
    invalid_payload = {
        "overall_legibility": True,
        "medications": [
            {
                "raw_drug_name": "Aspirin",
                "drug_confidence": 2.5,  # Invalid
            }
        ],
    }
    mock_client.converse.return_value = make_converse_response(invalid_payload)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(SchemaValidationError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.error_code == "SCHEMA_VALIDATION_FAILURE"


# ------------------------------------------------------------------------------
# 4. AWS / Bedrock Upstream Error Mapping Tests
# ------------------------------------------------------------------------------


def test_bedrock_timeout_raises_timeout_error() -> None:
    """Test 10: Connection or read timeout raises BedrockTimeoutError."""
    mock_client = MagicMock()
    mock_client.converse.side_effect = ConnectTimeoutError(endpoint_url="https://bedrock.test")

    config = BedrockProviderConfig(timeout_seconds=15.0)
    extractor = BedrockPrescriptionExtractor(config=config, client=mock_client)

    with pytest.raises(BedrockTimeoutError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.retryable is True
    assert "timed out" in exc_info.value.message


def test_bedrock_access_denied_error() -> None:
    """Test 11: AccessDeniedException maps to BedrockAccessDeniedError."""
    mock_client = MagicMock()
    error_response = {
        "Error": {"Code": "AccessDeniedException", "Message": "You don't have access to this model"}
    }
    mock_client.converse.side_effect = ClientError(error_response, "Converse")

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(BedrockAccessDeniedError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.error_code == "BEDROCK_ACCESS_DENIED"


def test_bedrock_throttling_error() -> None:
    """Test 12: ThrottlingException maps to retryable BedrockThrottlingError."""
    mock_client = MagicMock()
    error_response = {"Error": {"Code": "ThrottlingException", "Message": "Rate limit exceeded"}}
    mock_client.converse.side_effect = ClientError(error_response, "Converse")

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(BedrockThrottlingError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.retryable is True
    assert exc_info.value.error_code == "BEDROCK_THROTTLED"


def test_bedrock_auth_failure_error() -> None:
    """Verify NoCredentialsError maps to BedrockAuthError."""
    mock_client = MagicMock()
    mock_client.converse.side_effect = NoCredentialsError()

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(BedrockAuthError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.error_code == "BEDROCK_AUTH_FAILURE"


def test_bedrock_model_unavailable_error() -> None:
    """Verify ResourceNotFoundException maps to BedrockModelUnavailableError."""
    mock_client = MagicMock()
    error_response = {
        "Error": {"Code": "ResourceNotFoundException", "Message": "Model ID not found"}
    }
    mock_client.converse.side_effect = ClientError(error_response, "Converse")

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    with pytest.raises(BedrockModelUnavailableError) as exc_info:
        extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")
    assert exc_info.value.error_code == "BEDROCK_MODEL_UNAVAILABLE"


# ------------------------------------------------------------------------------
# 5. Realistic Handwritten Prescription Fixture Test
# ------------------------------------------------------------------------------


def test_realistic_handwritten_prescription_fixture() -> None:
    """Verify a comprehensive, realistic multi-drug Indian outpatient prescription fixture."""
    mock_client = MagicMock()
    realistic_fixture = {
        "prescription_id": "rx-india-outpatient-2026-09",
        "overall_legibility": True,
        "doctor_notes_raw": "Review after 5 days with FBS report. Avoid oily food.",
        "medications": [
            {
                "raw_drug_name": "Tab Metformin SR",
                "drug_confidence": 0.97,
                "raw_strength": "500 mg",
                "strength_confidence": 0.95,
                "raw_dose": "1 tab",
                "dose_confidence": 0.94,
                "raw_timing_text": "1-0-1",
                "timing_confidence": 0.98,
                "raw_meal_instruction": "after food",
                "meal_confidence": 0.96,
                "raw_duration": "1 month",
                "duration_confidence": 0.92,
                "is_legible": True,
                "requires_review": False,
                "raw_notes": "Clear block lettering",
            },
            {
                "raw_drug_name": "Cap Amox",
                "drug_confidence": 0.91,
                "raw_strength": "500mg",
                "strength_confidence": 0.90,
                "raw_dose": "1 cap",
                "dose_confidence": 0.89,
                "raw_timing_text": "TDS",
                "timing_confidence": 0.93,
                "raw_meal_instruction": "PC",
                "meal_confidence": 0.88,
                "raw_duration": "5 days",
                "duration_confidence": 0.95,
                "is_legible": True,
                "requires_review": False,
                "raw_notes": "Slight cursive flourish",
            },
            {
                "raw_drug_name": "Tab Pantocid",
                "drug_confidence": 0.94,
                "raw_strength": "40mg",
                "strength_confidence": 0.92,
                "raw_dose": "1 tab",
                "dose_confidence": 0.90,
                "raw_timing_text": "1-0-0",
                "timing_confidence": 0.96,
                "raw_meal_instruction": "empty stomach",
                "meal_confidence": 0.95,
                "raw_duration": "10 days",
                "duration_confidence": 0.90,
                "is_legible": True,
                "requires_review": False,
            },
        ],
    }
    mock_client.converse.return_value = make_converse_response(realistic_fixture)

    extractor = BedrockPrescriptionExtractor(client=mock_client)
    result = extractor.extract(SAMPLE_IMAGE_BYTES, "image/jpeg")

    assert result.prescription_id == "rx-india-outpatient-2026-09"
    assert len(result.medications) == 3
    # Check all fields populated without loss
    m1 = result.medications[0]
    assert m1.raw_drug_name == "Tab Metformin SR"
    assert m1.raw_duration == "1 month"
    assert m1.raw_timing_text == "1-0-1"
