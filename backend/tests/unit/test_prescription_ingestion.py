"""Comprehensive Unit and Integration Tests for Phase 3 Prescription Ingestion API & Persistence.

Tests required by Phase 3 specification:
1. successful upload
2. unsupported MIME type
3. empty file
4. oversized file (>10MB)
5. S3 upload failure
6. successful extraction
7. low-confidence extraction
8. unreadable prescription
9. normalization result persistence
10. database failure
11. GET existing prescription
12. GET unknown prescription ID (404)
13. processing failure
14. request ID propagation
"""

import io
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import (
    get_extraction_service,
    get_prescription_repository,
    get_storage_port,
)
from app.db.models import Base, PrescriptionStatus
from app.db.session import get_db_session
from app.main import app
from app.ports.prescription_extractor import VisionExtractionPort
from app.ports.storage import ObjectStoragePort
from app.providers.bedrock.exceptions import (
    BedrockExtractionError,
    BedrockTimeoutError,
)
from app.providers.storage.exceptions import StorageError, StorageUploadError
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.prescription import (
    RawMedicationExtraction,
    RawPrescriptionExtraction,
)
from app.services.prescription_extraction import PrescriptionExtractionService
from app.services.prescription_ingestion import PrescriptionIngestionService

# ------------------------------------------------------------------------------
# Mock In-Memory Storage Port
# ------------------------------------------------------------------------------


class InMemoryStoragePort(ObjectStoragePort):
    """In-memory object storage mock that simulates S3 operations without AWS."""

    def __init__(self, should_fail_upload: bool = False) -> None:
        self.storage: dict[str, bytes] = {}
        self.should_fail_upload = should_fail_upload

    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if self.should_fail_upload:
            raise StorageUploadError(key=key, details="Simulated S3 connection failure")
        self.storage[key] = data
        return key

    def get_object(self, key: str) -> bytes:
        if key not in self.storage:
            raise StorageError(f"Key {key} not found", key=key)
        return self.storage[key]

    def delete_object(self, key: str) -> bool:
        if key in self.storage:
            del self.storage[key]
            return True
        return False

    def generate_presigned_url(self, key: str, expiration_seconds: int = 900) -> str:
        return f"https://mock-s3.amazonaws.com/{key}?expires={expiration_seconds}"


# ------------------------------------------------------------------------------
# Mock Vision Extractor Port
# ------------------------------------------------------------------------------


class MockVisionExtractor(VisionExtractionPort):
    """Deterministic mock extractor for testing various multimodal responses."""

    def __init__(
        self,
        response_factory: Any = None,
        should_fail: bool = False,
    ) -> None:
        self.response_factory = response_factory
        self.should_fail = should_fail

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        request_id: str | None = None,
    ) -> RawPrescriptionExtraction:
        if self.should_fail:
            raise BedrockTimeoutError(timeout_seconds=30.0, request_id=request_id)
        if self.response_factory:
            return self.response_factory()

        # Default: high confidence Metformin 500mg
        return RawPrescriptionExtraction(
            prescription_id="test-rx-id",
            overall_legibility=True,
            medications=[
                RawMedicationExtraction(
                    raw_drug_name="Metformin",
                    drug_confidence=0.95,
                    raw_strength="500mg",
                    strength_confidence=0.94,
                    raw_dose="1 tablet",
                    dose_confidence=0.95,
                    raw_timing_text="1-0-1",
                    timing_confidence=0.95,
                    raw_meal_instruction="after food",
                    meal_confidence=0.92,
                    raw_duration="1 month",
                    duration_confidence=0.90,
                    is_legible=True,
                    requires_review=False,
                )
            ],
        )


# ------------------------------------------------------------------------------
# Test SQLite In-Memory Database Fixture
# ------------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db_session():
    """Create a fresh in-memory SQLite database session for each test."""
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_maker() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
def mock_storage():
    return InMemoryStoragePort()


@pytest.fixture
def mock_extractor():
    return MockVisionExtractor()


@pytest.fixture
async def client(test_db_session: AsyncSession, mock_storage: InMemoryStoragePort, mock_extractor: MockVisionExtractor):
    """Provide an AsyncClient configured with overridden DB, S3, and Extractor dependencies."""
    app.dependency_overrides[get_db_session] = lambda: test_db_session
    app.dependency_overrides[get_storage_port] = lambda: mock_storage
    app.dependency_overrides[get_extraction_service] = lambda: PrescriptionExtractionService(extractor=mock_extractor)
    app.dependency_overrides[get_prescription_repository] = lambda: PrescriptionRepository(session=test_db_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ------------------------------------------------------------------------------
# Phase 3 Test Cases
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_1_successful_upload(client: AsyncClient, mock_storage: InMemoryStoragePort):
    """1. Successful upload: Valid JPEG returns HTTP 201 with completed status and verified medications."""
    file_content = b"\xff\xd8\xff\xe0" + b"fake-jpeg-content-for-testing"
    files = {"file": ("prescription.jpg", io.BytesIO(file_content), "image/jpeg")}
    headers = {"X-Request-ID": "req-upload-001"}

    response = await client.post("/api/v1/prescriptions", files=files, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["request_id"] == "req-upload-001"
    assert data["status"] == "COMPLETED"
    assert data["requires_review"] is False
    assert len(data["medications"]) == 1

    med = data["medications"][0]
    assert med["drug_name"] == "Metformin"
    assert med["is_verified_safe"] is True
    assert med["strength"]["value"] == 500.0
    assert med["strength"]["unit"] == "mg"
    assert med["dose"]["value"] == 1.0
    assert med["dose"]["unit"] == "tablet"
    assert med["schedule"]["morning"] is True
    assert med["schedule"]["evening"] is False
    assert med["schedule"]["night"] is True
    assert med["meal_instruction"]["after_meal"] is True
    assert med["duration"]["value"] == 1
    assert med["duration"]["unit"] == "month"
    assert med["duration"]["raw_text"] == "1 month"

    # Verify S3 mock received the payload
    assert len(mock_storage.storage) == 1


@pytest.mark.asyncio
async def test_2_unsupported_mime_type(client: AsyncClient):
    """2. Unsupported MIME type: PDF or text files rejected with 400 Bad Request."""
    files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4..."), "application/pdf")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["code"] == "INVALID_IMAGE_PAYLOAD"
    assert "Unsupported media type" in data["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_3_empty_file(client: AsyncClient):
    """3. Empty file: 0-byte upload rejected with 400 Bad Request."""
    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"]["code"] == "INVALID_IMAGE_PAYLOAD"
    assert "empty" in data["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_4_oversized_file(client: AsyncClient):
    """4. Oversized file: Payload exceeding 10MB rejected with 413 Entity Too Large."""
    ten_mb_plus = b"X" * (10 * 1024 * 1024 + 1024)
    files = {"file": ("huge.jpg", io.BytesIO(ten_mb_plus), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 413
    data = response.json()
    assert data["detail"]["error"]["code"] == "FILE_SIZE_EXCEEDED"


@pytest.mark.asyncio
async def test_5_s3_upload_failure(client: AsyncClient, mock_storage: InMemoryStoragePort):
    """5. S3 upload failure: Storage error handled gracefully without leaking credentials (HTTP 500)."""
    mock_storage.should_fail_upload = True
    files = {"file": ("rx.webp", io.BytesIO(b"RIFF....WEBP"), "image/webp")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert "securely storing" in data["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_6_successful_extraction(client: AsyncClient):
    """6. Successful extraction: Verifies full multi-medication extraction pipeline."""
    def two_meds_factory():
        return RawPrescriptionExtraction(
            prescription_id="rx-multi-01",
            overall_legibility=True,
            medications=[
                RawMedicationExtraction(
                    raw_drug_name="Metformin",
                    drug_confidence=0.95,
                    raw_strength="500mg",
                    raw_dose="1 tab",
                    raw_timing_text="1-0-1",
                    is_legible=True,
                ),
                RawMedicationExtraction(
                    raw_drug_name="Pantocid",
                    drug_confidence=0.92,
                    raw_strength="40mg",
                    raw_dose="1 tab",
                    raw_timing_text="1-0-0",
                    raw_meal_instruction="before food",
                    raw_duration="15 days",
                    is_legible=True,
                ),
            ],
        )

    app.dependency_overrides[get_extraction_service] = lambda: PrescriptionExtractionService(
        extractor=MockVisionExtractor(response_factory=two_meds_factory)
    )

    files = {"file": ("rx.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "COMPLETED"
    assert len(data["medications"]) == 2
    assert data["medications"][0]["drug_name"] == "Metformin"
    assert data["medications"][1]["drug_name"] == "Pantocid"
    assert data["medications"][1]["meal_instruction"]["before_meal"] is True


@pytest.mark.asyncio
async def test_7_low_confidence_extraction(client: AsyncClient):
    """7. Low-confidence extraction: Triggers REQUIRES_REVIEW and flags safety reasons."""
    def low_conf_factory():
        return RawPrescriptionExtraction(
            prescription_id="rx-low-conf",
            overall_legibility=True,
            medications=[
                RawMedicationExtraction(
                    raw_drug_name="Amoxicillin",
                    drug_confidence=0.60,  # Below 0.85 threshold
                    raw_strength="500mg",
                    raw_dose="1 cap",
                    raw_timing_text="TDS",
                    is_legible=True,
                )
            ],
        )

    app.dependency_overrides[get_extraction_service] = lambda: PrescriptionExtractionService(
        extractor=MockVisionExtractor(response_factory=low_conf_factory)
    )

    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "REQUIRES_REVIEW"
    assert data["requires_review"] is True
    assert any("Confidence" in r for r in data["safety_reasons"])
    assert data["medications"][0]["is_verified_safe"] is False


@pytest.mark.asyncio
async def test_8_unreadable_prescription(client: AsyncClient):
    """8. Unreadable prescription: Fatal illegibility triggers REQUIRES_REVIEW with refusal explanation."""
    def unreadable_factory():
        return RawPrescriptionExtraction(
            prescription_id="rx-unreadable",
            overall_legibility=False,
            medications=[
                RawMedicationExtraction(
                    raw_drug_name=None,
                    is_legible=False,
                )
            ],
        )

    app.dependency_overrides[get_extraction_service] = lambda: PrescriptionExtractionService(
        extractor=MockVisionExtractor(response_factory=unreadable_factory)
    )

    files = {"file": ("blurred.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "REQUIRES_REVIEW"
    assert data["requires_review"] is True
    assert any("illegible" in r.lower() or "unreadable" in r.lower() for r in data["safety_reasons"])


@pytest.mark.asyncio
async def test_9_normalization_result_persistence(client: AsyncClient, test_db_session: AsyncSession):
    """9. Normalization result persistence: Database models correctly persist raw and normalized records."""
    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)
    assert response.status_code == 201
    rx_id = response.json()["prescription_id"]

    # Verify directly via repository
    repo = PrescriptionRepository(test_db_session)
    saved = await repo.get_by_id(rx_id)
    assert saved is not None
    assert saved.status == PrescriptionStatus.COMPLETED.value
    assert len(saved.medications) == 1
    med = saved.medications[0]
    assert med.raw_drug_name == "Metformin"
    assert med.drug_name == "Metformin"
    assert med.strength_value == 500.0
    assert med.strength_unit == "mg"
    assert med.is_verified_safe is True
    assert saved.validation_result is not None
    assert saved.validation_result.is_safe is True
    assert len(saved.audit_events) >= 2


@pytest.mark.asyncio
async def test_10_database_failure(client: AsyncClient, test_db_session: AsyncSession):
    """10. Database failure: Handled gracefully via global exception handler."""
    # Mock repository flush to simulate DB failure
    mock_repo = MagicMock(spec=PrescriptionRepository)
    mock_repo.get_by_idempotency_key.return_value = None
    mock_repo.create_prescription.side_effect = Exception("Database connection pool exhausted")

    app.dependency_overrides[get_prescription_repository] = lambda: mock_repo

    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["safe_action_required"] == "CONSULT_PHARMACIST"


@pytest.mark.asyncio
async def test_11_get_existing_prescription(client: AsyncClient):
    """11. GET existing prescription: Returns latest persisted state matching contract."""
    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    post_res = await client.post("/api/v1/prescriptions", files=files)
    rx_id = post_res.json()["prescription_id"]

    get_res = await client.get(f"/api/v1/prescriptions/{rx_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["prescription_id"] == rx_id
    assert data["status"] == "COMPLETED"
    assert len(data["medications"]) == 1
    assert data["medications"][0]["drug_name"] == "Metformin"


@pytest.mark.asyncio
async def test_12_get_unknown_prescription_id(client: AsyncClient):
    """12. GET unknown prescription ID: Returns HTTP 404 with structured error envelope."""
    non_existent_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/prescriptions/{non_existent_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"]["code"] == "PRESCRIPTION_NOT_FOUND"
    assert non_existent_id in data["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_13_processing_failure(client: AsyncClient):
    """13. Processing failure: Upstream extractor failure returns 500 without leaking stack traces."""
    app.dependency_overrides[get_extraction_service] = lambda: PrescriptionExtractionService(
        extractor=MockVisionExtractor(should_fail=True)
    )

    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    response = await client.post("/api/v1/prescriptions", files=files)

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["error"]["code"] == "EXTRACTION_FAILED"
    # Verify no raw botocore/boto3 internal stack traces leaked
    assert "Bedrock converse timed out" not in data["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_14_request_id_and_idempotency(client: AsyncClient):
    """14. Request ID propagation and Idempotency key handling."""
    custom_request_id = "trace-uuid-12345"
    idempotency_key = "idemp-key-67890"

    files = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    headers = {
        "X-Request-ID": custom_request_id,
        "Idempotency-Key": idempotency_key,
    }

    # First call creates record
    res1 = await client.post("/api/v1/prescriptions", files=files, headers=headers)
    assert res1.status_code == 201
    assert res1.headers.get("X-Request-ID") == custom_request_id
    assert res1.json()["request_id"] == custom_request_id
    first_rx_id = res1.json()["prescription_id"]

    # Second call with same idempotency key returns identical record
    files2 = {"file": ("rx.jpg", io.BytesIO(b"\xff\xd8\xff\xe0..."), "image/jpeg")}
    res2 = await client.post("/api/v1/prescriptions", files=files2, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["prescription_id"] == first_rx_id
