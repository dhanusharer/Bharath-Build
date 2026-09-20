"""FastAPI Route Dependencies for Storage, Extractor, Service, and Session Injection."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.ports.prescription_extractor import VisionExtractionPort
from app.ports.storage import ObjectStoragePort
from app.providers.bedrock.config import BedrockProviderConfig
from app.providers.bedrock.prescription_extractor import BedrockPrescriptionExtractor
from app.providers.storage.s3 import S3ObjectStorage
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.prescription_extraction import PrescriptionExtractionService
from app.services.prescription_ingestion import PrescriptionIngestionService


def get_storage_port(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ObjectStoragePort:
    """Dependency for S3 Object Storage Port."""
    return S3ObjectStorage(
        bucket_name=settings.S3_BUCKET_NAME,
        region=settings.AWS_REGION,
        presigned_expiration_seconds=settings.S3_PRESIGNED_EXPIRATION_SECONDS,
    )


def get_vision_extractor(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VisionExtractionPort:
    """Dependency for Vision Extraction Port (Bedrock Adapter)."""
    bedrock_config = BedrockProviderConfig(
        model_id=settings.BEDROCK_MODEL_ID,
        fallback_model_id=settings.BEDROCK_FALLBACK_MODEL_ID,
        region=settings.AWS_REGION,
        timeout_seconds=settings.BEDROCK_TIMEOUT_SECONDS,
        max_retries=settings.BEDROCK_MAX_RETRIES,
        temperature=settings.BEDROCK_TEMPERATURE,
        max_tokens=settings.BEDROCK_MAX_TOKENS,
    )
    return BedrockPrescriptionExtractor(config=bedrock_config)


def get_extraction_service(
    extractor: Annotated[VisionExtractionPort, Depends(get_vision_extractor)],
) -> PrescriptionExtractionService:
    """Dependency for PrescriptionExtractionService."""
    return PrescriptionExtractionService(extractor=extractor)


def get_prescription_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PrescriptionRepository:
    """Dependency for PrescriptionRepository with per-request session."""
    return PrescriptionRepository(session=session)


def get_ingestion_service(
    storage: Annotated[ObjectStoragePort, Depends(get_storage_port)],
    extraction_service: Annotated[PrescriptionExtractionService, Depends(get_extraction_service)],
    repo: Annotated[PrescriptionRepository, Depends(get_prescription_repository)],
) -> PrescriptionIngestionService:
    """Dependency for PrescriptionIngestionService."""
    return PrescriptionIngestionService(
        storage_port=storage,
        extraction_service=extraction_service,
        repository=repo,
    )
